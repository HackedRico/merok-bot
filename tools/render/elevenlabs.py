from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

from tools.render.tts import Speech, WordTiming

# =============================================================================
# Module Overview
# =============================================================================
# Part 2 adapter: ElevenLabs text to speech with character timestamps, folded
# into word timings. Needs `ELEVENLABS_API_KEY`. Not exercised by tests; the
# silent voice is.

DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"
MODEL = "eleven_multilingual_v2"


class ElevenLabsVoice:
    """Adapter: real speech, timings from the API's `with-timestamps` endpoint."""

    name = "elevenlabs"

    def __init__(self, api_key: str | None = None, voice_id: str = DEFAULT_VOICE) -> None:
        key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        if not key:
            raise ValueError("ElevenLabs needs `ELEVENLABS_API_KEY`")
        self._key = key
        self.voice_id = voice_id

    def speak(self, text: str, out_stem: Path) -> Speech:
        if not text.strip():
            raise ValueError("text is empty")
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/with-timestamps",
            data=json.dumps({"text": text, "model_id": MODEL}).encode(),
            headers={"xi-api-key": self._key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.load(resp)
        audio_path = Path(str(out_stem) + ".mp3")
        audio_path.write_bytes(base64.b64decode(body["audio_base64"]))
        words = _words_from_characters(body["alignment"])
        return Speech(audio_path=str(audio_path), words=words, duration_s=words[-1].end_s if words else 0.0)


def _words_from_characters(alignment: dict) -> tuple[WordTiming, ...]:
    """Fold ElevenLabs' per-character timings into per-word timings at whitespace."""
    chars, starts, ends = alignment["characters"], alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    words: list[WordTiming] = []
    buf, start = "", None
    for c, s, e in zip(chars, starts, ends):
        if c.isspace():
            if buf:
                words.append(WordTiming(buf, start, e))
                buf, start = "", None
            continue
        if start is None:
            start = s
        buf += c
    if buf:
        words.append(WordTiming(buf, start, ends[-1]))
    return tuple(words)
