"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.vector_store import VectorStoreManager
from app.api.routes import health, documents, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: eagerly initialise the singleton vector store (loads embedding model)."""
    logger.info("Starting up — initialising vector store & embedding model...")
    VectorStoreManager.get_instance()
    logger.info("Vector store ready ✓")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Agentic RAG API",
        description=(
            "Upload enterprise documents (PDF, TXT, CSV, Excel) and query them "
            "with an AI agent powered by LangGraph + LLM + ChromaDB."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow Streamlit frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://localhost:8501", "http://127.0.0.1:8501"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    prefix = "/api/v1"
    app.include_router(health.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Agentic RAG API — visit /docs for the Swagger UI"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
