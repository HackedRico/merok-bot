# chat

The orchestrator. `respond(message, session, tools, llm) -> Reply`: one message routes to one
tool, the tool runs, the reply quotes the returned numbers, and the session remembers what
was shown so "post the third one" means something.

Routing is rules first, model second: a handful of verbs and phrasings map straight to a
tool, deterministically, so the demo never depends on a model's mood; anything the rules do
not catch is put to the model as a JSON choice, and if that fails the message is treated as
an intent to draft. Reply text is composed from the values, not written by the model, so it
is always right about the numbers.

Invariants: no branch here belongs in a tool; if one appears, move it. Every reply carries
the tool call it made and the attachments the app renders.

Test: `uv run pytest tests/test_chat.py`. Done when each example message in the plan routes to
the right tool.
