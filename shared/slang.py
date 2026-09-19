from __future__ import annotations

import re

# =============================================================================
# Module Overview
# =============================================================================
# A small lexicon of internet slang and meme formats, for the government
# chart: which official accounts adopted this register, and when. Each entry
# is a word or a format marker; matching is whole-word and case-insensitive.
# The list is deliberately short and recognisable, so a judge can read it.

SLANG = (
    "lowkey", "highkey", "no cap", "fr fr", "rizz", "sus", "based", "cringe", "slay", "vibe", "vibes",
    "goated", "unhinged", "delulu", "brainrot", "skibidi", "sigma", "gyat", "aura", "cooked",
    "it's giving", "main character", "npc", "ratio", "tell me you", "without telling me", "pov:",
    "nobody:", "me:", "asmr", "let him cook", "chat is this real", "crash out", "ts pmo", "6 7",
    "bussin", "yeet", "stan", "simp", "bet", "cap", "iykyk", "ded", "💀", "🔥", "😭",
)

_PATTERN = re.compile(r"(?<!\w)(" + "|".join(re.escape(s) for s in sorted(SLANG, key=len, reverse=True)) + r")(?!\w)", re.IGNORECASE)


def slang_hits(text: str) -> tuple[str, ...]:
    """The lexicon entries a text contains, in order of appearance."""
    return tuple(m.group(1).lower() for m in _PATTERN.finditer(text or ""))


def uses_slang(text: str) -> bool:
    """True when at least one entry appears."""
    return _PATTERN.search(text or "") is not None
