"""Chat route — runs the OpenAI SDK agent and returns an answer with sources."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException

from app.core.agent import RagEmptyError, run_agent
from app.core.vector_store import VectorStoreManager
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chat/status", tags=["Chat"])
async def chat_status():
    """Returns whether the RAG knowledge base is ready for queries."""
    vs = VectorStoreManager.get_instance()
    empty = vs.is_empty()
    return {
        "rag_ready": not empty,
        "docs_indexed": vs.document_count(),
        "message": (
            "Ready — knowledge base is loaded."
            if not empty
            else "Knowledge base is empty. Please upload and index documents first."
        ),
    }


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Submit a natural language question to the OpenAI RAG agent.
    Returns 503 if the knowledge base is empty (RAG not built).
    """
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    session_id = request.session_id or str(uuid.uuid4())

    try:
        result = await run_agent(request.question)
    except RagEmptyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "rag_empty",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Agent pipeline error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    sources = [
        SourceChunk(
            filename=s.get("filename", "unknown"),
            page=s.get("page"),
            excerpt=s.get("excerpt", ""),
        )
        for s in result.get("sources", [])
    ]

    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        agent_steps=result.get("agent_steps", []),
        session_id=session_id,
    )
