"""Application configuration via pydantic-settings (reads from .env)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "google"          # "google" | "openai"
    llm_model: str = "models/gemini-flash-latest"
    google_api_key: str = ""
    openai_api_key: str = ""

    # Embeddings (HuggingFace — runs locally)
    embedding_model: str = "all-MiniLM-L6-v2"

    # RAG chunking
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 5

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    frontend_origin: str = "http://localhost:8501"


@lru_cache
def get_settings() -> Settings:
    return Settings()
