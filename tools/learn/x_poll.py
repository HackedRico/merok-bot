from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Sequence

from shared.types import CurvePoint, PostId

# =============================================================================
# Module Overview
# =============================================================================
# The live poller: each call reads the post's like count once and appends a
# point, so "how did it do?" asked again and again draws the real curve in
# the minutes since posting. One read per call, never a loop that blocks a
# chat request. The read itself is a function handed in by `api/`, so this
# tool imports nothing from Ship.

MAX_READS_PER_POST = 60


class XPoller:
    """Adapter: one metrics read per call, accumulated per post."""

    name = "x"

    def __init__(self, read_likes: Callable[[str], int]) -> None:
        self._read_likes = read_likes
        self._points: dict[str, list[CurvePoint]] = {}

    def trajectory(self, post: PostId, minutes: float) -> Sequence[CurvePoint]:
        if post.platform != "x":
            raise ValueError(f"the X poller can only read X posts, got {post.platform!r}")
        points = self._points.setdefault(post.id, [])
        if len(points) >= MAX_READS_PER_POST:
            return points
        posted = post.posted_at or datetime.now(timezone.utc)
        elapsed = (datetime.now(timezone.utc) - posted).total_seconds() / 60.0
        points.append(CurvePoint(minutes=round(elapsed, 2), likes=int(self._read_likes(post.id))))
        return [p for p in points if p.minutes <= minutes] or points[-1:]
