# api

FastAPI. `create_app(settings)` is the only place that reads config and builds adapters: the
data source, the embedder, the model, the voice, the visuals, the publisher, the poller. It
mines the window's templates and fits the traction model at startup so every request is
fast, then serves `/chat`, `/health`, `/tools` and `/clips/{name}`.

Invariants: no logic beyond wiring and HTTP. Sessions live in memory keyed by
`conversation_id`; restarting the server forgets them, which is fine for a demo.

Run: `uv run uvicorn api.main:create_app_from_env --factory --port 8000`. Test: `uv run pytest tests/test_api.py`.
