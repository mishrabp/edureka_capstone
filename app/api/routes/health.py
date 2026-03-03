"""Health check route."""
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.core.vector_store import VectorStoreManager
from app.config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Returns server health and current vector store stats."""
    settings = get_settings()
    vs = VectorStoreManager.get_instance()
    return HealthResponse(
        status="ok",
        docs_indexed=vs.document_count(),
        embedding_model=settings.embedding_model,
        llm_model=settings.llm_model,
    )
