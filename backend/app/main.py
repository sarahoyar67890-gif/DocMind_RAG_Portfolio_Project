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
    UploadResponse, DocumentListResponse, SelectDocumentsRequest,
    InsightsRequest, QueryRequest, QueryResponse, InsightsResponse, HealthResponse,
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
    version="2.0.0",
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
    docs = doc_manager.list_documents()
    selected_ids = set(doc_manager.get_selected_document_ids())
    selected_names = [d.filename for d in docs if d.document_id in selected_ids]
    return HealthResponse(
        status="ok",
        groq_configured=llm_service.is_configured(),
        documents_indexed=len(docs),
        selected_documents=selected_names,
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
    except Exception:
        log.exception("Unexpected error processing upload '%s'", file.filename)
        raise HTTPException(status_code=500, detail="Something went wrong while processing this document.")

    message = "Document loaded from cache." if status.from_cache else "Document processed successfully."
    return UploadResponse(document=status, message=message)


@app.get("/documents", response_model=DocumentListResponse)
def list_documents():
    docs = doc_manager.list_documents()
    selected = doc_manager.get_selected_document_ids()
    return DocumentListResponse(documents=docs, selected_document_ids=selected)


@app.post("/documents/select", response_model=DocumentListResponse)
def select_documents(request: SelectDocumentsRequest):
    docs = doc_manager.set_selected_documents(request.document_ids)
    selected = doc_manager.get_selected_document_ids()
    return DocumentListResponse(documents=docs, selected_document_ids=selected)


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    doc = doc_manager.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc_manager.remove_document(document_id)
    return {"message": f"Removed '{doc.filename}'."}


@app.post("/documents/insights", response_model=InsightsResponse)
def document_insights(request: InsightsRequest):
    doc = doc_manager.get_document(request.document_id)
    if not doc:
        raise HTTPException(status_code=400, detail="That document was not found. Upload it first.")
    if not llm_service.is_configured():
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the backend.")

    samples = vector_store.get_sample_chunks(doc.document_id, max_samples=6)
    if not samples:
        raise HTTPException(status_code=500, detail="No indexed content found for this document.")

    try:
        overview = llm_service.generate_overview(doc.filename, samples)
    except LLMServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return InsightsResponse(
        document_id=doc.document_id,
        overview=overview,
        sample_pages_used=sorted({c.page_number for c in samples}),
    )


@app.post("/query", response_model=QueryResponse)
def query_document(request: QueryRequest):
    requested_ids = request.document_ids if request.document_ids else doc_manager.get_selected_document_ids()
    if not requested_ids:
        raise HTTPException(
            status_code=400,
            detail="No documents selected. Upload a PDF and select at least one document.",
        )

    docs = [doc_manager.get_document(doc_id) for doc_id in requested_ids]
    docs = [d for d in docs if d is not None]
    if not docs:
        raise HTTPException(
            status_code=400,
            detail="The selected documents are no longer available. Refresh your document list.",
        )

    if not llm_service.is_configured():
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the backend.")

    top_k = request.top_k or settings.retrieval_top_k
    document_ids = [d.document_id for d in docs]
    document_names = [d.filename for d in docs]

    try:
        return rag_pipeline.answer(
            request.question,
            document_ids=document_ids,
            document_names=document_names,
            top_k=top_k,
        )
    except LLMServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        log.exception("Unexpected error answering query")
        raise HTTPException(status_code=500, detail="Something went wrong while answering this question.")
