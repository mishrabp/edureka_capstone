"""HTTP client wrapper for the FastAPI backend."""
from __future__ import annotations

from typing import BinaryIO, List, Optional

import httpx

import os

# Use environment variable for backend URL to support Docker/HF deployment
# Defaults to localhost:8001 as used in the local run.sh
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8001/api/v1")
TIMEOUT = 120  # seconds — allow time for LLM inference


def upload_document(file_bytes: bytes, filename: str) -> dict:
    """POST /documents/upload — returns DocumentUploadResponse dict."""
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(
            f"{BASE_URL}/documents/upload",
            files={"file": (filename, file_bytes, _content_type(filename))},
        )
        response.raise_for_status()
        return response.json()


def list_documents() -> List[dict]:
    """GET /documents — returns list of DocumentInfo dicts."""
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(f"{BASE_URL}/documents")
        response.raise_for_status()
        return response.json().get("documents", [])


def delete_document(doc_id: str) -> dict:
    """DELETE /documents/{doc_id}."""
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.delete(f"{BASE_URL}/documents/{doc_id}")
        response.raise_for_status()
        return response.json()


def reset_store() -> dict:
    """DELETE /documents — wipe the entire vector store."""
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.delete(f"{BASE_URL}/documents")
        response.raise_for_status()
        return response.json()



def ask(question: str, session_id: Optional[str] = None) -> dict:
    """POST /chat — returns ChatResponse dict."""
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(
            f"{BASE_URL}/chat",
            json={"question": question, "session_id": session_id},
        )
        response.raise_for_status()
        return response.json()


def health() -> dict:
    """GET /health."""
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{BASE_URL}/health")
        response.raise_for_status()
        return response.json()


def chat_status() -> dict:
    """GET /chat/status — returns rag_ready, docs_indexed, message."""
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{BASE_URL}/chat/status")
        response.raise_for_status()
        return response.json()



def _content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
    }.get(ext, "application/octet-stream")
