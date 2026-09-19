from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from shared.types import PostId
from tools.learn import XPoller, observe
from tools.ship.x_api import COST_PER_POST_USD, COST_WITH_LINK_USD, OAuth1, XPublisher

# The X adapters against a fake transport: what goes over the wire, and the cap, without spending a cent.


def _transport(seen: list[httpx.Request], likes: int = 7) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={"data": {"id": "1830000000000000001", "text": json.loads(request.content)["text"]}})
        return httpx.Response(200, json={"data": {"id": "1830000000000000001", "public_metrics": {"like_count": likes}}})

    return httpx.MockTransport(handler)


def _publisher(tmp_path: Path, seen: list[httpx.Request], budget: float = 10.0) -> XPublisher:
    return XPublisher("ck", "cs", "at", "ats", budget, tmp_path, transport=_transport(seen))


def test_post_is_signed_and_recorded(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    pub = _publisher(tmp_path, seen)
    post = pub.post("Thursday's town hall is at 6pm.")
    assert post.platform == "x" and post.id == "1830000000000000001" and post.url.endswith(post.id) and post.posted_at is not None
    req = seen[0]
    assert req.url == "https://api.x.com/2/tweets" and json.loads(req.content) == {"text": "Thursday's town hall is at 6pm."}
    auth = req.headers["Authorization"]
    assert auth.startswith("OAuth ") and 'oauth_consumer_key="ck"' in auth and 'oauth_signature_method="HMAC-SHA1"' in auth and "oauth_signature=" in auth
    assert pub.spent_usd() == COST_PER_POST_USD


def test_the_cap_refuses_before_any_request(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    pub = _publisher(tmp_path, seen, budget=0.01)
    with pytest.raises(ValueError, match="budget"):
        pub.post("too expensive")
    assert seen == []
    pub2 = _publisher(tmp_path, seen, budget=0.5)
    pub2.post("with a link https://example.org")
    assert pub2.spent_usd() == COST_WITH_LINK_USD


def test_signature_is_deterministic_for_the_same_inputs() -> None:
    auth = OAuth1("ck", "cs", "at", "ats")
    params = {"oauth_nonce": "n", "oauth_timestamp": "1", "oauth_consumer_key": "ck", "oauth_token": "at", "oauth_signature_method": "HMAC-SHA1", "oauth_version": "1.0", "tweet.fields": "public_metrics"}
    a = auth.sign("GET", "https://api.x.com/2/tweets/1", params)
    b = auth.sign("GET", "https://api.x.com/2/tweets/1", dict(reversed(list(params.items()))))
    assert a == b and len(a) == 28


def test_live_poller_adds_one_point_per_call(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    poller = XPoller(_publisher(tmp_path, seen, budget=1.0).likes)
    post = PostId("x", "1830000000000000001", None, posted_at=datetime.now(timezone.utc) - timedelta(minutes=3))
    first = observe(post, minutes=60, source=poller)
    second = observe(post, minutes=60, source=poller)
    assert len(first.points) == 1 and len(second.points) == 2 and second.points[-1].likes == 7
    assert all(r.method == "GET" and "public_metrics" in str(r.url) for r in seen)
