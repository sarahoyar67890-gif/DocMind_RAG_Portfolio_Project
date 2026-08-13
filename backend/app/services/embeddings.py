"""
app/services/embeddings.py — Sentence-Transformers embedding wrapper.

The model is loaded once (module-level cache keyed by model name) since
loading is the expensive part; encoding individual batches is cheap by
comparison.
"""

import logging
import numpy as np
from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

_model_cache: dict[str, SentenceTransformer] = {}


def get_embedding_model(model_name: str) -> SentenceTransformer:
    if model_name not in _model_cache:
        log.info("Loading embedding model '%s' (first use — this downloads/caches the model)...", model_name)
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def embed_texts(texts: list[str], model_name: str) -> np.ndarray:
    """Returns L2-normalized embeddings, shape (len(texts), dim). Normalizing
    lets us use cosine similarity via a plain dot product downstream, which
    is what ChromaDB's cosine space expects."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    model = get_embedding_model(model_name)
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return embeddings.astype(np.float32)


def embed_query(query: str, model_name: str) -> np.ndarray:
    return embed_texts([query], model_name)[0]
