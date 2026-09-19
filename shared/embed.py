from __future__ import annotations

import zlib
from typing import Protocol, Sequence

import numpy as np

# =============================================================================
# Module Overview
# =============================================================================
# One embedding for the whole app. `Embedder` is the protocol; `HashEmbedder`
# needs no download and is the default; `NomicEmbedder` is the sponsor's model
# behind the same interface, loaded lazily so the dependency stays optional.


class Embedder(Protocol):
    """Map texts to L2-normalised row vectors."""

    name: str

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


# -----------------------------------------------------------------
# Hashing embedder
# -----------------------------------------------------------------


class HashEmbedder:
    """Character n-gram feature hashing; deterministic, offline, good enough to cluster and retrieve."""

    name = "hash"

    def __init__(self, dim: int = 512, ngram: tuple[int, int] = (3, 5)) -> None:
        if dim < 16:
            raise ValueError("dim must be at least 16")
        lo, hi = ngram
        if lo < 1 or hi < lo:
            raise ValueError("ngram must be (lo, hi) with 1 <= lo <= hi")
        self.dim = dim
        self.ngram = ngram

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        lo, hi = self.ngram
        for row, text in enumerate(texts):
            padded = f" {text.lower()} "
            for n in range(lo, hi + 1):
                for i in range(max(len(padded) - n + 1, 0)):
                    # crc32 is stable across processes, unlike Python's salted hash().
                    out[row, zlib.crc32(padded[i : i + n].encode()) % self.dim] += 1.0
        # Damp frequent n-grams so length does not dominate the direction.
        out = np.log1p(out)
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1.0, norms)


# -----------------------------------------------------------------
# Nomic embedder, optional
# -----------------------------------------------------------------


class NomicEmbedder:
    """nomic-embed-text-v1.5 through sentence-transformers; installed with `uv sync --extra nomic`."""

    name = "nomic"

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
