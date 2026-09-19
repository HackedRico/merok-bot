from __future__ import annotations

import time
import uuid
from pathlib import Path

from shared.types import Candidate, Clip, Sound
from tools.render.compose import compose
from tools.render.script import captions_for, spoken_text, visual_brief
from tools.render.tts import SilentVoice, Voice
from tools.render.visuals import LoopsVisuals, Visuals

# =============================================================================
# Module Overview
# =============================================================================
# Render: a drafted post becomes a TikTok-ready clip. Script, then voice,
# then visuals, then ffmpeg composition. The voice and the visuals are seams;
# the defaults run on the laptop with nothing installed but ffmpeg.

__all__ = ["render", "SilentVoice", "LoopsVisuals", "Voice", "Visuals"]

MAX_SECONDS = 30.0


def render(candidate: Candidate, voice: Voice, visuals: Visuals, sound: Sound | None, out_dir: Path) -> Clip:
    """Render `candidate` as a captioned 9:16 clip under `out_dir` and return where it landed."""
    if not candidate.text.strip():
        raise ValueError("candidate text is empty")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"clip-{int(time.time())}-{uuid.uuid4().hex[:6]}"

    spoken = spoken_text(candidate.text)
    speech = voice.speak(spoken, out_dir / f"{stem}.voice")
    duration = min(max(speech.duration_s + 1.0, 4.0), MAX_SECONDS)
    captions = captions_for(speech.words)
    background = visuals.generate(visual_brief(candidate.text), duration, out_dir / f"{stem}.bg.mp4")
    out_path = compose(background, speech.audio_path, captions, duration, out_dir / f"{stem}.mp4", sound.title if sound else None)
    return Clip(
        path=str(out_path),
        duration_s=duration,
        captions=captions,
        sound=sound,
        voice_used=voice.name,
        visuals_used=visuals.name,
    )
