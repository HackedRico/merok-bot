from __future__ import annotations

from shared.llm import LLM
from shared.types import Candidate, Exemplars, Message, Template
from tools.draft.prompt import DRAFT_COUNT, parse_candidates, persona_system, request
from tools.draft.retrieve import retrieve
from tools.draft.turing import turing_test

# =============================================================================
# Module Overview
# =============================================================================
# Draft: five posts in the user's own voice. The sponsor's Digital Twin
# method: a persona prompt built from retrieved exemplars of the author's
# real posts, then generation. `turing_test` scores whether drafts can be
# told from the real thing.

__all__ = ["draft", "retrieve", "turing_test", "DRAFT_COUNT"]


def draft(intent: str, exemplars: Exemplars, template: Template | None, llm: LLM) -> list[Candidate]:
    """Five candidates for `intent` in the exemplars' voice, riding `template` when one is given."""
    if not intent.strip():
        raise ValueError("intent is empty; say what the post should do")
    if not exemplars.posts:
        raise ValueError("exemplars are empty; retrieve the author's posts first")
    raw = llm.complete(persona_system(exemplars), [Message("user", request(intent, template))], temperature=0.8, max_tokens=900)
    texts = parse_candidates(raw)
    template_text = template.text if template else None
    return [Candidate(text=t, rationale=r, template_text=template_text) for t, r in texts]
