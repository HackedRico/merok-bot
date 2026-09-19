from __future__ import annotations

import logging
from typing import Protocol, Sequence

import duckdb
import pyarrow as pa

from shared.config import Settings

# =============================================================================
# Module Overview
# =============================================================================
# The lake seam. `DataSource` is the interface every tool reads through;
# `BucketSource`, `LocalSource` and `FixtureSource` are its adapters. Tables
# cross the seam as immutable `pyarrow.Table`s, and `latest` and `curves` are
# the two derived views everything needs: final state per tweet, and the
# like-count trajectory per tweet.

log = logging.getLogger(__name__)

# The columns every adapter projects the firehose down to, in this order.
FIREHOSE_COLUMNS = (
    "id",
    "author_id",
    "body",
    "created_at",
    "like_count",
    "retweet_count",
    "reply_count",
    "views_count",
    "lang",
    "has_media",
    "has_link",
    "version",
)

GOV_COLUMNS = (
    "tweet_id",
    "author_id",
    "author_handle",
    "person",
    "party",
    "account_kind",
    "author_followers",
    "created_at",
    "text",
    "lang",
    "like_count",
    "retweet_count",
    "reply_count",
    "view_count",
    "in_reply_to_tweet_id",
)


class DataSource(Protocol):
    """Where tables come from; adapters differ in origin, never in shape."""

    name: str

    def firehose(self, files: Sequence[int] | None = None, lang: str | None = "en", originals_only: bool = True) -> pa.Table: ...

    def gov_tweets(self, handles: Sequence[str] | None = None) -> pa.Table: ...

    def tiktok(self) -> pa.Table: ...


# -----------------------------------------------------------------
# SQL fragments the adapters share
# -----------------------------------------------------------------


def firehose_select(source_sql: str, lang: str | None, originals_only: bool) -> str:
    """The projection and filters that turn a raw firehose scan into the shared shape."""
    where = ["length(id) = 19"]
    if lang:
        where.append(f"lang = '{lang}'")
    if originals_only:
        # Retweets carry the original's text; replies ride a thread, not a template.
        where.append("NOT starts_with(body, 'RT @')")
        where.append("reply_to_status_id IS NULL")
    return f"""
        SELECT id, author_id, body, created_at,
               like_count, retweet_count, reply_count, views_count, lang,
               (media IS NOT NULL AND CAST(media AS VARCHAR) NOT IN ('', '[]', 'null')) AS has_media,
               regexp_matches(body, 'https?://') AS has_link,
               version
        FROM {source_sql}
        WHERE {' AND '.join(where)}
    """


def gov_select(source_sql: str, handles: Sequence[str] | None) -> str:
    """Project the government file to the shared shape, optionally for a few handles."""
    where = "TRUE"
    if handles:
        quoted = ", ".join("'" + h.lower().replace("'", "") + "'" for h in handles)
        where = f"lower(author_handle) IN ({quoted})"
    return f"SELECT {', '.join(GOV_COLUMNS)} FROM {source_sql} WHERE {where}"


# -----------------------------------------------------------------
# Derived views
# -----------------------------------------------------------------


def latest(table: pa.Table) -> pa.Table:
    """One row per tweet id, the highest `version`: the final state."""
    _require_columns(table, ("id", "version"))
    con = duckdb.connect()
    con.register("t", table)
    return con.execute(
        "SELECT * FROM t QUALIFY row_number() OVER (PARTITION BY id ORDER BY version DESC) = 1"
    ).to_arrow_table()


def curves(table: pa.Table) -> pa.Table:
    """Every observation of every tweet with minutes since creation: the trajectory view."""
    _require_columns(table, ("id", "version", "created_at", "like_count"))
    con = duckdb.connect()
    con.register("t", table)
    return con.execute(
        """
        SELECT id, author_id, created_at, version, like_count, views_count,
               date_diff('second', created_at, version) / 60.0 AS minutes
        FROM t
        ORDER BY id, version
        """
    ).to_arrow_table()


def _require_columns(table: pa.Table, columns: Sequence[str]) -> None:
    missing = [c for c in columns if c not in table.column_names]
    if missing:
        raise ValueError(f"table is missing columns {missing}; read it through `shared.data`")


# -----------------------------------------------------------------
# Factory
# -----------------------------------------------------------------


def make_source(settings: Settings) -> DataSource:
    """Build the data source a settings value names."""
    from shared.data.cache import LocalSource
    from shared.data.fixture import FixtureSource

    if settings.data_source == "fixture":
        return FixtureSource(settings.fixtures_dir)
    if settings.data_source == "local":
        return LocalSource(settings.cache_dir, fallback=FixtureSource(settings.fixtures_dir))
    raise ValueError(f"unknown data source {settings.data_source!r}")
