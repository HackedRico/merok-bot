from __future__ import annotations

from typing import Any

import duckdb
import pyarrow as pa

from shared.data import latest
from shared.text import normalise

# =============================================================================
# Module Overview
# =============================================================================
# Exact-match clustering on normalised text, done in DuckDB over the Arrow
# table. One row out per cluster with the counts, the first authors, sample
# ids, the per-hour curve and the shares the spam verdict needs. MinHash for
# near-duplicates is the next step and is not here yet.

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
                   list(DISTINCT author_id ORDER BY author_id)[1:5] AS first_authors,
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


def _rows(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
