from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import numpy as np

from shared.embed import Embedder
from shared.text import has_link, word_count
from shared.types import AuthorBaseline, Context

# =============================================================================
# Module Overview
# =============================================================================
# What the model sees. `Features` is the immutable row; `FeatureBuilder`
# accumulates rows and emits the matrix. Named features come first, in
# `NAMES` order, and the embedding block follows, so the model can explain
# the named ones one at a time and the block as "what it says".

NAMES = (
    "author_median_log",
    "author_history_known",
    "hour_sin",
    "hour_cos",
    "words",
    "chars",
    "has_media",
    "has_link",
    "template_velocity_log",
    "exclaims",
    "question",
    "caps_share",
    "mentions",
    "hashtags",
    "emoji",
)

_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")


@dataclass(frozen=True, slots=True)
class Features:
    """One post's named feature values, in `NAMES` order, plus its embedding."""

    named: tuple[float, ...]
    embedding: np.ndarray


def named_features(text: str, author_median: float, history_known: bool, posted_at: datetime, has_media: bool, template_velocity: float) -> tuple[float, ...]:
    """The named block for one post; `has_link` is read from the text so nobody passes it twice."""
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    words = text.split()
    caps = sum(1 for w in words if len(w) > 1 and w.isupper())
    angle = 2 * math.pi * (posted_at.hour + posted_at.minute / 60) / 24
    return (
        math.log1p(max(author_median, 0.0)),
        1.0 if history_known else 0.0,
        math.sin(angle),
        math.cos(angle),
        float(word_count(text)),
        float(len(text)),
        1.0 if has_media else 0.0,
        1.0 if has_link(text) else 0.0,
        math.log1p(max(template_velocity, 0.0)),
        float(text.count("!")),
        1.0 if "?" in text else 0.0,
        caps / max(len(words), 1),
        float(text.count("@")),
        float(text.count("#")),
        float(len(_EMOJI.findall(text))),
    )


def features_for(text: str, author: AuthorBaseline, context: Context, embedder: Embedder) -> Features:
    """Features for one post at prediction time."""
    named = named_features(
        text, author.median_likes, author.posts > 0, context.posted_at, context.has_media, context.template_velocity
    )
    return Features(named=named, embedding=embedder.embed([text])[0])


class FeatureBuilder:
    """Accumulate rows, then `build` the matrix; embeddings are computed in one batch at the end."""

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._texts: list[str] = []
        self._named: list[tuple[float, ...]] = []

    def add(self, text: str, author_median: float, history_known: bool, posted_at: datetime, has_media: bool, template_velocity: float) -> None:
        self._texts.append(text)
        self._named.append(named_features(text, author_median, history_known, posted_at, has_media, template_velocity))

    def __len__(self) -> int:
        return len(self._texts)

    def build(self) -> np.ndarray:
        if not self._texts:
            raise ValueError("no rows added; call `add` first")
        named = np.asarray(self._named, dtype=np.float32)
        return np.hstack([named, self._embedder.embed(self._texts)])


def matrix_from(features: Features) -> np.ndarray:
    """A one-row matrix in the same column order `FeatureBuilder.build` uses."""
    return np.hstack([np.asarray(features.named, dtype=np.float32), features.embedding])[None, :]


def swap_named(row: np.ndarray, index: int, value: float) -> np.ndarray:
    """A copy of a one-row matrix with one named feature replaced."""
    if not 0 <= index < len(NAMES):
        raise IndexError(f"index must be in [0, {len(NAMES)})")
    out = row.copy()
    out[0, index] = value
    return out


def swap_embedding(row: np.ndarray, mean_embedding: np.ndarray) -> np.ndarray:
    """A copy of a one-row matrix with the embedding block replaced by the training mean."""
    out = row.copy()
    out[0, len(NAMES):] = mean_embedding
    return out


def describe(name: str, value: float) -> str:
    """A short human reading of one named feature's value."""
    readings = {
        "author_median_log": lambda v: f"author's median is {math.expm1(v):.0f} likes",
        "author_history_known": lambda v: "author history known" if v else "no author history",
        "words": lambda v: f"{v:.0f} words",
        "chars": lambda v: f"{v:.0f} characters",
        "has_media": lambda v: "has media" if v else "text only",
        "has_link": lambda v: "carries a link" if v else "no link",
        "template_velocity_log": lambda v: f"template at {math.expm1(v):.0f} authors this hour",
        "exclaims": lambda v: f"{v:.0f} exclamation marks",
        "question": lambda v: "asks a question" if v else "no question",
        "caps_share": lambda v: f"{v:.0%} of words in caps",
        "mentions": lambda v: f"{v:.0f} mentions",
        "hashtags": lambda v: f"{v:.0f} hashtags",
        "emoji": lambda v: f"{v:.0f} emoji",
    }
    if name in ("hour_sin", "hour_cos"):
        return "time of day"
    return readings[name](value)


def named_index(name: str) -> int:
    """Position of a named feature in the matrix."""
    return NAMES.index(name)


def names() -> Sequence[str]:
    """The named feature order."""
    return NAMES
