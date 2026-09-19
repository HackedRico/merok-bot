from __future__ import annotations

import logging
from typing import Protocol, Sequence

from shared.config import Settings
from shared.types import Message

# =============================================================================
# Module Overview
# =============================================================================
# The model seam. `LLM` is one method: a system prompt and messages in, text
# out. `OpenAICompatLLM` speaks to any OpenAI-compatible endpoint (Featherless,
# Gemini, Anthropic, OpenAI) so the model is three config strings. `FakeLLM`
# keeps every test, and a keyless demo, off the network.

log = logging.getLogger(__name__)


class LLM(Protocol):
    """Complete a conversation; the whole contract is this one call."""

    name: str

    def complete(self, system: str, messages: Sequence[Message], *, temperature: float = 0.7, max_tokens: int = 800) -> str: ...


def make_llm(settings: Settings) -> LLM:
    """The real endpoint when configured, the offline fake otherwise, with a warning."""
    from shared.llm.fake import FakeLLM
    from shared.llm.openai_compat import OpenAICompatLLM

    if settings.llm_configured:
        return OpenAICompatLLM(settings.llm_base_url, settings.llm_api_key, settings.llm_model)
    log.warning("[llm] MEROK_LLM_API_KEY or MEROK_LLM_MODEL is unset; using the offline fake. Drafts will be placeholders.")
    return FakeLLM.offline()
