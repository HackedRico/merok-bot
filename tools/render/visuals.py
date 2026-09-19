from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

# =============================================================================
# Module Overview
# =============================================================================
# The video generation seam. `generate` returns a 9:16 background video of
# the asked length. `LoopsVisuals` draws a slowly drifting gradient with
# ffmpeg, so there are no binary assets in the repo and nothing to download;
# a generated still and Veo are Part 2 adapters behind the same protocol.

WIDTH, HEIGHT = 1080, 1920

# Colour pairs by mood word in the brief; the brief comes from `script.visual_brief`.
PALETTES = {
    "urgent": ("0x8b1a1a", "0x1a0a0a"),
    "curious": ("0x0f2f4f", "0x0a0f1a"),
    "calm": ("0x3a2a12", "0x14100a"),
}


class Visuals(Protocol):
    """Produce a background video for a brief and a length."""

    name: str

    def generate(self, brief: str, seconds: float, out_path: Path) -> str: ...


class LoopsVisuals:
    """Adapter: an ffmpeg gradient that drifts; instant, free, offline."""

    name = "loops"

    def generate(self, brief: str, seconds: float, out_path: Path) -> str:
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        mood = next((m for m in PALETTES if m in brief), "calm")
        c0, c1 = PALETTES[mood]
        speed = "0.05" if mood == "urgent" else "0.015"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"gradients=s={WIDTH}x{HEIGHT}:d={seconds}:speed={speed}:c0={c0}:c1={c1}:nb_colors=2:type=linear",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-t", f"{seconds}",
            str(out_path),
        ]
        subprocess.run(cmd, check=True)
        return str(out_path)
