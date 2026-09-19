from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import duckdb
import pyarrow as pa

from shared.data import DataSource, gov_select

# =============================================================================
# Module Overview
# =============================================================================
# The local adapter: parquet files under `.cache/` that `scripts/pull_month.py`
# and `scripts/pull_gov.py` materialise from the bucket. When a file is not
# there yet it logs and falls back to the fixture, so the app runs on a fresh
# clone and gets better as the pulls land.

log = logging.getLogger(__name__)

FIREHOSE_DIR = "firehose_en"
GOV_FILE = "gov-tweets-unified.parquet"
TIKTOK_FILE = "tiktok_sounds.parquet"


class LocalSource:
    """Adapter: the materialised month on disk, with a fixture fallback per table."""

    name = "local"

    def __init__(self, cache_dir: Path, fallback: DataSource) -> None:
        self.cache_dir = Path(cache_dir)
        self.fallback = fallback
        self._con = duckdb.connect()

    def firehose(self, files: Sequence[int] | None = None, lang: str | None = "en", originals_only: bool = True) -> pa.Table:
        directory = self.cache_dir / FIREHOSE_DIR
        parts = sorted(directory.glob("*.parquet")) if directory.is_dir() else []
        if files:
            wanted = {f"{i:06d}" for i in files}
            parts = [p for p in parts if p.stem.split("-")[-1] in wanted]
        if not parts:
            log.warning("[LocalSource] no cached firehose files under %s; falling back to the fixture. Run scripts/pull_month.py.", directory)
            return self.fallback.firehose(files, lang, originals_only)
        urls = ", ".join(f"'{p}'" for p in parts)
        return self._con.execute(f"SELECT * FROM read_parquet([{urls}])").to_arrow_table()

    def gov_tweets(self, handles: Sequence[str] | None = None) -> pa.Table:
        path = self.cache_dir / GOV_FILE
        if not path.is_file():
            log.warning("[LocalSource] %s is missing; falling back to the fixture. Run scripts/pull_gov.py.", path)
            return self.fallback.gov_tweets(handles)
        return self._con.execute(gov_select(f"read_parquet('{path}')", handles)).to_arrow_table()

    def tiktok(self) -> pa.Table:
        path = self.cache_dir / TIKTOK_FILE
        if not path.is_file():
            log.warning("[LocalSource] %s is missing; falling back to the fixture. Run scripts/pull_sounds.py.", path)
            return self.fallback.tiktok()
        return self._con.execute(f"SELECT * FROM read_parquet('{path}')").to_arrow_table()
