"""
In-memory ChromaDB vector store — singleton manager.

Uses HuggingFace sentence-transformers for embeddings (no API key required).
ChromaDB is configured with no persistence (ephemeral / in-memory only).
"""
from __future__ import annotations

import logging
from typing import List, Optional

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Thread-safe singleton managing an in-memory ChromaDB collection."""

    _instance: Optional["VectorStoreManager"] = None

    def __init__(self) -> None:
        settings = get_settings()

        logger.info("Loading embedding model: %s", settings.embedding_model)
        self._embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # Ephemeral (in-memory) Chroma client
        self._chroma_client = chromadb.EphemeralClient()

        self._store = Chroma(
            client=self._chroma_client,
            collection_name="rag_store",
            embedding_function=self._embeddings,
        )

        # Track document metadata: {doc_id: {filename, file_type, chunks}}
        self._doc_registry: dict[str, dict] = {}

        logger.info("Vector store initialised (in-memory ChromaDB)")

    @classmethod
    def get_instance(cls) -> "VectorStoreManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Write ─────────────────────────────────────────────────────────────────

    def add_documents(self, docs: List[Document], doc_id: str, filename: str, file_type: str) -> int:
        """Add chunks to the vector store and register the document."""
        if not docs:
            return 0

        self._store.add_documents(docs)

        self._doc_registry[doc_id] = {
            "filename": filename,
            "file_type": file_type,
            "chunks": len(docs),
        }
        logger.info("Indexed %d chunks for doc_id=%s (%s)", len(docs), doc_id, filename)
        return len(docs)

    def delete_document(self, doc_id: str) -> bool:
        """Remove all chunks belonging to a document from the store."""
        if doc_id not in self._doc_registry:
            return False

        # Chroma supports filter-based deletion
        try:
            self._store._collection.delete(where={"doc_id": doc_id})
            del self._doc_registry[doc_id]
            logger.info("Deleted doc_id=%s from vector store", doc_id)
            return True
        except Exception as exc:
            logger.error("Failed to delete doc_id=%s: %s", doc_id, exc)
            return False

    def reset_all(self) -> int:
        """
        Drop and recreate the Chroma collection, wiping every document and chunk.
        Returns the number of documents that were removed.
        """
        count = len(self._doc_registry)
        try:
            self._chroma_client.delete_collection("rag_store")
        except Exception:
            pass  # collection may already be empty
        # Recreate a fresh collection backed by the same embedding model
        self._store = Chroma(
            client=self._chroma_client,
            collection_name="rag_store",
            embedding_function=self._embeddings,
        )
        self._doc_registry.clear()
        logger.info("Vector store reset — %d documents removed", count)
        return count

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_retriever(self, top_k: Optional[int] = None):
        """Return a LangChain retriever for use in the RAG agent."""
        k = top_k or get_settings().top_k
        return self._store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k},
        )

    def list_documents(self) -> List[dict]:
        """Return metadata for all indexed documents."""
        return [
            {"doc_id": doc_id, **meta}
            for doc_id, meta in self._doc_registry.items()
        ]

    def document_count(self) -> int:
        return len(self._doc_registry)

    def is_empty(self) -> bool:
        return self.document_count() == 0
