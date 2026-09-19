from __future__ import annotations

import json
import re
from typing import Sequence

from chat.session import Session
from chat.tools import ToolSpec
from shared.llm import LLM
from shared.types import Message, ToolCall

# =============================================================================
# Module Overview
# =============================================================================
# Which tool a message means. Rules first: they are deterministic, cheap and
# explainable at the table. The model second, asked for JSON. A message that
# neither resolves is an intent to draft, because that is what the app is for.

ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_NUMBER = re.compile(r"(?:#|number |draft |no\.? ?)?\b([1-5])\b")
_QUOTED = re.compile(r"[\"“]([^\"”]{8,})[\"”]")

_LISTEN = ("spreading", "trending", "what's hot", "whats hot", "templates", "right now", "this hour", "what are people posting", "listen")
_EXPLAIN = ("what is this", "what does this mean", "explain", "what does", "meaning of", "what is \"", "what's this", "translate")
_RENDER = ("clip", "tiktok", "video", "render", "reel")
_SHIP = ("post it", "post the", "post draft", "post number", "ship", "publish", "send it", "post #", "post 1", "post 2", "post 3", "post 4", "post 5")
_LEARN = ("how did it do", "how is it doing", "how's it doing", "curve", "so far", "on track", "learn", "did it work", "results")
_SCORE = ("score", "predict", "how will", "how would", "forecast", "will it travel")
_DRAFT = ("draft", "write", "help me", "announce", "say", "post about", "tweet about", "compose")


def ordinal(message: str) -> int:
    """The draft number a message points at, default 1."""
    low = message.lower()
    for word, n in ORDINALS.items():
        if re.search(rf"\b{word}\b", low):
            return n
    m = _NUMBER.search(low)
    return int(m.group(1)) if m else 1


def pasted_text(message: str) -> str:
    """The text to explain: a quoted span, the text after a colon, or the message minus its trigger."""
    q = _QUOTED.search(message)
    if q:
        return q.group(1).strip()
    if ":" in message:
        after = message.split(":", 1)[1].strip()
        if len(after) >= 8:
            return after
    low = message.lower()
    for trigger in _EXPLAIN:
        if trigger in low:
            cut = low.index(trigger) + len(trigger)
            rest = message[cut:].strip(" ?:.\"“”")
            if len(rest) >= 8:
                return rest
    return message.strip()


def route_by_rules(message: str, session: Session) -> ToolCall | None:
    """A tool call when a rule matches, else None."""
    low = message.lower().strip()
    if not low:
        return None
    if any(t in low for t in _EXPLAIN) or "http" in low:
        return ToolCall("explain", {"text": pasted_text(message)})
    if any(t in low for t in _LISTEN):
        return ToolCall("listen", {})
    if any(t in low for t in _LEARN) and session.post is not None:
        return ToolCall("learn", {})
    if any(t in low for t in _RENDER):
        return ToolCall("render", {"index": ordinal(message)})
    if any(t in low for t in _SHIP):
        return ToolCall("ship", {"index": ordinal(message)})
    if any(t in low for t in _SCORE):
        return ToolCall("score", {"index": ordinal(message)} if session.candidates else {"text": message})
    if any(t in low for t in _DRAFT):
        return ToolCall("draft", {"intent": message})
    return None


def route_by_model(message: str, specs: Sequence[ToolSpec], llm: LLM) -> ToolCall | None:
    """Ask the model to choose; None when it declines or answers badly."""
    menu = "\n".join(f"- {s.name}: {s.description} args: {json.dumps(s.args)}" for s in specs)
    system = (
        "You route a user's message to exactly one tool. Return JSON only, of the form "
        '{"tool": "<name>", "args": {...}} or {"tool": null} if nothing fits.\nTools:\n' + menu
    )
    try:
        raw = llm.complete(system, [Message("user", message)], temperature=0.0, max_tokens=200)
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1]) if start >= 0 else {}
    except (ValueError, RuntimeError):
        return None
    name = data.get("tool") if isinstance(data, dict) else None
    if name in {s.name for s in specs}:
        args = data.get("args") if isinstance(data.get("args"), dict) else {}
        return ToolCall(str(name), args)
    return None


def route(message: str, session: Session, specs: Sequence[ToolSpec], llm: LLM) -> ToolCall:
    """Rules, then the model, then draft."""
    call = route_by_rules(message, session) or route_by_model(message, specs, llm)
    if call is not None:
        return call
    return ToolCall("draft", {"intent": message}) if len(message.split()) >= 3 else ToolCall("help", {})
