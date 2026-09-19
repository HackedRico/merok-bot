#!/usr/bin/env python3
"""Chart 1: distinct authors per hour for the most replicated templates in the cached day,
organic and paid drawn apart. Reads through `shared.data` and `tools.listen` so the chart and
the app compute the same numbers; this file only plots.

Usage:
    uv run python analysis/template_curves.py [--top 8] [--min-authors 5]
Writes analysis/out/template_curves.png and analysis/out/template_curves.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.config import load_settings  # noqa: E402
from shared.data import make_source  # noqa: E402
from shared.text import truncate  # noqa: E402
from shared.types import to_json  # noqa: E402
from tools.listen import listen  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--min-authors", type=int, default=5)
    args = ap.parse_args()

    settings = load_settings()
    source = make_source(settings)
    tweets = source.firehose()
    templates = listen(tweets, min_authors=args.min_authors, max_templates=args.top)
    if not templates:
        raise SystemExit("no templates found; is the cache or fixture present?")

    OUT.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6))
    for t in templates:
        hours = [h.hour for h in t.curve]
        authors = [h.authors for h in t.curve]
        paid = t.spam.is_spam
        ax.plot(
            hours, authors, marker="o", linewidth=2 if not paid else 1.5,
            linestyle="-" if not paid else "--", alpha=0.95 if not paid else 0.7,
            label=f"{'paid' if paid else 'organic'} · {t.authors} authors · {truncate(t.normalised, 42)}",
        )
    ax.set_title(f"Templates spread, not posts: distinct authors per hour, {tweets.num_rows:,} English originals", fontsize=13)
    ax.set_ylabel("distinct authors in the hour")
    ax.set_xlabel("UTC")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / "template_curves.png", dpi=160)
    (OUT / "template_curves.json").write_text(json.dumps(to_json(templates), indent=1))
    print(f"wrote {OUT / 'template_curves.png'} with {len(templates)} templates from {source.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
