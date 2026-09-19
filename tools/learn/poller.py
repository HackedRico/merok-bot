from __future__ import annotations

from typing import Protocol, Sequence

from shared.types import CurvePoint, PostId

# =============================================================================
# Module Overview
# =============================================================================
# The poller protocol: given a post, the likes seen over its first minutes.


class Poller(Protocol):
    """Where the curve's points come from."""

    name: str

    def trajectory(self, post: PostId, minutes: float) -> Sequence[CurvePoint]: ...
