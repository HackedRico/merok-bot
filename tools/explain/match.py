from __future__ import annotations

from typing import Sequence

import numpy as np

from shared.embed import Embedder, cosine
from shared.text import normalise
from shared.types import Template

# =============================================================================
# Module Overview
# =============================================================================
# Which template a post rides. Exact normalised text is a certain match;
# otherwise the nearest template by embedding, if it is near enough.

THRESHOLD = 0.55


def match(text: str, templates: Sequence[Template], embedder: Embedder, threshold: float = THRESHOLD) -> tuple[Template | None, float]:
    """The matched template and the similarity, or (None, best similarity) below `threshold`."""
    if not templates:
        return None, 0.0
    key = normalise(text)
    for t in templates:
        if t.normalised == key:
            return t, 1.0
    sims = cosine(embedder.embed([key]), embedder.embed([t.normalised for t in templates]))[0]
    best = int(np.argmax(sims))
    similarity = float(sims[best])
    return (templates[best], similarity) if similarity >= threshold else (None, similarity)
