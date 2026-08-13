"""
app/main.py — DocMind FastAPI backend.

Responsibilities: document upload/processing, query handling, retrieval,
answer generation, citation data. All RAG logic lives in services/ — this
file is routing + validation + error translation only.
"""

import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.schemas import (
    UploadResponse, ActiveDocumentResponse, QueryRequest, QueryResponse,
    InsightsResponse, HealthResponse,
)
from app.services.document_manager import DocumentManager
from app.services.pdf_processor import PDFProcessingError
from app.services.llm_service import LLMService, LLMServiceError
from app.services.rag_pipeline import RAGPipeline
from app.services.vectorstore import VectorStore

configure_logging()
log = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="DocMind API",
    description="RAG-powered document Q&A backend — retrieval, grounded generation, citations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-user portfolio app behind Docker/localhost; tighten for real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Wire up services (constructed once at startup) ---
vector_store = VectorStore(settings.chroma_persist_dir, settings.chroma_collection_name)
doc_manager = DocumentManager(settings, vector_store)
llm_service = LLMService(
    api_key=settings.groq_api_key,
    model=settings.groq_model,
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
)
rag_pipeline = RAGPipeline(vector_store, llm_service, settings.embedding_model)


@app.get("/health", response_model=HealthResponse)
def health():
    active = doc_manager.get_active_document()
    return HealthResponse(
        status="ok",
        groq_configured=llm_service.is_configured(),
        active_document=active.filename if active else None,
    )


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(file_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large. Maximum allowed size is {settings.max_upload_mb} MB.",
        )

    try:
        status, steps = doc_manager.process_upload(file_bytes, file.filename)
    except PDFProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("Unexpected error processing upload '%s'", file.filename)
        raise HTTPException(status_code=500, detail="Something went wrong while processing this document.")

    message = "Document loaded from cache." if status.from_cache else "Document processed successfully."
    return UploadResponse(document=status, message=message)


@app.get("/documents/active", response_model=ActiveDocumentResponse)
def get_active_document():
    return ActiveDocumentResponse(document=doc_manager.get_active_document())


@app.post("/documents/clear")
def clear_document():
    doc_manager.clear_active_document()
    return {"message": "Active document cleared."}


@app.post("/documents/insights", response_model=InsightsResponse)
def document_insights():
    active = doc_manager.get_active_document()
    if not active:
        raise HTTPException(status_code=400, detail="No active document. Upload a PDF first.")
    if not llm_service.is_configured():
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the backend.")

    samples = vector_store.get_sample_chunks(active.document_id, max_samples=6)
    if not samples:
        raise HTTPException(status_code=500, detail="No indexed content found for the active document.")

    try:
        overview = llm_service.generate_overview(active.filename, samples)
    except LLMServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return InsightsResponse(
        document_id=active.document_id,
        overview=overview,
        sample_pages_used=sorted({c.page_number for c in samples}),
    )


@app.post("/query", response_model=QueryResponse)
def query_document(request: QueryRequest):
    active = doc_manager.get_active_document()
    if not active:
        raise HTTPException(status_code=400, detail="No active document. Upload a PDF first.")
    if not llm_service.is_configured():
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the backend.")

    top_k = request.top_k or settings.retrieval_top_k
    try:
        return rag_pipeline.answer(request.question, document_id=active.document_id, top_k=top_k)
    except LLMServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        log.exception("Unexpected error answering query")
        raise HTTPException(status_code=500, detail="Something went wrong while answering this question.")
