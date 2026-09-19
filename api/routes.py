from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from chat import Deps, Session, Tools, respond
from shared.config import Settings
from shared.types import to_json

# =============================================================================
# Module Overview
# =============================================================================
# The HTTP surface: one chat route, health, the tool list, and the rendered
# clips. Each handler is a few lines; anything longer belongs in a tool.

router = APIRouter()


@dataclass
class State:
    """What the app holds between requests."""

    settings: Settings
    deps: Deps
    tools: Tools
    sessions: dict[str, Session] = field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


def _state(request: Request) -> State:
    return request.app.state.merok


@router.get("/health")
def health(request: Request) -> dict:
    st = _state(request)
    return {
        "status": "ok",
        "data_source": st.settings.data_source,
        "rows": st.deps.tweets.num_rows,
        "demo_handle": st.deps.demo_handle,
        "llm": st.deps.llm.name,
        "llm_configured": st.settings.llm_configured,
        "voice": st.deps.voice.name,
        "visuals": st.deps.visuals.name,
        "publisher": st.deps.publisher.name,
        "poller": st.deps.poller.name,
        "baseline": to_json(st.tools.baseline),
    }


@router.get("/tools")
def tools(request: Request) -> list[dict]:
    return [to_json(s) for s in _state(request).tools.specs]


@router.post("/chat")
def chat(body: ChatRequest, request: Request) -> dict:
    st = _state(request)
    cid = body.conversation_id or uuid.uuid4().hex[:10]
    session = st.sessions.setdefault(cid, Session())
    reply = respond(body.message, session, st.tools, st.deps.llm)
    return {"conversation_id": cid, "reply": to_json(reply)}


@router.post("/reset/{conversation_id}")
def reset(conversation_id: str, request: Request) -> dict:
    _state(request).sessions.pop(conversation_id, None)
    return {"conversation_id": conversation_id, "reset": True}


@router.get("/clips/{name}")
def clip(name: str, request: Request) -> FileResponse:
    path = (_state(request).deps.clip_dir / Path(name).name).resolve()
    if not path.is_file() or path.suffix != ".mp4":
        raise HTTPException(404, "no such clip")
    return FileResponse(path, media_type="video/mp4")
