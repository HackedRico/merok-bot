from __future__ import annotations

import re
from typing import Sequence

from shared.types import Caption
from tools.render.tts import WordTiming

# =============================================================================
# Module Overview
# =============================================================================
# From a post to what gets spoken and what gets shown. Spoken text drops
# links and turns handles and hashtags into words; captions are the spoken
# words in short groups with the voice's timings.

WORDS_PER_CAPTION = 4
_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def spoken_text(post: str) -> str:
    """The post as a voice should read it: no links, handles and hashtags as plain words."""
    text = _URL.sub("", post)
    text = re.sub(r"[@#](\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def captions_for(words: Sequence[WordTiming], per_caption: int = WORDS_PER_CAPTION) -> tuple[Caption, ...]:
    """Group timed words into captions of a few words each, spanning the group's first start to last end."""
    if per_caption < 1:
        raise ValueError("per_caption must be at least 1")
    out: list[Caption] = []
    for i in range(0, len(words), per_caption):
        group = words[i : i + per_caption]
        out.append(Caption(text=" ".join(w.word for w in group), start_s=group[0].start_s, end_s=group[-1].end_s))
    return tuple(out)


def visual_brief(post: str) -> str:
    """One line for the visuals seam: a mood read off the post's punctuation and case."""
    words = post.split()
    shouting = sum(1 for w in words if len(w) > 2 and w.isupper()) >= 2 or post.count("!") >= 2
    if shouting:
        return "urgent, high contrast, fast drift"
    if "?" in post:
        return "curious, cool tones, slow drift"
    return "calm, warm tones, slow drift"
