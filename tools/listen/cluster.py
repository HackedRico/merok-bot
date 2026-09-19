from __future__ import annotations

from typing import Any

import duckdb
import pyarrow as pa

from shared.data import latest
from shared.embed import Embedder, cosine
from shared.text import normalise

# =============================================================================
# Module Overview
# =============================================================================
# Exact-match clustering on normalised text, done in DuckDB over the Arrow
# table. One row out per cluster with the counts, the author ids, sample
# ids, the per-hour curve and the shares the spam verdict needs. Near-
# duplicate groups are then folded together by embedding similarity, so one
# crypto copy with fifty swapped links is one template, not fifty.

TIKTOK_COLUMNS = ("video_id", "creator_id", "music_id", "music_title", "created_at")


def with_normalised(tweets: pa.Table) -> pa.Table:
    """The table with a `normalised` column computed by the one shared normaliser."""
    bodies = tweets.column("body").to_pylist()
    return tweets.append_column("normalised", pa.array([normalise(b or "") for b in bodies], pa.string()))


def cluster_templates(tweets: pa.Table, min_authors: int, min_chars: int) -> list[dict[str, Any]]:
    """Group the final state of each tweet by normalised text; keep groups with enough authors."""
    final = with_normalised(latest(tweets))
    con = duckdb.connect()
    con.register("t", final)
    # `curve` is one struct per UTC hour, ordered, so the caller can turn it into HourCounts directly.
    sql = f"""
        WITH hourly AS (
            SELECT normalised, date_trunc('hour', created_at AT TIME ZONE 'UTC') AS hour,
                   count(DISTINCT author_id) AS authors, count(*) AS posts
            FROM t GROUP BY 1, 2
        ),
        curves AS (
            SELECT normalised, list(struct_pack(hour := hour, authors := authors, posts := posts) ORDER BY hour) AS curve
            FROM hourly GROUP BY 1
        ),
        groups AS (
            SELECT normalised,
                   arg_min(body, created_at) AS text,
                   count(DISTINCT author_id) AS authors,
                   count(*) AS posts,
                   min(created_at) AS first_seen,
                   list(DISTINCT author_id ORDER BY author_id) AS author_ids,
                   list(id ORDER BY created_at)[1:5] AS sample_ids,
                   avg(CASE WHEN has_link THEN 1.0 ELSE 0.0 END) AS link_share,
                   avg(CASE WHEN coalesce(views_count, 0) = 0 THEN 1.0 ELSE 0.0 END) AS zero_views_share
            FROM t
            WHERE length(normalised) >= {int(min_chars)}
            GROUP BY normalised
            HAVING count(DISTINCT author_id) >= {int(min_authors)}
        )
        SELECT g.*, c.curve
        FROM groups g JOIN curves c USING (normalised)
        ORDER BY authors DESC, posts DESC
    """
    return _rows(con.execute(sql))


def cluster_sounds(videos: pa.Table, min_creators: int) -> list[dict[str, Any]]:
    """Group videos by music id; the TikTok twin of `cluster_templates`."""
    missing = [c for c in TIKTOK_COLUMNS if c not in videos.column_names]
    if missing:
        raise ValueError(f"videos table is missing columns {missing}; expected {TIKTOK_COLUMNS}")
    con = duckdb.connect()
    con.register("v", videos)
    sql = f"""
        WITH hourly AS (
            SELECT music_id, date_trunc('hour', created_at AT TIME ZONE 'UTC') AS hour,
                   count(DISTINCT creator_id) AS authors, count(*) AS posts
            FROM v GROUP BY 1, 2
        ),
        curves AS (
            SELECT music_id, list(struct_pack(hour := hour, authors := authors, posts := posts) ORDER BY hour) AS curve
            FROM hourly GROUP BY 1
        ),
        groups AS (
            SELECT music_id, arg_min(music_title, created_at) AS title,
                   count(DISTINCT creator_id) AS creators, count(*) AS videos, min(created_at) AS first_seen
            FROM v GROUP BY music_id HAVING count(DISTINCT creator_id) >= {int(min_creators)}
        )
        SELECT g.*, c.curve FROM groups g JOIN curves c USING (music_id)
        ORDER BY creators DESC, videos DESC
    """
    return _rows(con.execute(sql))


def merge_variants(rows: list[dict[str, Any]], embedder: Embedder, threshold: float = 0.75) -> list[dict[str, Any]]:
    """Fold near-duplicate groups into the largest one: the same copy with a swapped link, number or greeting is one template."""
    if len(rows) < 2:
        return rows
    ordered = sorted(rows, key=lambda r: (-r["authors"], -r["posts"]))
    vectors = embedder.embed([r["normalised"] for r in ordered])
    sims = cosine(vectors, vectors)
    # Union-find so a chain of variants (A like B, B like C) lands in one group under its largest member.
    root = list(range(len(ordered)))

    def find(i: int) -> int:
        while root[i] != i:
            root[i] = root[root[i]]
            i = root[i]
        return i

    for j in range(len(ordered)):
        for i in range(j):
            if sims[i, j] >= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    root[max(ri, rj)] = min(ri, rj)
    merged: dict[int, dict[str, Any]] = {}
    for j, r in enumerate(ordered):
        i = find(j)
        if i == j:
            merged[i] = {**r, "author_ids": set(r["author_ids"]), "variants": 1}
            continue
        m = merged[i]
        total = m["posts"] + r["posts"]
        # Shares are re-weighted by posts; the hourly curves are summed, which can double-count an
        # account that posted two variants in one hour, and that is rare enough to say rather than fix.
        m["link_share"] = (m["link_share"] * m["posts"] + r["link_share"] * r["posts"]) / total
        m["zero_views_share"] = (m["zero_views_share"] * m["posts"] + r["zero_views_share"] * r["posts"]) / total
        m["posts"] = total
        m["author_ids"] |= set(r["author_ids"])
        m["first_seen"] = min(m["first_seen"], r["first_seen"])
        m["curve"] = _sum_curves(m["curve"], r["curve"])
        m["variants"] += 1
    out = []
    for m in merged.values():
        m["authors"] = len(m["author_ids"])
        m["author_ids"] = sorted(m["author_ids"])
        out.append(m)
    return sorted(out, key=lambda r: (-r["authors"], -r["posts"]))


def _sum_curves(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_hour: dict[Any, dict[str, Any]] = {}
    for point in list(a) + list(b):
        slot = by_hour.setdefault(point["hour"], {"hour": point["hour"], "authors": 0, "posts": 0})
        slot["authors"] += int(point["authors"])
        slot["posts"] += int(point["posts"])
    return [by_hour[h] for h in sorted(by_hour)]


def _rows(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
