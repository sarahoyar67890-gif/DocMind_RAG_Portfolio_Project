"""
app/config.py — Centralized configuration for DocMind's backend.

Every tunable value (chunking, retrieval, model names, ports) lives here and
is overridable via environment variables / .env. Nothing below is a magic
number scattered through the codebase — services import `settings` from
this module.
"""

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Groq LLM ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 800

    # --- Embeddings ---
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Chunking ---
    chunk_size: int = 800
    chunk_overlap: int = 150

    # --- Retrieval ---
    retrieval_top_k: int = 4

    # --- Vector store ---
    chroma_persist_dir: str = "/app/chroma_data"
    chroma_collection_name: str = "docmind_chunks"

    # --- Upload limits ---
    max_upload_mb: int = 30

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Document registry (backend-local metadata store) ---
    registry_path: str = "/app/app/data/document_registry.json"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Ensure local directories exist regardless of where this runs (Docker or bare Windows)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.registry_path).parent.mkdir(parents=True, exist_ok=True)
    return settings