# tools/render

Render: make it a clip. `render(candidate, voice, visuals, sound, out_dir) -> Clip`: a 9:16
MP4 of about twenty seconds, the post spoken by `voice`, word-timed captions burned over a
background from `visuals`, and the trending sound named on the clip.

Pipeline: `script` (post to spoken text and caption chunks) then `voice` (audio plus word
timings) then `visuals` (background video) then `compose` (ffmpeg). The middle two are seams:
`SilentVoice` and `LoopsVisuals` run offline and are the defaults; ElevenLabs, a generated
still and Veo are Part 2 adapters behind the same protocols.

Invariants: captions cover the whole spoken text in order; the clip is 1080 by 1920 H.264
with an audio track even when the voice is silent, because upload flows expect one; the
render writes one file under `out_dir` and returns its path, nothing else touches disk.

Gotchas: ffmpeg must be on PATH. Homebrew's ffmpeg has no text filter, so captions are drawn
by Pillow into PNGs and overlaid for their time windows; a post's punctuation never touches
the filter graph. The sound is named, not mixed in.

Test: `uv run pytest tests/test_render.py`. Done when a clip renders from a draft in under a
minute with the local adapters.
