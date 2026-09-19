from __future__ import annotations

from shared.types import Comparison, Curve, Forecast, PostId
from tools.learn.poller import Poller
from tools.learn.replay import ReplayPoller

# =============================================================================
# Module Overview
# =============================================================================
# Learn: watch what a post actually does and hold it against the forecast.
# The poller is the seam; replay serves a real trajectory from the firehose
# so the screen works before anything is posted for real. The firehose first
# sees a tweet hours to days after it is posted, so the comparison names the
# checkpoint the curve actually reached instead of assuming thirty minutes.

__all__ = ["observe", "compare", "Poller", "ReplayPoller"]

HALF_HOUR = 30.0
DAY = 24 * 60.0
AHEAD, BEHIND = 1.2, 0.8


def observe(post: PostId, minutes: float, source: Poller) -> Curve:
    """The like curve of `post` over its first `minutes`, from `source`."""
    if minutes <= 0:
        raise ValueError("minutes must be positive")
    points = source.trajectory(post, minutes)
    return Curve(post=post, points=tuple(sorted(points, key=lambda p: p.minutes)))


def compare(curve: Curve, forecast: Forecast) -> Comparison:
    """Observed likes against the forecast at the latest checkpoint the curve reached: thirty minutes, or a day."""
    if not curve.points:
        return Comparison(curve=curve, forecast=forecast, likes_at_30=0, predicted_at_30=0.0, verdict="no observations yet")
    last = curve.points[-1]
    early = [p for p in curve.points if p.minutes <= HALF_HOUR]
    if early and forecast.likes_1h is not None:
        # Inside the first hour the forecast is read as a linear ramp to the one-hour value.
        observed, predicted, label = early[-1].likes, forecast.likes_1h * (HALF_HOUR / 60.0), "30 minutes"
    else:
        hours = last.minutes / 60.0
        observed, predicted, label = last.likes, forecast.likes_1d, f"{hours:.0f} hours" if hours < 48 else f"{hours / 24:.0f} days"
    ratio = observed / max(predicted, 1.0)
    state = "ahead of forecast" if ratio > AHEAD else "behind forecast" if ratio < BEHIND else "on track"
    return Comparison(curve=curve, forecast=forecast, likes_at_30=observed, predicted_at_30=predicted, verdict=f"{state} at {label}")
