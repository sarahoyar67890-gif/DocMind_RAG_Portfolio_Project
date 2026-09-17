"""
app/services/rag_pipeline.py — Ties hybrid retrieval + LLM generation
together, and builds the citation objects the frontend renders as source
cards.

Anti-hallucination is enforced in two places, deliberately:
  1. Prompting (see llm_service.SYSTEM_PROMPT) — instructs the model to
     refuse rather than guess.
  2. Application logic (here) — if retrieval finds literally nothing across
     the selected document(s), we never call the LLM at all and return a
     fixed, honest "not enough information" response. A prompt can be a
     strong nudge; it isn't a hard guarantee, so the code doesn't rely on it
     alone for the one case (zero retrieved context) where we can be certain.
"""

import logging

from app.schemas import SourceChunk, QueryResponse
from app.services.llm_service import LLMService, LLMServiceError
from app.services.retrieval import retrieve_hybrid
from app.services.vectorstore import VectorStore

log = logging.getLogger(__name__)

NO_CONTEXT_ANSWER = (
    "I couldn't find any relevant content in the selected document(s) for this question. "
    "They don't appear to provide enough information to answer it."
)


class RAGPipeline:
    def __init__(
        self,
        vector_store: VectorStore,
        llm_service: LLMService,
        embedding_model: str,
        dense_top_k: int,
        bm25_top_k: int,
        hybrid_top_k: int,
        rrf_k: int,
    ):
        self._store = vector_store
        self._llm = llm_service
        self._embedding_model = embedding_model
        self._dense_top_k = dense_top_k
        self._bm25_top_k = bm25_top_k
        self._hybrid_top_k = hybrid_top_k
        self._rrf_k = rrf_k

    def answer(
        self,
        question: str,
        document_ids: list[str],
        document_names: list[str],
        top_k: int,
    ) -> QueryResponse:
        fused = retrieve_hybrid(
            store=self._store,
            embedding_model=self._embedding_model,
            query=question,
            document_ids=document_ids,
            dense_top_k=self._dense_top_k,
            bm25_top_k=self._bm25_top_k,
            hybrid_top_k=self._hybrid_top_k,
            rrf_k=self._rrf_k,
        )
        # Hybrid retrieval returns up to hybrid_top_k fused candidates; only
        # the top `top_k` of those are actually sent to the LLM. (Phase 3
        # replaces this straight truncation with cross-encoder reranking.)
        retrieved = fused[:top_k]

        log.info(
            "Hybrid retrieval: %d fused candidates, %d sent to LLM, across %d document(s) for question %r",
            len(fused), len(retrieved), len(document_ids), question[:80],
        )

        if not retrieved:
            return QueryResponse(
                answer=NO_CONTEXT_ANSWER,
                grounded=False,
                sources=[],
                question=question,
                documents_searched=document_names,
            )

        try:
            answer_text = self._llm.generate_answer(question, retrieved)
        except LLMServiceError:
            # Surface a clean error rather than a raw exception; the router
            # translates this into an HTTP 502 with the same message.
            raise

        sources = [
            SourceChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                excerpt=chunk.text,
                retrieval_similarity=chunk.dense_similarity or 0.0,
                dense_similarity=chunk.dense_similarity,
                bm25_score=chunk.bm25_score,
                rrf_score=round(chunk.rrf_score, 5),
            )
            for chunk in retrieved
        ]

        return QueryResponse(
            answer=answer_text,
            grounded=True,
            sources=sources,
            question=question,
            documents_searched=document_names,
        )
