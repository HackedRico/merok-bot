from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pyarrow as pa
import pytest

from shared.data import curves, latest
from shared.embed import HashEmbedder, cosine
from shared.llm.fake import FakeLLM
from shared.text import has_link, normalise, truncate, word_count
from shared.types import Message, SpamVerdict, Template, to_json


def test_normalise_strips_what_a_template_should_not_key_on() -> None:
    body = "Do you REMEMBER when you joined X? I do! https://t.co/abc @someone #memories  "
    assert normalise(body) == "do you remember when you joined x? i do!"
    assert has_link(body) and not has_link("no link here")
    assert word_count("one two  three") == 3
    assert truncate("abcdefgh", 6) == "abc..."


def test_hash_embedder_is_deterministic_and_puts_like_with_like() -> None:
    emb = HashEmbedder(dim=256)
    a = emb.embed(["the senator will hold a town hall thursday"])
    b = emb.embed(["the senator will hold a town hall thursday"])
    c = emb.embed(["claim your airdrop now, link in bio"])
    assert np.allclose(a, b)
    assert cosine(a, a)[0, 0] == pytest.approx(1.0, abs=1e-5)
    assert cosine(a, c)[0, 0] < 0.5


def test_fixture_hour_has_the_shared_shape(hour_table: pa.Table) -> None:
    assert {"id", "author_id", "body", "created_at", "like_count", "version", "has_media", "has_link"} <= set(hour_table.column_names)
    assert hour_table.num_rows > 50_000


def test_latest_keeps_one_row_per_id_and_curves_measure_minutes(hour_table: pa.Table) -> None:
    final = latest(hour_table)
    ids = final.column("id").to_pylist()
    assert len(ids) == len(set(ids))
    assert final.num_rows < hour_table.num_rows, "the hour has repeat snapshots, so latest() must drop some"
    traj = curves(hour_table)
    assert "minutes" in traj.column_names
    assert min(traj.column("minutes").to_pylist()) >= 0


def test_fake_llm_cycles_and_records(fake_llm: FakeLLM) -> None:
    msgs = [Message("user", "hi")]
    assert fake_llm.complete("sys", msgs) == "reply one"
    assert fake_llm.complete("sys", msgs) == "reply two"
    assert fake_llm.complete("sys", msgs) == "reply one"
    assert len(fake_llm.calls) == 3


def test_to_json_flattens_frozen_values() -> None:
    t = Template(
        text="x", normalised="x", authors=3, posts=3, first_seen=datetime(2026, 8, 29, tzinfo=timezone.utc),
        first_authors=("a",), sample_ids=("1",), curve=(), spam=SpamVerdict(0.2, ("few links",)),
    )
    j = to_json(t)
    assert j["first_seen"].startswith("2026-08-29")
    assert j["spam"]["reasons"] == ["few links"]


def test_slang_lexicon_matches_whole_words_only() -> None:
    from shared.slang import slang_hits, uses_slang

    assert slang_hits("POV: you lowkey love the farm bill 💀") == ("pov:", "lowkey", "💀")
    assert not uses_slang("The capital budget passed.")
    assert not uses_slang("recapitulate")
