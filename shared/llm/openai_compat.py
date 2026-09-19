from __future__ import annotations

from typing import Sequence

from openai import OpenAI

from shared.types import Message

# =============================================================================
# Module Overview
# =============================================================================
# Adapter for any OpenAI-compatible chat endpoint. Featherless, Gemini,
# Anthropic and OpenAI all expose one, so a base URL, a key and a model name
# are the whole configuration. Chosen over LiteLLM because the endpoint the
# team has is OpenAI-compatible and this drops about a hundred transitive
# dependencies the team would otherwise have to answer for.


class OpenAICompatLLM:
    """Adapter: chat completions against `base_url` with `model`."""

    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float = 60.0) -> None:
        if not api_key:
            raise ValueError("api_key is empty; set `MEROK_LLM_API_KEY`")
        if not model:
            raise ValueError("model is empty; set `MEROK_LLM_MODEL`")
        self.model = model
        # An empty base_url means the OpenAI default, which is what the SDK does with None.
        self._client = OpenAI(base_url=base_url or None, api_key=api_key, timeout=timeout_s)

    def complete(self, system: str, messages: Sequence[Message], *, temperature: float = 0.7, max_tokens: int = 800) -> str:
        if not messages:
            raise ValueError("messages must not be empty")
        payload = [{"role": "system", "content": system}] + [{"role": m.role, "content": m.content} for m in messages]
        response = self._client.chat.completions.create(
            model=self.model, messages=payload, temperature=temperature, max_tokens=max_tokens
        )
        choice = response.choices[0].message.content if response.choices else None
        if not choice:
            raise RuntimeError(f"model {self.model!r} returned no content")
        return choice.strip()
