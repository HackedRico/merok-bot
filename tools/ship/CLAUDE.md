# tools/ship

Ship: post it. `Publisher.post(text) -> PostId`. Adapters: `DryRunPublisher` returns an id
and records the text, the rehearsal default; `ClipboardPublisher` puts the text on the
clipboard for TikTok, Instagram and LinkedIn, whose posting APIs lock unaudited apps out.
The X adapter is Part 2 and is the only code that would spend money.

Invariants: `post` validates the text (non-empty, at most 280 characters for X) before any
side effect. The dry run never touches the network.

Test: `uv run pytest tests/test_ship.py`.
