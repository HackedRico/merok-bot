#!/usr/bin/env python3
"""Cut the test fixtures from the bucket: one firehose hour of English originals and the demo
account's tweets from the government file.

Learned 2026-09-19: file 300 (a UTC evening on August 29) holds 97k English original rows,
87k distinct tweets, and 30 templates at five or more authors; the brief's number reproduces
from it, so the fixture keeps every version row (the curves need them). The government file
is 263 MB and DuckDB scans it whole over HTTPS in about ten seconds; one account is a few
thousand rows, so the fixture keeps the most recent 3,000 for retrieval and the Turing test.
The TikTok shards are gated on Hugging Face and need `HF_TOKEN`; see pull_sounds.py.

Usage:
    uv run python scripts/make_fixture.py [--file 300] [--handle sensanders]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.data.bucket import BucketSource  # noqa: E402
from shared.data.fixture import FIREHOSE_FIXTURE, GOV_FIXTURE  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=int, default=300, help="firehose file index, one hour")
    ap.add_argument("--handle", default="sensanders", help="government account for the demo user")
    ap.add_argument("--gov-rows", type=int, default=3000, help="most recent rows to keep for the handle")
    ap.add_argument("--out", default="tests/fixtures")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    source = BucketSource()

    hour = source.firehose(files=[args.file])
    pq.write_table(hour, out / FIREHOSE_FIXTURE, compression="zstd")
    print(f"{FIREHOSE_FIXTURE}: {hour.num_rows} rows, {(out / FIREHOSE_FIXTURE).stat().st_size / 1e6:.1f} MB")

    gov = source.gov_tweets([args.handle])
    con = duckdb.connect()
    con.register("gov", gov)
    recent = con.execute(f"SELECT * FROM gov ORDER BY created_at DESC LIMIT {args.gov_rows}").to_arrow_table()
    pq.write_table(recent, out / GOV_FIXTURE, compression="zstd")
    print(f"{GOV_FIXTURE}: {recent.num_rows} rows for @{args.handle}, {(out / GOV_FIXTURE).stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
