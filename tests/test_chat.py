from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pytest

from chat import Deps, Session, Tools, respond
from chat.router import ordinal, pasted_text, route_by_rules
from shared.embed import HashEmbedder
from shared.llm.fake import FakeLLM
from tools.learn.replay import ReplayPoller
from tools.render import LoopsVisuals, SilentVoice
from tools.score import Traction
from tools.ship import DryRunPublisher


@pytest.fixture(scope="module")
def tools(hour_table: pa.Table, gov_table: pa.Table, embedder: HashEmbedder, tmp_path_factory) -> Tools:
    drafts = json.dumps([{"text": f"Town hall Thursday at 6pm. Draft {i}.", "why": "plain"} for i in range(1, 6)])
    llm = FakeLLM(lambda system, messages: drafts if "You write posts" in system else "A meme about join dates.")
    deps = Deps(
        tweets=hour_table, own_posts=gov_table, demo_handle="sensanders", embedder=embedder, llm=llm,
        traction=Traction.fit(hour_table, embedder, max_rows=8_000), voice=SilentVoice(), visuals=LoopsVisuals(),
        publisher=DryRunPublisher(), poller=ReplayPoller(hour_table, seed=1), clip_dir=tmp_path_factory.mktemp("clips"),
    )
    return Tools(deps)


def test_rules_route_the_plans_example_messages() -> None:
    s = Session()
    assert route_by_rules("What are people posting this hour?", s).tool == "listen"
    assert route_by_rules('Someone posted this at me, what does it mean: "do you remember when you joined x? i do!"', s).tool == "explain"
    assert route_by_rules("Help me announce Thursday's town hall.", s).tool == "draft"
    assert route_by_rules("Turn the third one into a TikTok.", s) == route_by_rules("make draft 3 a clip", s)
    assert route_by_rules("Post the third one.", s).args == {"index": 3}
    assert route_by_rules("how did it do?", s) is None, "learn needs something posted first"
    assert ordinal("post the second one") == 2 and ordinal("post it") == 1
    assert pasted_text('what is "do you remember when you joined x"?') == "do you remember when you joined x"


def test_a_conversation_walks_the_loop(tools: Tools) -> None:
    llm = tools._d.llm
    s = Session()
    r = respond("What are people posting this hour?", s, tools, llm)
    assert r.tool_calls[0].tool == "listen" and r.attachments[0].kind == "templates" and "templates are moving" in r.text

    r = respond("Someone posted this at me, what does it mean: do you remember when you joined x? i do!", s, tools, llm)
    assert r.tool_calls[0].tool == "explain" and "rides a template" in r.text

    r = respond("Help me announce Thursday's town hall.", s, tools, llm)
    assert r.tool_calls[0].tool == "draft" and len(s.candidates) == 5 and len(s.forecasts) == 5
    assert "scores highest" in r.text

    r = respond("score draft 2", s, tools, llm)
    assert r.tool_calls[0].tool == "score" and "likes in a day" in r.text

    r = respond("Post the third one.", s, tools, llm)
    assert r.tool_calls[0].tool == "ship" and s.post is not None and "Draft 3" in s.candidates[2].text

    r = respond("How did it do?", s, tools, llm)
    assert r.tool_calls[0].tool == "learn" and "forecast" in r.text

    r = respond("Turn the third one into a TikTok.", s, tools, llm)
    assert r.tool_calls[0].tool == "render" and s.clip is not None and Path(s.clip.path).exists()


def test_validation_messages_become_replies(tools: Tools) -> None:
    r = respond("Post the third one.", Session(), tools, tools._d.llm)
    assert r.text.startswith("no drafts yet")
    assert respond("hi", Session(), tools, tools._d.llm).text.startswith("I can do seven things")
