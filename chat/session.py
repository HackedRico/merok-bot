from __future__ import annotations

from dataclasses import dataclass, field

from shared.types import Candidate, Clip, Explanation, Forecast, PostId, Template

# =============================================================================
# Module Overview
# =============================================================================
# What a conversation remembers between turns: the last things shown, so an
# ordinal like "the third one" resolves. Mutable on purpose; it is the one
# piece of state in the chat and it belongs to one conversation.


@dataclass
class Session:
    """Per-conversation memory of what the assistant last showed."""

    templates: list[Template] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    forecasts: list[Forecast] = field(default_factory=list)
    explanation: Explanation | None = None
    post: PostId | None = None
    posted_forecast: Forecast | None = None
    clip: Clip | None = None

    def candidate(self, index: int) -> Candidate:
        """The `index`th candidate shown (one-based), or a `ValueError` naming what exists."""
        if not self.candidates:
            raise ValueError("no drafts yet; ask for a draft first")
        if not 1 <= index <= len(self.candidates):
            raise ValueError(f"there are {len(self.candidates)} drafts; pick 1 to {len(self.candidates)}")
        return self.candidates[index - 1]
