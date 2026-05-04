"""Singleton encoder — ONNX-based embedding via fastembed (no PyTorch/CUDA)."""

from typing import Optional

import numpy as np

_encoder: Optional["_Encoder"] = None
MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384-dim, ~33MB ONNX model, ~100MB RAM
EMBEDDING_DIM = 384


class _Encoder:
    """Thin wrapper around fastembed.TextEmbedding that mimics the sentence-transformers API."""

    def __init__(self) -> None:
        from fastembed import TextEmbedding
        self._model = TextEmbedding(MODEL_NAME)

    def encode(self, texts: list, normalize_embeddings: bool = True) -> np.ndarray:
        """Embed a list of strings and return a (N, 384) float32 array."""
        return np.array(list(self._model.embed(texts)), dtype=np.float32)


def get_encoder() -> _Encoder:
    """Return the shared encoder, loading it on first call."""
    global _encoder
    if _encoder is None:
        _encoder = _Encoder()
    return _encoder
