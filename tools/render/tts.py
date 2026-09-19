from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# =============================================================================
# Module Overview
# =============================================================================
# The voice seam. `speak` returns audio on disk plus per-word timings, which
# is what the captions need. `SilentVoice` produces no audio and even
# timings at a reading pace, so a clip renders offline; ElevenLabs sits in
# `elevenlabs.py` behind the same protocol.


@dataclass(frozen=True, slots=True)
class WordTiming:
    """One spoken word and when it is heard."""

    word: str
    start_s: float
    end_s: float


@dataclass(frozen=True, slots=True)
class Speech:
    """What a voice produced: an audio file, or None when silent, and the word timings."""

    audio_path: str | None
    words: tuple[WordTiming, ...]
    duration_s: float


class Voice(Protocol):
    """Speak a text and say when each word lands."""

    name: str

    def speak(self, text: str, out_stem: Path) -> Speech: ...


class SilentVoice:
    """Adapter: no audio, words paced evenly at `wpm`; the offline default and the test adapter."""

    name = "silent"

    def __init__(self, wpm: int = 150) -> None:
        if wpm < 40 or wpm > 400:
            raise ValueError("wpm must be between 40 and 400")
        self.wpm = wpm

    def speak(self, text: str, out_stem: Path) -> Speech:
        words = text.split()
        if not words:
            raise ValueError("text has no words to speak")
        per_word = 60.0 / self.wpm
        timings = tuple(WordTiming(w, round(i * per_word, 3), round((i + 1) * per_word, 3)) for i, w in enumerate(words))
        return Speech(audio_path=None, words=timings, duration_s=round(len(words) * per_word, 3))
