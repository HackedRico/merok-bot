from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyarrow as pa

from tools.listen import listen, sounds
from tools.listen.curve import velocity


def test_the_fixture_hour_reproduces_the_briefs_number(hour_table: pa.Table) -> None:
    templates = listen(hour_table, min_authors=5)
    assert len(templates) >= 25, f"expected the hour to hold about 30 templates at 5+ authors, got {len(templates)}"
    # Two organic memes lead the hour: the Grok report-card prompt and X's join-date share card.
    top = templates[0]
    assert "report card" in top.normalised or "remember when you joined" in top.normalised
    assert top.authors >= 20
    for t in templates:
        assert sum(h.posts for h in t.curve) == t.posts
        assert 0.0 <= t.spam.score <= 1.0 and t.spam.reasons


def test_organic_and_paid_replication_are_told_apart(hour_table: pa.Table) -> None:
    templates = listen(hour_table, min_authors=5)
    join_date = next(t for t in templates if "remember when you joined" in t.normalised)
    airdrop = next(t for t in templates if "airdrop" in t.normalised or "claim" in t.normalised)
    assert not join_date.spam.is_spam, join_date.spam.reasons
    assert airdrop.spam.is_spam, airdrop.spam.reasons


def test_sounds_are_templates_on_tiktok() -> None:
    t0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(30):
        rows.append(("v%d" % i, "creator%d" % (i % 12), "music-A", "song a", t0 + timedelta(minutes=7 * i)))
    for i in range(4):
        rows.append(("w%d" % i, "creator%d" % i, "music-B", "song b", t0))
    videos = pa.table(
        {
            "video_id": [r[0] for r in rows],
            "creator_id": [r[1] for r in rows],
            "music_id": [r[2] for r in rows],
            "music_title": [r[3] for r in rows],
            "created_at": pa.array([r[4] for r in rows], pa.timestamp("us", tz="UTC")),
        }
    )
    result = sounds(videos, min_creators=5)
    assert [s.music_id for s in result] == ["music-A"]
    assert result[0].creators == 12 and result[0].videos == 30
    assert velocity(result[0].curve) >= 1
