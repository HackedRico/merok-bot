from __future__ import annotations

import json

import pyarrow as pa
import pytest

from shared.embed import HashEmbedder
from shared.llm.fake import FakeLLM
from tools.draft import draft, retrieve, turing_test
from tools.draft.prompt import parse_candidates


def test_retrieve_finds_the_authors_posts_nearest_the_intent(gov_table: pa.Table, embedder: HashEmbedder) -> None:
    ex = retrieve(gov_table, "sensanders", "health care is a human right", k=5, embedder=embedder)
    assert len(ex.posts) == 5 and ex.median_likes > 0
    assert any("health" in p.lower() for p in ex.posts)
    assert not any(p.startswith("RT @") for p in ex.posts)


def test_draft_returns_five_candidates_from_json(gov_table: pa.Table, embedder: HashEmbedder) -> None:
    ex = retrieve(gov_table, "sensanders", "town hall", k=3, embedder=embedder)
    canned = json.dumps([{"text": f"Post number {i}.", "why": "short"} for i in range(1, 7)])
    llm = FakeLLM([canned])
    out = draft("announce Thursday's town hall", ex, None, llm)
    assert [c.text for c in out] == [f"Post number {i}." for i in range(1, 6)]
    assert "@sensanders" in llm.calls[0][0]
    assert ex.posts[0] in llm.calls[0][0]


def test_parser_falls_back_to_numbered_lines_and_refuses_too_few() -> None:
    lines = "\n".join(f"{i}. Draft {i} here" for i in range(1, 6))
    assert [t for t, _ in parse_candidates(lines)] == [f"Draft {i} here" for i in range(1, 6)]
    with pytest.raises(ValueError):
        parse_candidates("1. only one")


def test_turing_test_scores_copies_near_chance_and_junk_high(gov_table: pa.Table, embedder: HashEmbedder) -> None:
    real = [t for t in gov_table.column("text").to_pylist() if t and not t.startswith("RT @")]
    copies = real[:8]
    junk = ["claim ur airdrop now!!! 🚀🚀🚀 link in bio"] * 4 + ["gm gm wagmi ser", "lol skibidi rizz fr fr", "buy $TOKEN presale live", "rt to win"]
    assert turing_test(copies, real[8:], embedder) < 0.7
    assert turing_test(junk, real, embedder) > 0.8
