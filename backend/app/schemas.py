"""
app/schemas.py — Pydantic models for DocMind's API contract.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ProcessingStep(BaseModel):
    name: str
    status: str  # "pending" | "in_progress" | "done" | "error"
    detail: Optional[str] = None


class DocumentStatus(BaseModel):
    document_id: str
    filename: str
    num_pages: int
    num_chunks: int
    file_size_bytes: int
    is_selected: bool
    from_cache: bool
    steps: list[ProcessingStep]


class UploadResponse(BaseModel):
    document: DocumentStatus
    message: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentStatus]
    selected_document_ids: list[str]


class SelectDocumentsRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


class InsightsRequest(BaseModel):
    document_id: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=10)
    # If omitted, the backend uses whatever documents are currently selected
    # in the registry. If provided, this request's documents take priority
    # for that single call without changing the persisted selection.
    document_ids: Optional[list[str]] = None


class SourceChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    excerpt: str
    retrieval_similarity: float
    # Hybrid-retrieval metadata (Phase 2). None where not applicable, e.g.
    # bm25_score is None for a chunk that only matched via dense search.
    dense_similarity: Optional[float] = None
    bm25_score: Optional[float] = None
    rrf_score: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    grounded: bool
    sources: list[SourceChunk]
    question: str
    documents_searched: list[str] = Field(default_factory=list)


class InsightsResponse(BaseModel):
    document_id: str
    overview: str
    sample_pages_used: list[int]


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    groq_configured: bool
    documents_indexed: int
    selected_documents: list[str] = Field(default_factory=list)
