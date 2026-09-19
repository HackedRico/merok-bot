#!/usr/bin/env python3
"""Chart 2: government learned to meme. For each month since 2019, the share of official
congressional posts that use the slang and meme-format lexicon, and the engagement those
posts earned against the same accounts' other posts in the same month.

The baseline is per account and per month on purpose: engagement rose for nearly every
official account after January 2025 for reasons unrelated to format, so a raw before-and-after
would confound meme adoption with the regime change. Reads the government table through
`shared.data`; this file only aggregates and plots.

Usage:
    uv run python analysis/gov_memes.py [--since 2019-01]
Writes analysis/out/gov_memes.png and analysis/out/gov_memes.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import matplotlib
import pyarrow as pa

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.config import load_settings  # noqa: E402
from shared.data import make_source  # noqa: E402
from shared.slang import uses_slang  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def monthly(gov: pa.Table, since: str) -> list[dict]:
    """Per month: posts, slang share, and the median-likes ratio of slang posts to other posts within the same account."""
    texts = gov.column("text").to_pylist()
    flagged = gov.append_column("slang", pa.array([uses_slang(t) for t in texts], pa.bool_()))
    con = duckdb.connect()
    con.register("g", flagged)
    rows = con.execute(
        f"""
        WITH base AS (
            SELECT strftime(created_at, '%Y-%m') AS month, author_handle, slang, like_count
            FROM g
            WHERE account_kind = 'official' AND created_at >= '{since}-01' AND NOT starts_with(text, 'RT @')
        ),
        per_account AS (
            SELECT month, author_handle,
                   median(like_count) FILTER (WHERE slang) AS slang_med,
                   median(like_count) FILTER (WHERE NOT slang) AS other_med,
                   count(*) FILTER (WHERE slang) AS slang_n
            FROM base GROUP BY 1, 2
        )
        SELECT b.month,
               count(*) AS posts,
               avg(CASE WHEN b.slang THEN 1.0 ELSE 0.0 END) AS slang_share,
               count(DISTINCT b.author_handle) FILTER (WHERE b.slang) AS accounts_using,
               median(p.slang_med / greatest(p.other_med, 1.0)) FILTER (WHERE p.slang_n >= 3 AND p.other_med IS NOT NULL) AS lift
        FROM base b JOIN per_account p USING (month, author_handle)
        GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    return [dict(zip(("month", "posts", "slang_share", "accounts_using", "lift"), r)) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2019-01")
    args = ap.parse_args()

    source = make_source(load_settings())
    gov = source.gov_tweets()
    rows = monthly(gov, args.since)
    if not rows:
        raise SystemExit("no government rows; run scripts/pull_gov.py")

    OUT.mkdir(exist_ok=True)
    months = [r["month"] for r in rows]
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(months, [100 * r["slang_share"] for r in rows], color="#C8481A", alpha=0.85, label="share of official posts using the slang lexicon")
    ax1.set_ylabel("% of official posts with slang or a meme format")
    ax1.tick_params(axis="x", labelrotation=90, labelsize=7)
    ax2 = ax1.twinx()
    lifts = [r["lift"] if r["lift"] is not None else float("nan") for r in rows]
    ax2.plot(months, lifts, color="#1B211F", marker=".", linewidth=1.5, label="median lift: slang posts vs the same account's other posts, same month")
    ax2.axhline(1.0, color="#9AA6A0", linewidth=1, linestyle="--")
    ax2.set_ylabel("engagement lift (1.0 = no different)")
    ax1.set_title(f"Government learned to meme: {gov.num_rows:,} tweets by official congressional accounts, per account per month", fontsize=12)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "gov_memes.png", dpi=160)
    (OUT / "gov_memes.json").write_text(json.dumps(rows, indent=1, default=str))
    print(f"wrote {OUT / 'gov_memes.png'} over {len(rows)} months from {source.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
