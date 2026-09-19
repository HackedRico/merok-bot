#!/usr/bin/env python3
"""Materialise firehose hour files as English originals under .cache/firehose_en/, one
parquet per source file, resumable.

Learned 2026-09-19: a projected, filtered read of one 140 MB hour file over HTTPS takes about
eight seconds and leaves about 97k rows; a day is 22 files and four minutes, the month is
about an hour. Files are in id order, so index order is time order. File 300 starts at
2026-08-29 04:32 UTC.

Usage:
    uv run python scripts/pull_month.py --from 290 --to 313      # about one day
    uv run python scripts/pull_month.py                          # all 396 files
Re-running skips files that already exist.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.config import load_settings  # noqa: E402
from shared.data.bucket import FIREHOSE_FILES, BucketSource  # noqa: E402
from shared.data.cache import FIREHOSE_DIR  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--to", dest="end", type=int, default=FIREHOSE_FILES - 1, help="inclusive")
    args = ap.parse_args()
    if not 0 <= args.start <= args.end < FIREHOSE_FILES:
        raise SystemExit(f"--from and --to must satisfy 0 <= from <= to < {FIREHOSE_FILES}")

    out = load_settings().cache_dir / FIREHOSE_DIR
    out.mkdir(parents=True, exist_ok=True)
    source = BucketSource()
    for index in range(args.start, args.end + 1):
        path = out / f"tweets-{index:06d}.parquet"
        if path.exists():
            continue
        t = time.time()
        table = source.firehose(files=[index])
        # Write to a temp name so a killed run never leaves a truncated parquet behind.
        tmp = path.with_suffix(".tmp")
        pq.write_table(table, tmp, compression="zstd")
        tmp.rename(path)
        print(f"{path.name}: {table.num_rows} rows in {time.time() - t:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
