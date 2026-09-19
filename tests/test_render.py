from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from shared.types import Candidate
from tools.render import LoopsVisuals, SilentVoice, render
from tools.render.script import captions_for, spoken_text, visual_brief


def test_script_speaks_without_links_and_groups_captions() -> None:
    assert spoken_text("Town hall Thursday 6pm! Details: https://t.co/x @sensanders #Vermont") == "Town hall Thursday 6pm! Details: sensanders Vermont"
    words = SilentVoice(wpm=120).speak("one two three four five six seven", Path("/tmp/x")).words
    caps = captions_for(words, per_caption=4)
    assert [c.text for c in caps] == ["one two three four", "five six seven"]
    assert caps[0].start_s == 0.0 and caps[1].end_s == words[-1].end_s
    assert "urgent" in visual_brief("BREAKING!! THIS IS HUGE!") and "calm" in visual_brief("a quiet note.")


def test_a_clip_renders_offline_in_under_a_minute(tmp_path: Path) -> None:
    candidate = Candidate(text="Do you remember when you joined X? I do! Thursday's town hall is at 6pm.", rationale="", template_text=None)
    t = time.time()
    clip = render(candidate, SilentVoice(), LoopsVisuals(), None, tmp_path)
    assert time.time() - t < 60
    path = Path(clip.path)
    assert path.exists() and path.stat().st_size > 20_000
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(probe.stdout)
    kinds = {s["codec_type"] for s in info["streams"]}
    assert kinds == {"video", "audio"}
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1080, 1920)
    assert abs(float(info["format"]["duration"]) - clip.duration_s) < 1.0
    assert clip.captions and clip.voice_used == "silent" and clip.visuals_used == "loops"
