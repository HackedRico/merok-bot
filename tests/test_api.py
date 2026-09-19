from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from shared.config import Settings


@pytest.fixture(scope="module")
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def test_health_names_every_adapter(client: TestClient) -> None:
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["data_source"] == "fixture" and h["rows"] > 50_000
    assert h["llm"] == "fake" and h["voice"] == "silent" and h["publisher"] == "dry_run" and h["poller"] == "replay"
    assert h["x_configured"] is False and h["x_budget_usd"] == 10.0
    assert h["baseline"]["author"] == "sensanders"


def test_chat_keeps_a_conversation(client: TestClient) -> None:
    first = client.post("/chat", json={"message": "What are people posting this hour?"}).json()
    cid = first["conversation_id"]
    assert first["reply"]["tool_calls"][0]["tool"] == "listen"
    assert first["reply"]["attachments"][0]["kind"] == "templates"
    second = client.post("/chat", json={"message": "Help me announce Thursday's town hall.", "conversation_id": cid}).json()
    assert second["reply"]["tool_calls"][0]["tool"] == "draft"
    third = client.post("/chat", json={"message": "post the second one", "conversation_id": cid}).json()
    assert third["reply"]["tool_calls"][0]["tool"] == "ship"
    assert client.post("/reset/" + cid).json()["reset"] is True


def test_root_points_at_the_app(client: TestClient) -> None:
    assert client.get("/").json()["app"].endswith(":8081")


def test_tools_and_clips_routes(client: TestClient) -> None:
    names = [t["name"] for t in client.get("/tools").json()]
    assert names == ["listen", "explain", "draft", "score", "render", "ship", "learn"]
    assert client.get("/clips/nope.mp4").status_code == 404
