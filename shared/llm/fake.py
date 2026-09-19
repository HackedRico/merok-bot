from __future__ import annotations

from typing import Callable, Sequence

from shared.types import Message

# =============================================================================
# Module Overview
# =============================================================================
# The offline adapter. Tests hand it canned replies and read back what it was
# asked; a keyless demo gets `FakeLLM.offline()`, which answers with visibly
# marked placeholders so nobody mistakes them for a model's work.


class FakeLLM:
    """Adapter: canned replies in order, or a function of the last user message."""

    name = "fake"

    def __init__(self, replies: Sequence[str] | Callable[[str, Sequence[Message]], str]) -> None:
        if not callable(replies) and not replies:
            raise ValueError("replies must be a non-empty sequence or a callable")
        self._replies = replies
        self._next = 0
        self.calls: list[tuple[str, tuple[Message, ...]]] = []

    def complete(self, system: str, messages: Sequence[Message], *, temperature: float = 0.7, max_tokens: int = 800) -> str:
        self.calls.append((system, tuple(messages)))
        if callable(self._replies):
            return self._replies(system, messages)
        reply = self._replies[self._next % len(self._replies)]
        self._next += 1
        return reply

    @classmethod
    def offline(cls) -> "FakeLLM":
        """A fake whose every answer says it is one; the demo runs, the drafts are placeholders."""

        def answer(system: str, messages: Sequence[Message]) -> str:
            last = messages[-1].content if messages else ""
            if "Return JSON" in system or "JSON" in system[:200]:
                return '{"tool": null}'
            return f"[offline model] No model key is set, so this is a placeholder for: {last[:120]}"

        return cls(answer)
