from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from shared.types import Caption

# =============================================================================
# Module Overview
# =============================================================================
# The ffmpeg composition. Each caption is drawn by Pillow into a transparent
# PNG and overlaid for its time window, because Homebrew's ffmpeg ships
# without the text filter; the voice is the audio track, or silence, so
# uploaders that expect audio accept the file; the sound's name sits in the
# corner.

WIDTH, HEIGHT = 1080, 1920
FONT_CANDIDATES = (
    ("/System/Library/Fonts/Helvetica.ttc", 1),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """The first bold system face Pillow can open; `index` picks the bold face inside a .ttc."""
    for path, index in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                return ImageFont.truetype(path, size)
    raise FileNotFoundError("no caption font found; install DejaVu Sans or add a path to `FONT_CANDIDATES`")


def caption_image(text: str, out_path: Path, size: int = 84, width: int = WIDTH - 120) -> Path:
    """Draw `text` white with a black outline on a transparent canvas, wrapped to `width`."""
    font = load_font(size)
    lines = _wrap(text, font, width)
    line_h = int(size * 1.25)
    canvas = Image.new("RGBA", (WIDTH, line_h * len(lines) + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x, y = (WIDTH - w) / 2, 20 + i * line_h
        draw.text((x, y), line, font=font, fill="white", stroke_width=6, stroke_fill="black")
    canvas.save(out_path)
    return out_path


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and font.getlength(trial) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    return lines + [current] if current else lines or [""]


def compose(background: str, audio: str | None, captions: Sequence[Caption], duration_s: float, out_path: Path, sound_title: str | None) -> Path:
    """Overlay `captions` on `background` for their time windows, add `audio` or silence, write `out_path`."""
    if shutil.which("ffmpeg") is None:
        raise FileNotFoundError("ffmpeg is not on PATH; `brew install ffmpeg`")
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", background]
        if audio:
            cmd += ["-i", audio]
        else:
            # Silent clips still get a track: TikTok's and Instagram's uploaders reject video-only files.
            cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

        overlays: list[tuple[int, str]] = []
        for i, cap in enumerate(captions):
            png = caption_image(cap.text, Path(tmp) / f"cap{i}.png")
            cmd += ["-i", str(png)]
            overlays.append((2 + i, f"(W-w)/2:(H-h)/2:enable='between(t,{cap.start_s:.3f},{cap.end_s + 0.05:.3f})'"))
        if sound_title:
            png = caption_image(f"sound: {sound_title}", Path(tmp) / "sound.png", size=40)
            cmd += ["-i", str(png)]
            overlays.append((2 + len(captions), "(W-w)/2:H-h-80"))

        graph, current = [], "0:v"
        for n, (index, position) in enumerate(overlays):
            label = f"v{n}"
            graph.append(f"[{current}][{index}:v]overlay={position}[{label}]")
            current = label
        filter_complex = ";".join(graph) if graph else "[0:v]null[v0]"
        current = current if graph else "v0"

        cmd += [
            "-filter_complex", filter_complex, "-map", f"[{current}]", "-map", "1:a",
            "-t", f"{duration_s}", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(out_path),
        ]
        subprocess.run(cmd, check=True)
    return Path(out_path)
