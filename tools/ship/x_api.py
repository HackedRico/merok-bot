from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from shared.types import PostId
from tools.ship.publisher import validate_post

# =============================================================================
# Module Overview
# =============================================================================
# The real publisher: POST /2/tweets on the X API with OAuth 1.0a user
# context, signed here with the standard library so there is no dependency
# whose surface the team would have to explain. The only code in the repo
# that spends money, so it checks a dollar cap against a ledger on disk
# before every call.

API = "https://api.x.com/2"
# Pay-per-use prices as of the brief (February 2026): a post, and a post carrying a link.
COST_PER_POST_USD = 0.015
COST_WITH_LINK_USD = 0.20
LEDGER = "x_ledger.json"


class XPublisher:
    """Adapter: post to X as the authorised user, inside a spend cap."""

    name = "x"

    def __init__(self, consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str, budget_usd: float, ledger_dir: Path, transport: httpx.BaseTransport | None = None) -> None:
        for label, value in (("consumer_key", consumer_key), ("consumer_secret", consumer_secret), ("access_token", access_token), ("access_token_secret", access_token_secret)):
            if not value:
                raise ValueError(f"X {label} is empty; set the four `X_*` variables in .env")
        if budget_usd <= 0:
            raise ValueError("budget_usd must be positive")
        self._auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
        self.budget_usd = budget_usd
        self._ledger = Path(ledger_dir) / LEDGER
        self._client = httpx.Client(transport=transport, timeout=30)

    # -----------------------------------------------------------------
    # Spend ledger
    # -----------------------------------------------------------------

    def spent_usd(self) -> float:
        """Dollars this ledger has recorded so far."""
        if not self._ledger.is_file():
            return 0.0
        return float(json.loads(self._ledger.read_text()).get("spent_usd", 0.0))

    def _record(self, cost: float, post_id: str) -> None:
        state = json.loads(self._ledger.read_text()) if self._ledger.is_file() else {"spent_usd": 0.0, "posts": []}
        state["spent_usd"] = round(float(state["spent_usd"]) + cost, 4)
        state["posts"].append({"id": post_id, "cost_usd": cost, "at": datetime.now(timezone.utc).isoformat()})
        self._ledger.parent.mkdir(parents=True, exist_ok=True)
        self._ledger.write_text(json.dumps(state, indent=1))

    # -----------------------------------------------------------------
    # Posting
    # -----------------------------------------------------------------

    def post(self, text: str) -> PostId:
        cleaned = validate_post(text)
        cost = COST_WITH_LINK_USD if "http" in cleaned else COST_PER_POST_USD
        if self.spent_usd() + cost > self.budget_usd:
            raise ValueError(f"posting would cross the X budget of ${self.budget_usd:.2f}; raise `MEROK_X_BUDGET_USD` or stop")
        url = f"{API}/tweets"
        response = self._client.post(url, json={"text": cleaned}, headers={"Authorization": self._auth.header("POST", url)})
        if response.status_code >= 400:
            raise RuntimeError(f"X refused the post: {response.status_code} {response.text[:200]}")
        post_id = str(response.json()["data"]["id"])
        self._record(cost, post_id)
        return PostId(platform="x", id=post_id, url=f"https://x.com/i/web/status/{post_id}", posted_at=datetime.now(timezone.utc))

    def likes(self, post_id: str) -> int:
        """The post's current like count, one read."""
        url = f"{API}/tweets/{post_id}"
        params = {"tweet.fields": "public_metrics"}
        response = self._client.get(url, params=params, headers={"Authorization": self._auth.header("GET", url, params)})
        if response.status_code >= 400:
            raise RuntimeError(f"X refused the read: {response.status_code} {response.text[:200]}")
        return int(response.json()["data"]["public_metrics"]["like_count"])


# =============================================================================
# OAuth 1.0a
# =============================================================================


def _enc(value: str) -> str:
    return quote(str(value), safe="")


class OAuth1:
    """HMAC-SHA1 request signing per RFC 5849, the form X's v2 API accepts for user context."""

    def __init__(self, consumer_key: str, consumer_secret: str, token: str, token_secret: str) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._token = token
        self._token_secret = token_secret

    def header(self, method: str, url: str, params: dict[str, str] | None = None) -> str:
        oauth = {
            "oauth_consumer_key": self._consumer_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self._token,
            "oauth_version": "1.0",
        }
        oauth["oauth_signature"] = self.sign(method, url, {**(params or {}), **oauth})
        return "OAuth " + ", ".join(f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(oauth.items()))

    def sign(self, method: str, url: str, params: dict[str, str]) -> str:
        """The signature over method, base URL and every query and oauth parameter, sorted after encoding."""
        pairs = sorted((_enc(k), _enc(v)) for k, v in params.items())
        base = "&".join((method.upper(), _enc(url), _enc("&".join(f"{k}={v}" for k, v in pairs))))
        key = f"{_enc(self._consumer_secret)}&{_enc(self._token_secret)}".encode()
        return base64.b64encode(hmac.new(key, base.encode(), hashlib.sha1).digest()).decode()
