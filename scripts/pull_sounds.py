#!/usr/bin/env python3
"""Cache the music id columns of one TikTok shard as .cache/tiktok_sounds.parquet.

Learned 2026-09-19: the Hugging Face dataset `kuben-developer/tiktok-videos-4b` is gated, so
this needs `HF_TOKEN` in the environment, and the sponsor's S3 backup under `tiktok/` is not
public-listable. Until a token is at hand, `tools.listen.sounds` is exercised on a synthetic
table and the app's Render names no sound.

Usage:
    HF_TOKEN=hf_... uv run python scripts/pull_sounds.py --shard 0 --rows 200000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.config import load_settings  # noqa: E402
from shared.data.cache import TIKTOK_FILE  # noqa: E402

DATASET = "kuben-developer/tiktok-videos-4b"


def shard_urls(token: str) -> list[str]:
    req = urllib.request.Request(f"https://huggingface.co/api/datasets/{DATASET}/tree/main", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        tree = json.load(resp)
    return [f"https://huggingface.co/datasets/{DATASET}/resolve/main/{e['path']}" for e in tree if e["path"].endswith(".parquet")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--rows", type=int, default=200_000)
    args = ap.parse_args()
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise SystemExit("set HF_TOKEN; the dataset is gated")

    urls = shard_urls(token)
    if not urls:
        raise SystemExit("no parquet shards listed; check the dataset name")
    url = urls[args.shard % len(urls)]
    out = load_settings().cache_dir / TIKTOK_FILE
    out.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"CREATE SECRET hf (TYPE HUGGINGFACE, TOKEN '{token}')")
    # Column names follow the shard; adjust here once a shard has been inspected with DESCRIBE.
    con.execute(
        f"""
        COPY (
            SELECT video_id, author_id AS creator_id, music_id, music_title, create_time AS created_at
            FROM read_parquet('{url}') LIMIT {args.rows}
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
