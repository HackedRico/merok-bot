from __future__ import annotations

import pyarrow as pa

from shared.types import Sound, Template
from tools.listen.cluster import cluster_templates, cluster_sounds
from tools.listen.curve import hour_curve
from tools.listen.spam import verdict

# =============================================================================
# Module Overview
# =============================================================================
# Listen: mine what many accounts are posting right now. `listen` groups a
# firehose table by normalised text and returns each group as a `Template`
# with its replication curve and a spam verdict; `sounds` does the same for
# TikTok music ids. Both are pure over the table they are handed.


def listen(tweets: pa.Table, min_authors: int = 5, max_templates: int = 50, min_chars: int = 20) -> list[Template]:
    """Templates posted verbatim by `min_authors` or more distinct accounts, most replicated first."""
    if min_authors < 2:
        raise ValueError("min_authors must be at least 2; one author is a post, not a template")
    if tweets.num_rows == 0:
        return []
    rows = cluster_templates(tweets, min_authors=min_authors, min_chars=min_chars)
    templates = [
        Template(
            text=row["text"],
            normalised=row["normalised"],
            authors=row["authors"],
            posts=row["posts"],
            first_seen=row["first_seen"],
            first_authors=tuple(row["first_authors"]),
            sample_ids=tuple(row["sample_ids"]),
            curve=hour_curve(row["curve"]),
            spam=verdict(
                authors=row["authors"],
                posts=row["posts"],
                link_share=row["link_share"],
                zero_views_share=row["zero_views_share"],
                normalised=row["normalised"],
            ),
        )
        for row in rows
    ]
    templates.sort(key=lambda t: (-t.authors, -t.posts))
    return templates[:max_templates]


def sounds(videos: pa.Table, min_creators: int = 5, max_sounds: int = 50) -> list[Sound]:
    """TikTok sounds used by `min_creators` or more distinct creators; a sound is a template."""
    if min_creators < 2:
        raise ValueError("min_creators must be at least 2")
    if videos.num_rows == 0:
        return []
    rows = cluster_sounds(videos, min_creators=min_creators)
    result = [
        Sound(
            music_id=row["music_id"],
            title=row["title"],
            creators=row["creators"],
            videos=row["videos"],
            first_seen=row["first_seen"],
            curve=hour_curve(row["curve"]),
        )
        for row in rows
    ]
    result.sort(key=lambda s: (-s.creators, -s.videos))
    return result[:max_sounds]
