from __future__ import annotations

from pathlib import Path
from typing import Sequence

import duckdb
import pyarrow as pa

from shared.data import gov_select

# =============================================================================
# Module Overview
# =============================================================================
# The fixture adapter: the same interface as the bucket, served from the small
# parquet files under tests/fixtures. Tests run on it, and so does the demo if
# the venue wifi dies.

FIREHOSE_FIXTURE = "firehose_hour.parquet"
GOV_FIXTURE = "gov_sample.parquet"
TIKTOK_FIXTURE = "tiktok_sample.parquet"


class FixtureSource:
    """Adapter: parquet fixtures on disk, already projected to the shared shape."""

    name = "fixture"

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        if not self.directory.is_dir():
            raise FileNotFoundError(f"fixtures directory {self.directory} is missing; run `scripts/make_fixture.py`")
        self._con = duckdb.connect()

    def _path(self, name: str) -> Path:
        path = self.directory / name
        if not path.is_file():
            raise FileNotFoundError(f"fixture {path} is missing; run `scripts/make_fixture.py`")
        return path

    def firehose(self, files: Sequence[int] | None = None, lang: str | None = "en", originals_only: bool = True) -> pa.Table:
        # The fixture is already English originals, so `files`, `lang` and `originals_only` are accepted
        # for interface parity and have nothing left to filter.
        return self._con.execute(f"SELECT * FROM read_parquet('{self._path(FIREHOSE_FIXTURE)}')").to_arrow_table()

    def gov_tweets(self, handles: Sequence[str] | None = None) -> pa.Table:
        sql = gov_select(f"read_parquet('{self._path(GOV_FIXTURE)}')", handles)
        return self._con.execute(sql).to_arrow_table()

    def tiktok(self) -> pa.Table:
        return self._con.execute(f"SELECT * FROM read_parquet('{self._path(TIKTOK_FIXTURE)}')").to_arrow_table()
