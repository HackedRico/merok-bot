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
PUBLISHERS = ("x", "clipboard", "dry_run")
POLLERS = ("x", "replay")


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
    x_consumer_key: str
    x_consumer_secret: str
    x_access_token: str
    x_access_token_secret: str
    x_budget_usd: float
    demo_handle: str
    window_files: int
    cache_dir: Path
    fixtures_dir: Path

    @property
    def x_configured(self) -> bool:
        """True when all four X credentials are set; posting and polling need OAuth 1.0a user context."""
        return all((self.x_consumer_key, self.x_consumer_secret, self.x_access_token, self.x_access_token_secret))

    @property
    def llm_configured(self) -> bool:
        """True when a real model endpoint is set; otherwise the offline fake is used."""
        return bool(self.llm_api_key and self.llm_model)


def _choice(env: Mapping[str, str], key: str, allowed: tuple[str, ...], default: str) -> str:
    value = env.get(key, default).strip() or default
    if value not in allowed:
        raise ValueError(f"{key} must be one of {allowed}, got {value!r}")
    return value


def _positive_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key, "").strip()
    value = float(raw) if raw else default
    if value <= 0:
        raise ValueError(f"{key} must be positive, got {value}")
    return value


def _positive_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "").strip()
    value = int(raw) if raw else default
    if value < 1:
        raise ValueError(f"{key} must be a positive integer, got {value}")
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
        publisher=_choice(env, "MEROK_PUBLISHER", PUBLISHERS, "x"),
        poller=_choice(env, "MEROK_POLLER", POLLERS, "x"),
        x_consumer_key=env.get("X_CONSUMER_KEY", "").strip(),
        x_consumer_secret=env.get("X_CONSUMER_SECRET", "").strip(),
        x_access_token=env.get("X_ACCESS_TOKEN", "").strip(),
        x_access_token_secret=env.get("X_ACCESS_TOKEN_SECRET", "").strip(),
        x_budget_usd=_positive_float(env, "MEROK_X_BUDGET_USD", 10.0),
        demo_handle=env.get("MEROK_DEMO_HANDLE", "sensanders").strip().lower(),
        window_files=_positive_int(env, "MEROK_WINDOW_FILES", 6),
        cache_dir=(root / env.get("MEROK_CACHE_DIR", ".cache")).resolve(),
        fixtures_dir=(root / "tests" / "fixtures").resolve(),
    )
