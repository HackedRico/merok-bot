from __future__ import annotations

import uuid

from shared.types import PostId
from tools.ship.publisher import validate_post

# =============================================================================
# Module Overview
# =============================================================================
# The rehearsal adapter: behaves like a publisher, touches nothing.


class DryRunPublisher:
    """Adapter: returns a fresh id and keeps what it was asked to post."""

    name = "dry_run"

    def __init__(self) -> None:
        self.posted: list[str] = []

    def post(self, text: str) -> PostId:
        cleaned = validate_post(text)
        self.posted.append(cleaned)
        return PostId(platform="dry_run", id=uuid.uuid4().hex[:12], url=None)
