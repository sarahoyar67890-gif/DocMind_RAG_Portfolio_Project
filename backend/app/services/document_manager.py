"""
app/services/document_manager.py — Orchestrates PDF upload → extraction →
chunking → embedding → indexing, plus a small persisted registry that
tracks every processed document and which ones are currently "selected"
(i.e. in scope for the next query).

Multi-document model: uploading a document ADDS it to the registry and
registers it in the vector store; it does not replace anything else that
was already indexed. Selection is a separate, independent concept — a
document can be indexed but not selected (excluded from search without
losing its embeddings), and any number of documents can be selected at
once. Only `remove_document` actually deletes a document's vectors.

Caching: document_id is the SHA-256 hash of the uploaded file's bytes
(truncated to 16 hex chars). If a document with that hash has already been
processed (chunks already exist in the vector store), we skip re-extraction
and re-embedding entirely — re-uploading the same PDF twice is close to free.
"""

import hashlib
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
            self._write_registry({"documents": {}, "selected_document_ids": []})

    # ---------------- registry I/O ----------------
    def _read_registry(self) -> dict:
        with open(self._registry_path, "r") as f:
            data = json.load(f)
        # Defensive default for older registries written before this refactor.
        data.setdefault("documents", {})
        data.setdefault("selected_document_ids", [])
        return data

    def _write_registry(self, data: dict) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def _status_from_entry(self, document_id: str, entry: dict, selected_ids: set[str],
                            from_cache: bool, steps: list[ProcessingStep]) -> DocumentStatus:
        return DocumentStatus(
            document_id=document_id,
            filename=entry["filename"],
            num_pages=entry["num_pages"],
            num_chunks=entry["num_chunks"],
            file_size_bytes=entry["file_size_bytes"],
            is_selected=document_id in selected_ids,
            from_cache=from_cache,
            steps=steps,
        )

    # ---------------- core operations ----------------
    def process_upload(self, file_bytes: bytes, filename: str) -> tuple[DocumentStatus, list[ProcessingStep]]:
        steps: list[ProcessingStep] = []

        document_id = compute_document_id(file_bytes)
        steps.append(ProcessingStep(name="Document uploaded", status="done"))

        with self._lock:
            registry = self._read_registry()
            cached = document_id in registry["documents"] and self._store.document_exists(document_id)

        if cached:
            log.info("Document '%s' (id=%s) already indexed — using cache", filename, document_id)
            steps += [
                ProcessingStep(name="Extracting text", status="done", detail="cached"),
                ProcessingStep(name="Creating document chunks", status="done", detail="cached"),
                ProcessingStep(name="Generating embeddings", status="done", detail="cached"),
                ProcessingStep(name="Building vector index", status="done", detail="cached"),
                ProcessingStep(name="Ready for questions", status="done"),
            ]
            with self._lock:
                registry = self._read_registry()
                entry = registry["documents"][document_id]
                if document_id not in registry["selected_document_ids"]:
                    registry["selected_document_ids"].append(document_id)
                self._write_registry(registry)
                selected = set(registry["selected_document_ids"])
            return self._status_from_entry(document_id, entry, selected, from_cache=True, steps=steps), steps

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

        entry = {
            "filename": filename,
            "num_pages": len(pages),
            "num_chunks": len(chunks),
            "file_size_bytes": len(file_bytes),
            "processed_at": time.time(),
        }
        with self._lock:
            registry = self._read_registry()
            registry["documents"][document_id] = entry
            if document_id not in registry["selected_document_ids"]:
                registry["selected_document_ids"].append(document_id)
            self._write_registry(registry)
            selected = set(registry["selected_document_ids"])

        return self._status_from_entry(document_id, entry, selected, from_cache=False, steps=steps), steps

    def list_documents(self) -> list[DocumentStatus]:
        with self._lock:
            registry = self._read_registry()
        selected = set(registry["selected_document_ids"])
        docs = [
            self._status_from_entry(doc_id, entry, selected, from_cache=True, steps=[])
            for doc_id, entry in registry["documents"].items()
        ]
        docs.sort(key=lambda d: d.filename.lower())
        return docs

    def get_document(self, document_id: str) -> DocumentStatus | None:
        with self._lock:
            registry = self._read_registry()
        entry = registry["documents"].get(document_id)
        if not entry:
            return None
        selected = set(registry["selected_document_ids"])
        return self._status_from_entry(document_id, entry, selected, from_cache=True, steps=[])

    def get_selected_document_ids(self) -> list[str]:
        with self._lock:
            registry = self._read_registry()
        # Filter out any stale ids that no longer exist in the registry.
        return [doc_id for doc_id in registry["selected_document_ids"] if doc_id in registry["documents"]]

    def set_selected_documents(self, document_ids: list[str]) -> list[DocumentStatus]:
        """Replaces the selection wholesale with the given ids (unknown ids
        are silently dropped rather than raising, since the frontend just
        mirrors whatever set of checkboxes the user last touched)."""
        with self._lock:
            registry = self._read_registry()
            valid_ids = [doc_id for doc_id in document_ids if doc_id in registry["documents"]]
            registry["selected_document_ids"] = valid_ids
            self._write_registry(registry)
        return self.list_documents()

    def remove_document(self, document_id: str) -> None:
        """Deletes a document entirely: its vectors, its registry entry, and
        drops it from the current selection. This is the only operation that
        actually removes indexed data."""
        with self._lock:
            registry = self._read_registry()
            if document_id in registry["documents"]:
                self._store.delete_document(document_id)
                registry["documents"].pop(document_id, None)
                registry["selected_document_ids"] = [
                    doc_id for doc_id in registry["selected_document_ids"] if doc_id != document_id
                ]
                self._write_registry(registry)
                log.info("Removed document id=%s", document_id)
