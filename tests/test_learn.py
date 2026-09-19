from __future__ import annotations

import pyarrow as pa

from shared.types import Curve, CurvePoint, Forecast, PostId
from tools.learn import compare, observe
from tools.learn.replay import ReplayPoller


def test_replay_serves_a_real_early_trajectory(hour_table: pa.Table) -> None:
    poller = ReplayPoller(hour_table, seed=1)
    assert poller.available > 10
    curve = observe(PostId("dry_run", "abc", None), minutes=14 * 24 * 60, source=poller)
    assert len(curve.points) >= 3
    assert [p.minutes for p in curve.points] == sorted(p.minutes for p in curve.points)


def test_compare_reads_both_at_thirty_minutes() -> None:
    post = PostId("dry_run", "abc", None)
    curve = Curve(post, (CurvePoint(5, 10), CurvePoint(25, 40), CurvePoint(45, 90)))
    ahead = compare(curve, Forecast(likes_1d=100, likes_1h=40, relative_to_median=1.0, drivers=()))
    assert ahead.likes_at_30 == 40 and ahead.predicted_at_30 == 20 and ahead.verdict == "ahead of forecast at 30 minutes"
    late = Curve(post, (CurvePoint(3000, 80), CurvePoint(4400, 95)))
    day = compare(late, Forecast(likes_1d=100, likes_1h=None, relative_to_median=1.0, drivers=()))
    assert day.likes_at_30 == 95 and day.predicted_at_30 == 100 and day.verdict == "on track at 3 days"
    assert compare(Curve(post, ()), day.forecast).verdict == "no observations yet"
