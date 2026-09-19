from __future__ import annotations

from shared.types import SpamVerdict

# =============================================================================
# Module Overview
# =============================================================================
# Paid replication looks like organic replication until you look at the
# accounts. The verdict scores four signals and names each one it fired, so
# the split can be shown as part of the finding rather than applied silently.

# Words that sit in nearly every airdrop and presale copy and in almost no organic template.
CRYPTO_MARKERS = ("airdrop", "claim", "presale", "whitelist", "mint", "giveaway", "token", "$", "wallet", "live on")


def verdict(authors: int, posts: int, link_share: float, zero_views_share: float, normalised: str) -> SpamVerdict:
    """Score a template's replication as paid (near 1) or organic (near 0), with reasons."""
    if authors < 1 or posts < authors:
        raise ValueError("posts must be at least authors, and authors at least 1")
    reasons: list[str] = []
    score = 0.0

    repeat = posts / authors
    if repeat >= 1.5:
        score += 0.35
        reasons.append(f"accounts repeat it: {repeat:.1f} posts per author")
    # Links alone are weak evidence: X's share cards and news templates carry one and are organic.
    if link_share >= 0.5:
        score += 0.2
        reasons.append(f"{link_share:.0%} of posts carry a link")
    if zero_views_share >= 0.6:
        score += 0.2
        reasons.append(f"{zero_views_share:.0%} of posts have zero views")
    hits = [m for m in CRYPTO_MARKERS if m in normalised]
    if hits:
        score += 0.35
        reasons.append("crypto copy: " + ", ".join(hits[:3]))

    if not reasons:
        reasons.append("one post per account, no links, seen by real feeds")
    return SpamVerdict(score=min(score, 1.0), reasons=tuple(reasons))
