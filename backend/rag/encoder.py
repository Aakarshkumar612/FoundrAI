"""Singleton encoder — loads sentence-transformers model once at first use."""

from typing import Optional
from sentence_transformers import SentenceTransformer

_encoder: Optional[SentenceTransformer] = None
MODEL_NAME = "all-MiniLM-L6-v2"   # 80MB, 384-dim, fast CPU inference
EMBEDDING_DIM = 384


def get_encoder() -> SentenceTransformer:
    """Return the shared encoder, loading it on first call.

    Returns:
        Loaded SentenceTransformer model.
    """
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer(MODEL_NAME)
    return _encoder
