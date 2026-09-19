from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

# =============================================================================
# Module Overview
# =============================================================================
# One embedding for the whole app. `Embedder` is the protocol; `HashEmbedder`
# needs no download and is the default; `NomicEmbedder` is the sponsor's model
# behind the same interface, loaded lazily so the dependency stays optional.


class Embedder(Protocol):
    """Map texts to L2-normalised row vectors."""

    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


# -----------------------------------------------------------------
# Hashing embedder
# -----------------------------------------------------------------


class HashEmbedder:
    """Character n-gram feature hashing; deterministic, offline, and fast enough for 100k posts a second."""

    name = "hash"

    def __init__(self, dim: int = 512, ngram: tuple[int, int] = (3, 5)) -> None:
        if dim < 16:
            raise ValueError("dim must be at least 16")
        lo, hi = ngram
        if lo < 1 or hi < lo:
            raise ValueError("ngram must be (lo, hi) with 1 <= lo <= hi")
        self.dim = dim
        # char_wb pads words with spaces so n-grams never straddle two words; l2 makes dot products cosines.
        self._vec = HashingVectorizer(analyzer="char_wb", ngram_range=ngram, n_features=dim, norm="l2", lowercase=True)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if len(texts) == 0:
            return np.zeros((0, self.dim), dtype=np.float32)
        return self._vec.transform(list(texts)).toarray().astype(np.float32)


# -----------------------------------------------------------------
# Nomic embedder, optional
# -----------------------------------------------------------------


class NomicEmbedder:
    """nomic-embed-text-v1.5 through sentence-transformers; installed with `uv sync --extra nomic`."""

    name = "nomic"
    dim = 768

    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError("sentence-transformers is not installed; run `uv sync --extra nomic`") from exc
        self._model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        # Nomic expects a task prefix; documents and queries share one here.
        vectors = self._model.encode([f"search_document: {t}" for t in texts], normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)


def make_embedder(name: str) -> Embedder:
    """Build the embedder a settings value names."""
    if name == "hash":
        return HashEmbedder()
    if name == "nomic":
        return NomicEmbedder()
    raise ValueError(f"unknown embedder {name!r}; use `hash` or `nomic`")


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity matrix between two sets of already-normalised rows."""
    return a @ b.T
