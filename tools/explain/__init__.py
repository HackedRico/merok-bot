from __future__ import annotations

from typing import Sequence

from shared.embed import Embedder
from shared.llm import LLM
from shared.types import Explanation, Message, Template
from tools.explain.gloss import gloss_request, gloss_system
from tools.explain.match import match

# =============================================================================
# Module Overview
# =============================================================================
# Explain: take a post someone does not understand, find the template it
# rides, and say what it is using only what the data shows. The slang
# translator done right: grounded in a curve, not guessed.

__all__ = ["explain", "match"]


def explain(text: str, templates: Sequence[Template], llm: LLM, embedder: Embedder) -> Explanation:
    """What `text` rides, how far it spread, who started it, and a gloss the facts support."""
    if not text.strip():
        raise ValueError("text is empty; paste the post to explain")
    template, similarity = match(text, templates, embedder)
    gloss = llm.complete(gloss_system(), [Message("user", gloss_request(text, template, similarity))], temperature=0.3, max_tokens=300)
    return Explanation(text=text, template=template, similarity=similarity, gloss=gloss)
