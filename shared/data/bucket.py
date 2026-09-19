from __future__ import annotations

from typing import Sequence

import duckdb
import pyarrow as pa

from shared.data import firehose_select, gov_select

# =============================================================================
# Module Overview
# =============================================================================
# The sponsor's public bucket, read over HTTPS with DuckDB range requests. One
# firehose file is about one hour and 140 MB; a projected, filtered read of it
# takes about eight seconds. Nothing is downloaded whole.

BASE = "https://calcifer-hot.s3.us-east-2.amazonaws.com/hopkins-hackathon-2026"
FIREHOSE_FILES = 396
GOV_URL = f"{BASE}/gov-tweets-unified.parquet"


def firehose_url(index: int) -> str:
    """The URL of one hour file; files are in id order, so index order is time order."""
    if not 0 <= index < FIREHOSE_FILES:
        raise ValueError(f"file index must be in [0, {FIREHOSE_FILES}), got {index}")
    return f"{BASE}/twitter-firehose-last-month/tweets-{index:06d}.parquet"


class BucketSource:
    """Adapter: the public bucket over HTTPS."""

    name = "bucket"

    def __init__(self) -> None:
        self._con = duckdb.connect()
        self._con.execute("INSTALL httpfs; LOAD httpfs;")

    def firehose(self, files: Sequence[int] | None = None, lang: str | None = "en", originals_only: bool = True) -> pa.Table:
        # File 300 is a quiet UTC evening on August 29; the number the brief cites came from it.
        chosen = list(files) if files else [300]
        urls = ", ".join(f"'{firehose_url(i)}'" for i in chosen)
        sql = firehose_select(f"read_parquet([{urls}])", lang, originals_only)
        return self._con.execute(sql).to_arrow_table()

    def gov_tweets(self, handles: Sequence[str] | None = None) -> pa.Table:
        return self._con.execute(gov_select(f"read_parquet('{GOV_URL}')", handles)).to_arrow_table()

    def tiktok(self) -> pa.Table:
        raise PermissionError(
            "the TikTok shards are gated on Hugging Face; set `HF_TOKEN` and use scripts/pull_sounds.py, "
            "or read them from a cached parquet through `LocalSource`"
        )
