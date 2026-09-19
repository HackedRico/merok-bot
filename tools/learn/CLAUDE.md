# tools/learn

Learn: real versus forecast. `observe(post, minutes, source: Poller) -> Curve` collects likes
over the first minutes of a post's life; `compare(curve, forecast) -> Comparison` reads both
at the thirty-minute mark and says ahead, behind or on track.

Adapters: `ReplayPoller` serves a real trajectory from the firehose's repeat snapshots, so the
screen can be rehearsed without posting; the live X poller is Part 2.

Invariants: curve points are in minute order. `compare` reads the curve at thirty minutes
when it has a point there and a one-hour forecast exists (a linear ramp to the hour), else
at its last point against the one-day forecast, and the verdict names the checkpoint.

Gotchas: the firehose first observes a tweet hours to days after creation, so replayed curves
start late and the checkpoint is usually days. Live thirty-minute curves need the X poller.

Test: `uv run pytest tests/test_learn.py`.
