"""
app/services/vectorstore.py — ChromaDB wrapper for chunk storage + retrieval.

Single collection, every chunk tagged with `document_id` metadata. Retrieval
can be scoped to a specific set of document_ids (multi-document RAG with
document filtering) or left unscoped to search across every indexed
document — the schema doesn't need to change either way.
"""

import logging
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.services.chunking import Chunk

log = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    text: str
    similarity: float


class VectorStore:
    def __init__(self, persist_dir: str, collection_name: str):
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def document_exists(self, document_id: str) -> bool:
        """Used by the processing cache: if chunks for this document_id are
        already indexed, skip re-embedding entirely."""
        result = self._collection.get(where={"document_id": document_id}, limit=1)
        return len(result["ids"]) > 0

    def add_chunks(self, chunks: list[Chunk], embeddings) -> None:
        if not chunks:
            return
        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=[e.tolist() for e in embeddings],
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "document_id": c.document_id,
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                }
                for c in chunks
            ],
        )
        log.info("Indexed %d chunks into vector store", len(chunks))

    def query(
        self,
        query_embedding,
        document_ids: list[str] | None,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Dense similarity search. `document_ids`:
          - a non-empty list  -> restricted to exactly those documents (the
            normal multi-document-with-selection case; prevents any other
            document's chunks from leaking in).
          - None or []        -> unfiltered, searches every indexed document.
        """
        query_kwargs = {
            "query_embeddings": [query_embedding.tolist()],
            "n_results": top_k,
        }
        if document_ids:
            query_kwargs["where"] = (
                {"document_id": document_ids[0]}
                if len(document_ids) == 1
                else {"document_id": {"$in": document_ids}}
            )

        result = self._collection.query(**query_kwargs)
        if not result["ids"] or not result["ids"][0]:
            return []

        retrieved = []
        for i in range(len(result["ids"][0])):
            metadata = result["metadatas"][0][i]
            distance = result["distances"][0][i]  # cosine distance, lower = more similar
            similarity = max(0.0, 1.0 - distance)
            retrieved.append(RetrievedChunk(
                chunk_id=result["ids"][0][i],
                document_id=metadata["document_id"],
                document_name=metadata["document_name"],
                page_number=metadata["page_number"],
                text=result["documents"][0][i],
                similarity=round(similarity, 4),
            ))
        return retrieved

    def get_sample_chunks(self, document_id: str, max_samples: int = 6) -> list[RetrievedChunk]:
        """Pulls a small, page-spread sample of chunks for a document —
        used by the Document Insights feature, not for Q&A retrieval."""
        result = self._collection.get(where={"document_id": document_id})
        if not result["ids"]:
            return []

        items = list(zip(result["ids"], result["documents"], result["metadatas"]))
        items.sort(key=lambda x: x[2]["page_number"])

        if len(items) <= max_samples:
            sampled = items
        else:
            step = len(items) / max_samples
            indices = [int(i * step) for i in range(max_samples)]
            sampled = [items[i] for i in indices]

        return [
            RetrievedChunk(
                chunk_id=cid, document_id=meta["document_id"], document_name=meta["document_name"],
                page_number=meta["page_number"], text=text, similarity=0.0,
            )
            for cid, text, meta in sampled
        ]

    def delete_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})
        log.info("Deleted all chunks for document_id=%s", document_id)

    def count_chunks(self, document_id: str) -> int:
        result = self._collection.get(where={"document_id": document_id})
        return len(result["ids"])
