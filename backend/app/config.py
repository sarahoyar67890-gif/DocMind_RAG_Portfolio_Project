"""
app/config.py — Centralized configuration for DocMind's backend.

Every tunable value (chunking, retrieval, model names, ports) lives here and
is overridable via environment variables / .env. Nothing below is a magic
number scattered through the codebase — services import `settings` from
this module.

NOTE ON "FUTURE" SETTINGS: this file defines the full configuration surface
for DocMind 2.0 (hybrid retrieval, reranking, query transformation,
self-correcting RAG, OCR), even though not every phase of that upgrade is
implemented yet. Settings for not-yet-implemented features have defaults
that keep current behavior unchanged (e.g. RERANKER_ENABLED does nothing
until the reranker service exists) — this file just won't need to change
again as each phase lands.
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

    # --- Retrieval (baseline / dense) ---
    # retrieval_top_k stays as the default final chunk count used across the
    # app (e.g. as the fallback for QueryRequest.top_k). The dense/bm25/hybrid
    # knobs below are for the hybrid-retrieval pipeline (Phase 2).
    retrieval_top_k: int = 4
    dense_top_k: int = 20
    bm25_top_k: int = 20
    hybrid_top_k: int = 20  # candidates kept after RRF fusion, before reranking
    rrf_k: int = 60  # standard RRF damping constant

    # --- Reranking (Phase 3) ---
    reranker_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    final_top_k: int = 5  # candidates kept after reranking, sent to the LLM

    # --- Query transformation (Phase 4) ---
    query_transformation_enabled: bool = False

    # --- Self-correcting RAG (Phase 4) ---
    max_rag_retries: int = 2

    # --- Multi-document RAG (Phase 1 / Phase 5) ---
    multi_document_enabled: bool = True

    # --- OCR fallback for scanned PDFs (Phase 5) ---
    ocr_enabled: bool = False

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
