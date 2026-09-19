from __future__ import annotations

from chat.router import route
from chat.session import Session
from chat.tools import SPECS, Deps, Tools
from shared.llm import LLM
from shared.types import Reply

# =============================================================================
# Module Overview
# =============================================================================
# The orchestrator: one message becomes one tool call, the tool runs against
# the session, and the reply carries the text, the call and the cards.

__all__ = ["respond", "Session", "Tools", "Deps", "SPECS"]

HELP = (
    "I can do seven things: tell you what is spreading, explain a post you paste, draft five posts in your voice, "
    "score a draft, turn one into a clip, post it, and show how it did."
)


def respond(message: str, session: Session, tools: Tools, llm: LLM) -> Reply:
    """Route `message`, run the tool, and phrase what came back; errors become plain replies."""
    if not message.strip():
        return Reply(HELP, (), ())
    call = route(message, session, tools.specs, llm)
    if call.tool == "help":
        return Reply(HELP, (), ())
    try:
        result = tools.run(call.tool, call.args, session)
    except ValueError as exc:
        # A tool's own validation message is the most useful reply there is.
        return Reply(str(exc), (call,), ())
    return Reply(result.text, (call,), result.attachments)
