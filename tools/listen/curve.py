from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from shared.types import HourCount

# =============================================================================
# Module Overview
# =============================================================================
# Turn the per-hour structs DuckDB returns into the frozen `HourCount` tuple a
# template carries, and answer the one question Score asks of a curve: how
# many distinct authors it had in its latest hour.


def hour_curve(points: Sequence[dict[str, Any]]) -> tuple[HourCount, ...]:
    """Ordered `HourCount`s from DuckDB structs; hours are made timezone-aware UTC."""
    out: list[HourCount] = []
    for p in points:
        hour: datetime = p["hour"]
        if hour.tzinfo is None:
            hour = hour.replace(tzinfo=timezone.utc)
        out.append(HourCount(hour=hour, authors=int(p["authors"]), posts=int(p["posts"])))
    return tuple(sorted(out, key=lambda h: h.hour))


def velocity(curve: Sequence[HourCount]) -> float:
    """Distinct authors in the curve's latest hour; zero for an empty curve."""
    return float(curve[-1].authors) if curve else 0.0
