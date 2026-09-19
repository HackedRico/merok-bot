from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pyarrow as pa
import pytest

from shared.data import latest
from shared.embed import HashEmbedder
from shared.types import Context
from tools.score import Traction, baseline_for, leave_one_out_medians
from tools.score.baseline import author_baselines


@pytest.fixture(scope="module")
def split(hour_table: pa.Table) -> tuple[pa.Table, pa.Table]:
    ids = latest(hour_table).column("id").to_pylist()
    rng = np.random.default_rng(3)
    held = set(rng.choice(ids, size=len(ids) // 5, replace=False).tolist())
    mask = pa.array([i in held for i in hour_table.column("id").to_pylist()])
    return hour_table.filter(pa.compute.invert(mask)), hour_table.filter(mask)


@pytest.fixture(scope="module")
def traction(split: tuple[pa.Table, pa.Table], embedder: HashEmbedder) -> Traction:
    return Traction.fit(split[0], embedder, max_rows=25_000)


def test_leave_one_out_never_sees_its_own_label() -> None:
    median, known = leave_one_out_medians(["a", "a", "a", "b"], [0, 10, 1000, 5])
    assert known.tolist() == [1.0, 1.0, 1.0, 0.0]
    assert median[0] == 505.0 and median[2] == 5.0 and median[3] == 0.0


def test_baselines_measure_the_bar(gov_table: pa.Table) -> None:
    b = author_baselines(gov_table, author_col="author_handle")["sensanders"]
    assert b.posts == gov_table.num_rows and b.median_likes > 50
    assert baseline_for("nobody", []).posts == 0


def test_model_beats_predict_the_median_on_held_out_rows(traction: Traction, split: tuple[pa.Table, pa.Table]) -> None:
    ev = traction.evaluate(split[1])
    assert ev.rows > 5_000
    assert ev.beats_baseline, f"model MAE {ev.mae_model:.3f} vs median baseline {ev.mae_median_baseline:.3f}"


def test_forecast_is_relative_and_explained(traction: Traction) -> None:
    author = baseline_for("sensanders", [300, 450, 500, 700, 1200])
    ctx = Context(posted_at=datetime(2026, 9, 19, 14, 0, tzinfo=timezone.utc), has_media=False, has_link=False, template_velocity=24)
    f = traction.predict("Do you remember when you joined X? I do! Thursday's town hall is at 6pm.", author, ctx)
    assert f.likes_1d >= 0 and f.relative_to_median > 0
    assert 1 <= len(f.drivers) <= 5 and all(d.detail for d in f.drivers)
