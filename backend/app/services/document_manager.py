"""
app/services/document_manager.py — Orchestrates PDF upload → extraction →
chunking → embedding → indexing, plus a small persisted registry that
tracks document metadata and which document is currently "active".

Caching: document_id is the SHA-256 hash of the uploaded file's bytes
(truncated to 16 hex chars). If a document with that hash has already been
processed (chunks already exist in the vector store), we skip re-extraction
and re-embedding entirely and just mark it active — re-uploading the same
PDF twice is close to free.
"""

import json
import logging
import threading
import time
from pathlib import Path

from app.config import Settings
from app.schemas import DocumentStatus, ProcessingStep
from app.services.pdf_processor import extract_pages, PDFProcessingError
from app.services.chunking import chunk_pages
from app.services.embeddings import embed_texts
from app.services.vectorstore import VectorStore

log = logging.getLogger(__name__)

import hashlib


def compute_document_id(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()[:16]


class DocumentManager:
    """Thread-safe-ish singleton around a small JSON registry file. Not built
    for high concurrency (this is a single-user portfolio app), but the lock
    prevents corrupting the registry file on overlapping requests."""

    def __init__(self, settings: Settings, vector_store: VectorStore):
        self._settings = settings
        self._store = vector_store
        self._registry_path = Path(settings.registry_path)
        self._lock = threading.Lock()
        if not self._registry_path.exists():
            self._write_registry({"documents": {}, "active_document_id": None})

    # ---------------- registry I/O ----------------
    def _read_registry(self) -> dict:
        with open(self._registry_path, "r") as f:
            return json.load(f)

    def _write_registry(self, data: dict) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w") as f:
            json.dump(data, f, indent=2)

    # ---------------- core operations ----------------
    def process_upload(self, file_bytes: bytes, filename: str) -> tuple[DocumentStatus, list[ProcessingStep]]:
        steps: list[ProcessingStep] = []

        document_id = compute_document_id(file_bytes)
        steps.append(ProcessingStep(name="Document uploaded", status="done"))

        with self._lock:
            registry = self._read_registry()
            cached = document_id in registry["documents"]

            if cached and self._store.document_exists(document_id):
                log.info("Document '%s' (id=%s) already indexed — using cache", filename, document_id)
                entry = registry["documents"][document_id]
                steps += [
                    ProcessingStep(name="Extracting text", status="done", detail="cached"),
                    ProcessingStep(name="Creating document chunks", status="done", detail="cached"),
                    ProcessingStep(name="Generating embeddings", status="done", detail="cached"),
                    ProcessingStep(name="Building vector index", status="done", detail="cached"),
                    ProcessingStep(name="Ready for questions", status="done"),
                ]
                registry["active_document_id"] = document_id
                self._write_registry(registry)
                status = DocumentStatus(
                    document_id=document_id,
                    filename=entry["filename"],
                    num_pages=entry["num_pages"],
                    num_chunks=entry["num_chunks"],
                    file_size_bytes=entry["file_size_bytes"],
                    is_active=True,
                    from_cache=True,
                    steps=steps,
                )
                return status, steps

        # --- Not cached: run the real pipeline ---
        try:
            pages = extract_pages(file_bytes, filename)
            steps.append(ProcessingStep(name="Extracting text", status="done", detail=f"{len(pages)} pages"))
        except PDFProcessingError as e:
            steps.append(ProcessingStep(name="Extracting text", status="error", detail=str(e)))
            raise

        chunks = chunk_pages(
            pages, document_id, filename,
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )
        if not chunks:
            raise PDFProcessingError(
                f"'{filename}' produced no usable text chunks after processing."
            )
        steps.append(ProcessingStep(name="Creating document chunks", status="done", detail=f"{len(chunks)} chunks"))

        embeddings = embed_texts([c.text for c in chunks], self._settings.embedding_model)
        steps.append(ProcessingStep(name="Generating embeddings", status="done", detail=self._settings.embedding_model))

        self._store.add_chunks(chunks, embeddings)
        steps.append(ProcessingStep(name="Building vector index", status="done"))
        steps.append(ProcessingStep(name="Ready for questions", status="done"))

        with self._lock:
            registry = self._read_registry()
            registry["documents"][document_id] = {
                "filename": filename,
                "num_pages": len(pages),
                "num_chunks": len(chunks),
                "file_size_bytes": len(file_bytes),
                "processed_at": time.time(),
            }
            registry["active_document_id"] = document_id
            self._write_registry(registry)

        status = DocumentStatus(
            document_id=document_id,
            filename=filename,
            num_pages=len(pages),
            num_chunks=len(chunks),
            file_size_bytes=len(file_bytes),
            is_active=True,
            from_cache=False,
            steps=steps,
        )
        return status, steps

    def get_active_document(self) -> DocumentStatus | None:
        with self._lock:
            registry = self._read_registry()
        active_id = registry.get("active_document_id")
        if not active_id or active_id not in registry["documents"]:
            return None
        entry = registry["documents"][active_id]
        return DocumentStatus(
            document_id=active_id,
            filename=entry["filename"],
            num_pages=entry["num_pages"],
            num_chunks=entry["num_chunks"],
            file_size_bytes=entry["file_size_bytes"],
            is_active=True,
            from_cache=True,
            steps=[],
        )

    def clear_active_document(self) -> None:
        """Clears the ACTIVE pointer and deletes that document's vectors.
        Other previously-processed documents remain cached in the registry
        (re-uploading them later is instant), but only one can be active."""
        with self._lock:
            registry = self._read_registry()
            active_id = registry.get("active_document_id")
            if active_id:
                self._store.delete_document(active_id)
                registry["documents"].pop(active_id, None)
                registry["active_document_id"] = None
                self._write_registry(registry)
                log.info("Cleared active document id=%s", active_id)
