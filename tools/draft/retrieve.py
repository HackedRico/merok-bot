from __future__ import annotations

import numpy as np
import pyarrow as pa

from shared.embed import Embedder, cosine
from shared.types import Exemplars

# =============================================================================
# Module Overview
# =============================================================================
# The author's own posts nearest an intent, by embedding. Replies and
# retweets are dropped first: they are reactions in a thread, not the voice.


def retrieve(posts: pa.Table, author: str, intent: str, k: int, embedder: Embedder, text_col: str = "text", likes_col: str = "like_count") -> Exemplars:
    """The `k` posts by `author` most similar to `intent`, plus the author's median likes over all of them."""
    if k < 1:
        raise ValueError("k must be at least 1")
    for col in (text_col, likes_col):
        if col not in posts.column_names:
            raise ValueError(f"posts table is missing {col!r}")
    texts = posts.column(text_col).to_pylist()
    likes = posts.column(likes_col).to_pylist()
    replies = posts.column("in_reply_to_tweet_id").to_pylist() if "in_reply_to_tweet_id" in posts.column_names else [None] * len(texts)
    # The government file writes '0' for an original post, not null.
    keep = [i for i, t in enumerate(texts) if t and not t.startswith("RT @") and replies[i] in (None, "", "0")]
    if not keep:
        raise ValueError(f"no original posts for {author!r}")
    own = [texts[i] for i in keep]
    own_likes = [int(likes[i] or 0) for i in keep]
    sims = cosine(embedder.embed([intent]), embedder.embed(own))[0]
    order = np.argsort(-sims)[:k]
    return Exemplars(author=author, posts=tuple(own[i] for i in order), median_likes=float(np.median(own_likes)))
