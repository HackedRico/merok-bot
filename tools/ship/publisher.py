from __future__ import annotations

from typing import Protocol

from shared.types import PostId

# =============================================================================
# Module Overview
# =============================================================================
# The publisher protocol and the one validation every adapter runs first.

MAX_POST_CHARS = 280


class Publisher(Protocol):
    """Send a post somewhere and say where it went."""

    name: str

    def post(self, text: str) -> PostId: ...


def validate_post(text: str) -> str:
    """The text with surrounding whitespace removed, or a `ValueError` saying what is wrong."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("post text is empty")
    if len(cleaned) > MAX_POST_CHARS:
        raise ValueError(f"post is {len(cleaned)} characters; the limit is {MAX_POST_CHARS}")
    return cleaned
