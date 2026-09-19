from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np
import pyarrow as pa

from shared.types import AuthorBaseline

# =============================================================================
# Module Overview
# =============================================================================
# The bar a forecast is measured against: an author's median likes. For the
# demo user that is a history of thousands of posts; for a firehose training
# row it is the author's other posts in the same table, never the row itself.

MIN_HISTORY = 2


def baseline_for(author: str, likes: Sequence[int]) -> AuthorBaseline:
    """Median likes over an author's posts; `posts` says how much history backs it."""
    values = [int(v) for v in likes if v is not None]
    if not values:
        return AuthorBaseline(author=author, median_likes=0.0, posts=0)
    return AuthorBaseline(author=author, median_likes=float(np.median(values)), posts=len(values))


def author_baselines(table: pa.Table, author_col: str = "author_id", likes_col: str = "like_count") -> dict[str, AuthorBaseline]:
    """One baseline per author from a table with an author column and a likes column."""
    if author_col not in table.column_names or likes_col not in table.column_names:
        raise ValueError(f"table needs columns {author_col!r} and {likes_col!r}")
    by_author: dict[str, list[int]] = defaultdict(list)
    for author, likes in zip(table.column(author_col).to_pylist(), table.column(likes_col).to_pylist()):
        if author is not None and likes is not None:
            by_author[str(author)].append(int(likes))
    return {a: baseline_for(a, v) for a, v in by_author.items()}


def leave_one_out_medians(authors: Sequence[str], likes: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    """Per row: the median of the author's other rows, and a flag saying whether there were enough of them."""
    if len(authors) != len(likes):
        raise ValueError("authors and likes must have the same length")
    positions: dict[str, list[int]] = defaultdict(list)
    for i, a in enumerate(authors):
        positions[str(a)].append(i)
    values = np.asarray(likes, dtype=np.float64)
    median = np.zeros(len(likes), dtype=np.float64)
    known = np.zeros(len(likes), dtype=np.float64)
    for idx in positions.values():
        if len(idx) <= MIN_HISTORY:
            continue
        arr = values[idx]
        for j, i in enumerate(idx):
            others = np.delete(arr, j)
            median[i] = float(np.median(others))
            known[i] = 1.0
    return median, known
