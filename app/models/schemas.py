"""Pydantic models for API request/response schemas."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Document Schemas ──────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    chunks_indexed: int
    message: str = "Document ingested successfully"


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    chunks: int


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int


class DeleteResponse(BaseModel):
    doc_id: str
    message: str


# ── Chat Schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="User question")
    session_id: Optional[str] = Field(None, description="Optional conversation session ID")


class SourceChunk(BaseModel):
    filename: str
    page: Optional[int] = None
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = []
    agent_steps: List[str] = []
    session_id: Optional[str] = None


# ── Health Schema ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    docs_indexed: int = 0
    embedding_model: str = ""
    llm_model: str = ""
