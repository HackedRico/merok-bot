from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import State, router
from chat import Deps, Tools
from shared.config import Settings, load_settings
from shared.data import make_source
from shared.data.cache import LocalSource
from shared.embed import make_embedder
from shared.llm import make_llm
from tools.learn.replay import ReplayPoller
from tools.render import LoopsVisuals, SilentVoice
from tools.score import Traction
from tools.ship import ClipboardPublisher, DryRunPublisher

# =============================================================================
# Module Overview
# =============================================================================
# The app factory. Reads settings once, builds every adapter, warms the
# templates and the traction model, and mounts the routes. `app` at module
# level is what uvicorn serves.

log = logging.getLogger("merok.api")

TRAIN_ROWS = 25_000


def build_deps(settings: Settings) -> Deps:
    """Every adapter and table the chat tools need, from one settings value."""
    t = time.time()
    source = make_source(settings)
    files = None
    if isinstance(source, LocalSource):
        cached = source.cached_files()
        files = cached[-settings.window_files :] if cached else None
    tweets = source.firehose(files=files)
    own_posts = source.gov_tweets([settings.demo_handle])
    if own_posts.num_rows == 0:
        raise ValueError(f"no posts for MEROK_DEMO_HANDLE={settings.demo_handle!r}; pick an account in the government set")
    embedder = make_embedder(settings.embedder)
    log.info("[api] %s rows from %s, %s posts for @%s, loaded in %.0fs", tweets.num_rows, source.name, own_posts.num_rows, settings.demo_handle, time.time() - t)

    t = time.time()
    traction = Traction.fit(tweets, embedder, max_rows=TRAIN_ROWS)
    log.info("[api] traction fitted in %.0fs", time.time() - t)

    clip_dir = settings.cache_dir / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    return Deps(
        tweets=tweets,
        own_posts=own_posts,
        demo_handle=settings.demo_handle,
        embedder=embedder,
        llm=make_llm(settings),
        traction=traction,
        voice=SilentVoice() if settings.voice == "silent" else _elevenlabs(),
        visuals=LoopsVisuals(),
        publisher=ClipboardPublisher() if settings.publisher == "clipboard" else DryRunPublisher(),
        poller=ReplayPoller(tweets, seed=None),
        clip_dir=clip_dir,
    )


def _elevenlabs():
    from tools.render.elevenlabs import ElevenLabsVoice

    return ElevenLabsVoice()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API with adapters from `settings`, or from the environment."""
    settings = settings or load_settings()
    deps = build_deps(settings)
    tools = Tools(deps)
    app = FastAPI(title="merok-bot", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.state.merok = State(settings=settings, deps=deps, tools=tools, sessions={})
    app.include_router(router)
    return app


def create_app_from_env() -> FastAPI:
    """What `uvicorn api.main:create_app_from_env --factory` serves."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return create_app()
