#!/usr/bin/env python3
"""Cache the government tweet file locally: 263 MB, 2.16M rows, every official and campaign
account in the roster, engagement counts included. One download; chart 2 and the demo user's
history read it from .cache/ afterwards.

Usage:
    uv run python scripts/pull_gov.py
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.config import load_settings  # noqa: E402
from shared.data.bucket import GOV_URL  # noqa: E402
from shared.data.cache import GOV_FILE  # noqa: E402


def main() -> int:
    out = load_settings().cache_dir / GOV_FILE
    if out.exists():
        print(f"{out} already cached")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    tmp = out.with_suffix(".tmp")
    urllib.request.urlretrieve(GOV_URL, tmp)
    tmp.rename(out)
    print(f"{out.name}: {out.stat().st_size / 1e6:.0f} MB in {time.time() - t:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
