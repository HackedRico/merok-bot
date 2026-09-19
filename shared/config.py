from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

# =============================================================================
# Module Overview
# =============================================================================
# Environment to an immutable `Settings`. Only `api/` and `scripts/` call
# `load_settings`; everything else receives the adapters it builds as
# arguments, so no tool reads the environment.

DATA_SOURCES = ("local", "fixture")
EMBEDDERS = ("hash", "nomic")
VOICES = ("silent", "elevenlabs")
VISUALS = ("loops", "still", "veo")
PUBLISHERS = ("dry_run", "clipboard", "x")
POLLERS = ("replay", "x")


@dataclass(frozen=True, slots=True)
class Settings:
    """Every knob the app reads, with a local default for each."""

    data_source: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    embedder: str
    voice: str
    visuals: str
    publisher: str
    poller: str
    demo_handle: str
    cache_dir: Path
    fixtures_dir: Path

    @property
    def llm_configured(self) -> bool:
        """True when a real model endpoint is set; otherwise the offline fake is used."""
        return bool(self.llm_api_key and self.llm_model)


def _choice(env: Mapping[str, str], key: str, allowed: tuple[str, ...], default: str) -> str:
    value = env.get(key, default).strip() or default
    if value not in allowed:
        raise ValueError(f"{key} must be one of {allowed}, got {value!r}")
    return value


def load_settings(env: Mapping[str, str] | None = None, repo_root: Path | None = None) -> Settings:
    """Read settings from `.env` and the environment; the environment wins."""
    root = repo_root or Path(__file__).resolve().parents[1]
    if env is None:
        # A .env in the repo root never overrides a variable already exported.
        load_dotenv(root / ".env", override=False)
        env = os.environ
    return Settings(
        data_source=_choice(env, "MEROK_DATA_SOURCE", DATA_SOURCES, "local"),
        llm_base_url=env.get("MEROK_LLM_BASE_URL", "").strip(),
        llm_api_key=env.get("MEROK_LLM_API_KEY", "").strip(),
        llm_model=env.get("MEROK_LLM_MODEL", "").strip(),
        embedder=_choice(env, "MEROK_EMBEDDER", EMBEDDERS, "hash"),
        voice=_choice(env, "MEROK_VOICE", VOICES, "silent"),
        visuals=_choice(env, "MEROK_VISUALS", VISUALS, "loops"),
        publisher=_choice(env, "MEROK_PUBLISHER", PUBLISHERS, "dry_run"),
        poller=_choice(env, "MEROK_POLLER", POLLERS, "replay"),
        demo_handle=env.get("MEROK_DEMO_HANDLE", "sensanders").strip().lower(),
        cache_dir=(root / env.get("MEROK_CACHE_DIR", ".cache")).resolve(),
        fixtures_dir=(root / "tests" / "fixtures").resolve(),
    )
