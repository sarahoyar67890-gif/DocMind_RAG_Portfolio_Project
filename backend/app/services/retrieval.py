"""
app/services/retrieval.py — Hybrid retrieval: dense semantic search (via
ChromaDB) fused with BM25 lexical search, using Reciprocal Rank Fusion (RRF).

Why hybrid: dense embeddings are good at "what is this passage about"
semantic matches, but weak at exact tokens — dates, section numbers, IDs,
names, legal/technical terminology — where BM25's exact-term matching wins.
Fusing both, rather than picking one, catches queries either alone would
miss.

Why RRF: it combines two differently-scaled ranking signals (cosine
similarity vs. BM25 score) without needing to normalize or weight them
against each other — it only looks at each result's RANK within its own
list, which keeps the fusion simple, transparent, and hard to game with a
single outlier score.

Why the BM25 index is built on the fly: DocMind is a single-user, laptop-
scale app (a handful of documents, a few thousand chunks at most). Building
a fresh BM25Okapi index over the scoped corpus on every query costs
milliseconds and guarantees the lexical index can never drift out of sync
with what ChromaDB actually has indexed — no separate persistence layer to
keep consistent.
"""

import logging
import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.services.embeddings import embed_query
from app.services.vectorstore import RetrievedChunk, VectorStore

log = logging.getLogger(__name__)

# Keeps alphanumeric runs together (including dots/dashes/slashes) so things
# like "2024", "Section 4.2", "ISO-9001" stay as single meaningful tokens
# instead of being shredded by a plain \w+ split.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9./\-_]*")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class HybridChunk:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    text: str
    dense_similarity: float | None = None
    dense_rank: int | None = None
    bm25_score: float | None = None
    bm25_rank: int | None = None
    rrf_score: float = 0.0


def dense_search(
    store: VectorStore,
    embedding_model: str,
    query: str,
    document_ids: list[str],
    top_k: int,
) -> list[RetrievedChunk]:
    query_embedding = embed_query(query, embedding_model)
    return store.query(query_embedding, document_ids=document_ids, top_k=top_k)


def bm25_search(
    store: VectorStore,
    query: str,
    document_ids: list[str],
    top_k: int,
) -> list[tuple[RetrievedChunk, float]]:
    """Builds a BM25 index over every chunk in `document_ids` and scores
    `query` against it. Returns (chunk, score) pairs, best first, dropping
    zero-score matches (BM25 returns 0.0 for a document sharing no terms
    with the query — that's a non-match, not a weak match)."""
    corpus = store.get_all_chunks(document_ids)
    if not corpus:
        return []

    tokenized_corpus = [_tokenize(c.text) for c in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(zip(corpus, scores), key=lambda pair: pair[1], reverse=True)
    return [(chunk, float(score)) for chunk, score in ranked[:top_k] if score > 0]


def reciprocal_rank_fusion(
    dense_results: list[RetrievedChunk],
    bm25_results: list[tuple[RetrievedChunk, float]],
    rrf_k: int,
    hybrid_top_k: int,
) -> list[HybridChunk]:
    """RRF: each result's contribution is 1 / (rrf_k + rank), summed across
    whichever list(s) it appeared in. A chunk found near the top of BOTH
    lists ranks highest; a chunk found in only one list still contributes,
    just less. rrf_k (typically 60) dampens the influence of rank 1 vs.
    rank 2 so a single list's top pick doesn't dominate the fusion."""
    fused: dict[str, HybridChunk] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        hc = fused.setdefault(chunk.chunk_id, HybridChunk(
            chunk_id=chunk.chunk_id, document_id=chunk.document_id,
            document_name=chunk.document_name, page_number=chunk.page_number,
            text=chunk.text,
        ))
        hc.dense_similarity = chunk.similarity
        hc.dense_rank = rank
        hc.rrf_score += 1.0 / (rrf_k + rank)

    for rank, (chunk, score) in enumerate(bm25_results, start=1):
        hc = fused.setdefault(chunk.chunk_id, HybridChunk(
            chunk_id=chunk.chunk_id, document_id=chunk.document_id,
            document_name=chunk.document_name, page_number=chunk.page_number,
            text=chunk.text,
        ))
        hc.bm25_score = round(score, 4)
        hc.bm25_rank = rank
        hc.rrf_score += 1.0 / (rrf_k + rank)

    ordered = sorted(fused.values(), key=lambda hc: hc.rrf_score, reverse=True)
    return ordered[:hybrid_top_k]


def retrieve_hybrid(
    store: VectorStore,
    embedding_model: str,
    query: str,
    document_ids: list[str],
    dense_top_k: int,
    bm25_top_k: int,
    hybrid_top_k: int,
    rrf_k: int,
) -> list[HybridChunk]:
    """Runs dense + BM25 retrieval and fuses them. If BM25 fails for any
    reason (corrupt corpus, unexpected tokenization edge case), the query
    degrades to dense-only rather than failing outright — retrieval quality
    dips, but the app keeps working."""
    dense_results = dense_search(store, embedding_model, query, document_ids, dense_top_k)

    try:
        bm25_results = bm25_search(store, query, document_ids, bm25_top_k)
    except Exception:
        log.exception("BM25 retrieval failed — continuing with dense-only results")
        bm25_results = []

    fused = reciprocal_rank_fusion(dense_results, bm25_results, rrf_k=rrf_k, hybrid_top_k=hybrid_top_k)

    log.info(
        "Hybrid retrieval for %r: dense=%d bm25=%d fused=%d",
        query[:80], len(dense_results), len(bm25_results), len(fused),
    )
    return fused
