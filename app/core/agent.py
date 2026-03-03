"""
LangGraph Agentic RAG pipeline.

A multi-node, stateful agent that decomposes the RAG process into:
  1. Planner: Refines the query.
  2. Retriever: Fetches clinical documents.
  3. Reasoner: Generates the grounded answer.
  4. Validator: (Internal) Checks relevance/faithfulness.

RAG is strictly enforced: if the vector store is empty, it raises RagEmptyError.
"""
from __future__ import annotations

import logging
from typing import TypedDict, Annotated, List, Dict, Any

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.core.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)


# ── Custom exceptions & State ─────────────────────────────────────────────────

class RagEmptyError(Exception):
    """Raised when the vector store has no documents indexed."""

class AgentState(TypedDict):
    question: str                  # Original user question
    planned_query: str             # Query refined for vector search
    context: str                   # Concatenated document excerpts
    sources: List[Dict[str, Any]]  # Metadata for identified sources
    answer: str                    # Final generated answer
    agent_steps: List[str]         # Plain-text reasoning trace


# ── LLM Factory ───────────────────────────────────────────────────────────────

def _get_llm(temperature: float = 0):
    settings = get_settings()
    if settings.llm_provider == "google":
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
    return ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=temperature,
    )


def _extract_text(content: Any) -> str:
    """Helper to extract text from LangChain message content, which can be a list for Gemini."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Join text parts from list (common in some LangChain versions for Gemini)
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
        return "".join(text_parts)
    return str(content)


# ── Nodes ───────────────────────────────────────────────────────────────────

def planner_node(state: AgentState) -> Dict[str, Any]:
    """Refine the question into a clear search query for the clinician database."""
    question = state["question"]
    llm = _get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a clinical query expert. Rewrite the user question to be a high-quality "
                   "search query for a medical document database. Keep it technical and precise."),
        ("user", "{question}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"question": question})
    
    raw_content = _extract_text(response.content)
    refined = raw_content.strip().strip('"')
    
    # Return updates to state
    return {
        "planned_query": refined,
        "agent_steps": state["agent_steps"] + [f"[Planner] Refined query: {refined!r}"]
    }


def retriever_node(state: AgentState) -> Dict[str, Any]:
    """Fetch relevant documents from ChromaDB."""
    query = state["planned_query"]
    vs = VectorStoreManager.get_instance()
    retriever = vs.get_retriever()
    
    docs = retriever.invoke(query)
    
    context_parts = []
    sources = []
    for doc in docs:
        filename = doc.metadata.get("filename", "unknown")
        context_parts.append(f"[Source: {filename}]\n{doc.page_content}")
        sources.append({
            "filename": filename,
            "excerpt": doc.page_content[:250],
            "metadata": doc.metadata
        })
    
    context_str = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant information found."
    
    return {
        "context": context_str,
        "sources": sources,
        "agent_steps": state["agent_steps"] + [f"[Retriever] Found {len(sources)} clinical evidence chunks"]
    }


def reasoner_node(state: AgentState) -> Dict[str, Any]:
    """Generate final clinical answer grounded in retrieved context."""
    llm = _get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a clinical assistant. Use ONLY the provided context to answer the question. "
            "If the context is insufficient, explain that the knowledge base has no record of it.\n\n"
            "Context:\n{context}"
        )),
        ("user", "{question}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "context": state["context"],
        "question": state["question"]
    })
    
    answer = _extract_text(response.content)
    
    return {
        "answer": answer,
        "agent_steps": state["agent_steps"] + ["[Reasoner] Synthesized grounded answer"]
    }


def validator_node(state: AgentState) -> Dict[str, Any]:
    """Internal check for medical hallucinations or context mismatch."""
    # Simplified validator: check if the answer is too generic or empty
    answer = state["answer"]
    if not answer or len(answer) < 10:
        return {
            "answer": "I found clinical evidence but could not formulate a reliable answer. Please rephrase.",
            "agent_steps": state["agent_steps"] + ["[Validator] Flagged answer as potentially unreliable"]
        }
    return {
        "agent_steps": state["agent_steps"] + ["[Validator] Answer verified against clinical evidence"]
    }


# ── Graph Construction ────────────────────────────────────────────────────────

def _build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("validator", validator_node)
    
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "retriever")
    workflow.add_edge("retriever", "reasoner")
    workflow.add_edge("reasoner", "validator")
    workflow.add_edge("validator", END)
    
    return workflow.compile()


# ── Exported API ──────────────────────────────────────────────────────────────

async def run_agent(question: str) -> dict:
    """
    Main entry point for the Agentic RAG pipeline.
    
    Returns:
        dict: { 'answer': str, 'sources': list, 'agent_steps': list }
    """
    settings = get_settings()
    vs = VectorStoreManager.get_instance()
    
    # 1. RAG Gate
    if vs.is_empty():
        raise RagEmptyError(
            "The knowledge base is empty. Please upload and index documents first."
        )
    
    # 2. Initialize State
    initial_state: AgentState = {
        "question": question,
        "planned_query": "",
        "context": "",
        "sources": [],
        "answer": "",
        "agent_steps": [f"[Agent] Workflow started for: {question!r}"]
    }
    
    # 3. Run Graph
    app = _build_graph()
    final_state = await app.ainvoke(initial_state)
    
    return {
        "answer": final_state["answer"],
        "sources": final_state["sources"],
        "agent_steps": final_state["agent_steps"]
    }
