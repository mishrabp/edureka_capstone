"""Document upload, listing, and deletion routes."""
from __future__ import annotations

import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.ingestion import SUPPORTED_EXTENSIONS, generate_doc_id, load_and_chunk
from app.core.vector_store import VectorStoreManager
from app.models.schemas import DeleteResponse, DocumentListResponse, DocumentUploadResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, TXT, CSV, XLSX) and index it in the vector store.
    """
    filename = file.filename or "unnamed"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    doc_id = generate_doc_id()

    # Write to a temp file so loaders can access a real path
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        chunks = load_and_chunk(tmp_path, filename, doc_id)
    except Exception as exc:
        os.unlink(tmp_path)
        raise HTTPException(status_code=422, detail=f"Failed to process document: {exc}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not chunks:
        raise HTTPException(status_code=422, detail="Document produced no text content after parsing.")

    vs = VectorStoreManager.get_instance()
    chunks_indexed = vs.add_documents(chunks, doc_id, filename, ext.lstrip("."))

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=filename,
        file_type=ext.lstrip("."),
        chunks_indexed=chunks_indexed,
    )


@router.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents():
    """List all documents currently indexed in the vector store."""
    vs = VectorStoreManager.get_instance()
    docs = vs.list_documents()
    return DocumentListResponse(
        documents=docs,
        total=len(docs),
    )


@router.delete("/documents/{doc_id}", response_model=DeleteResponse, tags=["Documents"])
async def delete_document(doc_id: str):
    """Remove a document and all its chunks from the vector store."""
    vs = VectorStoreManager.get_instance()
    deleted = vs.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return DeleteResponse(doc_id=doc_id, message="Document removed successfully")


@router.delete("/documents", tags=["Documents"])
async def reset_all_documents():
    """
    Wipe the entire vector store — drop and recreate the collection.
    Use this to start fresh without restarting the server.
    """
    vs = VectorStoreManager.get_instance()
    removed = vs.reset_all()
    return {"removed_documents": removed, "message": f"Vector store cleared. {removed} document(s) removed."}

