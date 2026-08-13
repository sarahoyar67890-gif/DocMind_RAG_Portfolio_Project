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
    is_active: bool
    from_cache: bool
    steps: list[ProcessingStep]


class UploadResponse(BaseModel):
    document: DocumentStatus
    message: str


class ActiveDocumentResponse(BaseModel):
    document: Optional[DocumentStatus] = None


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=10)


class SourceChunk(BaseModel):
    chunk_id: str
    document_name: str
    page_number: int
    excerpt: str
    retrieval_similarity: float


class QueryResponse(BaseModel):
    answer: str
    grounded: bool
    sources: list[SourceChunk]
    question: str


class InsightsResponse(BaseModel):
    document_id: str
    overview: str
    sample_pages_used: list[int]


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    groq_configured: bool
    active_document: Optional[str] = None
