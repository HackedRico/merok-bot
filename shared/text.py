from __future__ import annotations

import re

# =============================================================================
# Module Overview
# =============================================================================
# Pure text helpers shared by Listen, Explain, Draft and Score, so every tool
# normalises a post the same way. `normalise` is the identity a template is
# keyed on; two posts with equal normalised text are the same template.

_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_HANDLE = re.compile(r"@\w+")
_HASHTAG = re.compile(r"#\w+")
_SPACE = re.compile(r"\s+")


def normalise(body: str) -> str:
    """Lower-case a post and strip URLs, handles, hashtags and extra whitespace."""
    if not isinstance(body, str):
        raise TypeError("body must be a str")
    stripped = _HASHTAG.sub("", _HANDLE.sub("", _URL.sub("", body.lower())))
    return _SPACE.sub(" ", stripped).strip()


def has_link(body: str) -> bool:
    """True when the post carries a URL, which marks paid replication more often than not."""
    return bool(_URL.search(body or ""))


def word_count(body: str) -> int:
    """Number of whitespace-separated words."""
    return len((body or "").split())


def truncate(body: str, limit: int = 80) -> str:
    """Cut a string for display, with an ellipsis when it was cut."""
    if limit < 4:
        raise ValueError("limit must be at least 4")
    return body if len(body) <= limit else body[: limit - 3] + "..."
