from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pyarrow as pa

from chat.session import Session
from shared.embed import Embedder
from shared.llm import LLM
from shared.text import has_link, truncate
from shared.types import Attachment, AuthorBaseline, Context, Template, to_json
from tools.draft import draft as draft_tool
from tools.draft import retrieve
from tools.explain import explain as explain_tool
from tools.learn import Poller, compare, observe
from tools.listen import listen as listen_tool
from tools.listen.curve import velocity
from tools.render import Visuals, Voice, render as render_tool
from tools.score import Traction, baseline_for
from tools.ship import Publisher

# =============================================================================
# Module Overview
# =============================================================================
# The seven tool declarations and the wiring that binds each to its adapters.
# `Deps` is everything the tools need, built once by `api/`; `Tools.run`
# executes one call against a session and returns the reply text and the
# cards. No logic beyond calling a tool and phrasing its result.


@dataclass(frozen=True)
class Deps:
    """Every adapter and table the tools need; `api/main.py` builds this from settings."""

    tweets: pa.Table
    own_posts: pa.Table
    demo_handle: str
    embedder: Embedder
    llm: LLM
    traction: Traction
    voice: Voice
    visuals: Visuals
    publisher: Publisher
    poller: Poller
    clip_dir: Path


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """A tool as the router and the model see it."""

    name: str
    description: str
    args: dict[str, str]


@dataclass(frozen=True, slots=True)
class ToolResult:
    """What a tool run produced: the reply text and the cards to render."""

    text: str
    attachments: tuple[Attachment, ...]


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("listen", "What is spreading on X right now: templates with their curves and a spam verdict.", {}),
    ToolSpec("explain", "What a pasted post is: the template it rides, its origin, organic or paid, in plain words.", {"text": "the post to explain"}),
    ToolSpec("draft", "Five posts in the account's own voice that do what the intent says, riding a live template.", {"intent": "what the post should do"}),
    ToolSpec("score", "Predicted likes for a draft against the account's median, with the drivers.", {"index": "which draft, one-based", "text": "or a post to score directly"}),
    ToolSpec("render", "Turn a draft into a captioned 9:16 clip for TikTok.", {"index": "which draft, one-based"}),
    ToolSpec("ship", "Post a draft.", {"index": "which draft, one-based"}),
    ToolSpec("learn", "How the last post is doing against its forecast.", {}),
)


class Tools:
    """The bound tools for one deployment; `run` executes one against a session."""

    def __init__(self, deps: Deps) -> None:
        self._d = deps
        self._baseline: AuthorBaseline = baseline_for(deps.demo_handle, deps.own_posts.column("like_count").to_pylist())
        self._mined: list[Template] | None = None
        self._runners: dict[str, Callable[[Session, dict[str, Any]], ToolResult]] = {
            "listen": self._listen,
            "explain": self._explain,
            "draft": self._draft,
            "score": self._score,
            "render": self._render,
            "ship": self._ship,
            "learn": self._learn,
        }

    @property
    def specs(self) -> tuple[ToolSpec, ...]:
        return SPECS

    @property
    def baseline(self) -> AuthorBaseline:
        return self._baseline

    def run(self, name: str, args: dict[str, Any], session: Session) -> ToolResult:
        """Execute `name` with `args` against `session`."""
        if name not in self._runners:
            raise ValueError(f"unknown tool {name!r}; the tools are {[s.name for s in SPECS]}")
        return self._runners[name](session, args)

    # -----------------------------------------------------------------
    # Listen and Explain
    # -----------------------------------------------------------------

    def _templates(self, session: Session) -> list[Template]:
        # The window is fixed for the life of the server, so mine it once and share it across conversations.
        if self._mined is None:
            self._mined = listen_tool(self._d.tweets, min_authors=5, max_templates=20)
        session.templates = self._mined
        return self._mined

    def _listen(self, session: Session, args: dict[str, Any]) -> ToolResult:
        templates = self._templates(session)
        organic = [t for t in templates if not t.spam.is_spam]
        paid = [t for t in templates if t.spam.is_spam]
        if not templates:
            return ToolResult("Nothing is replicating across five or more accounts in this window.", ())
        top = organic[0] if organic else templates[0]
        text = (
            f"{len(templates)} templates are moving in this window, {len(organic)} organic and {len(paid)} paid. "
            f'The top organic one is "{truncate(top.text, 90)}", posted by {top.authors} accounts, '
            f"{velocity(top.curve):.0f} of them in its latest hour."
        )
        return ToolResult(text, (Attachment("templates", {"templates": to_json(templates)}),))

    def _explain(self, session: Session, args: dict[str, Any]) -> ToolResult:
        text = str(args.get("text", "")).strip()
        if not text:
            raise ValueError("paste the post to explain")
        e = explain_tool(text, self._templates(session), self._d.llm, self._d.embedder)
        session.explanation = e
        if e.template is None:
            head = f"That is not a template I have seen spreading (best match {e.similarity:.0%})."
        else:
            kind = "paid replication" if e.template.spam.is_spam else "organic"
            head = f"It rides a template posted by {e.template.authors} accounts since {e.template.first_seen:%b %d %H:%M} UTC, {kind}."
        return ToolResult(f"{head} {e.gloss}", (Attachment("explanation", to_json(e)),))

    # -----------------------------------------------------------------
    # Draft and Score
    # -----------------------------------------------------------------

    def _ride(self, session: Session) -> Template | None:
        organic = [t for t in self._templates(session) if not t.spam.is_spam]
        return organic[0] if organic else None

    def _context(self, text: str, template: Template | None) -> Context:
        return Context(
            posted_at=datetime.now(timezone.utc),
            has_media=False,
            has_link=has_link(text),
            template_velocity=velocity(template.curve) if template else 0.0,
        )

    def _draft(self, session: Session, args: dict[str, Any]) -> ToolResult:
        intent = str(args.get("intent", "")).strip()
        if not intent:
            raise ValueError("say what the post should do")
        exemplars = retrieve(self._d.own_posts, self._d.demo_handle, intent, k=5, embedder=self._d.embedder)
        template = self._ride(session)
        candidates = draft_tool(intent, exemplars, template, self._d.llm)
        forecasts = [self._d.traction.predict(c.text, self._baseline, self._context(c.text, template)) for c in candidates]
        session.candidates, session.forecasts = candidates, forecasts
        best = max(range(len(forecasts)), key=lambda i: forecasts[i].likes_1d)
        ride = f' Two ride "{truncate(template.text, 60)}", which {template.authors} accounts posted.' if template else ""
        text = (
            f"Five drafts in @{self._d.demo_handle}'s voice, from {len(exemplars.posts)} of its own posts.{ride} "
            f"Draft {best + 1} scores highest: about {forecasts[best].likes_1d:.0f} likes in a day, "
            f"{forecasts[best].relative_to_median:.1f}x the account's median of {self._baseline.median_likes:.0f}."
        )
        cards = Attachment("candidates", {"candidates": to_json(candidates), "forecasts": to_json(forecasts), "baseline": to_json(self._baseline)})
        return ToolResult(text, (cards,))

    def _score(self, session: Session, args: dict[str, Any]) -> ToolResult:
        text = str(args.get("text", "")).strip()
        if not text:
            text = session.candidate(int(args.get("index", 1))).text
        template = self._ride(session)
        f = self._d.traction.predict(text, self._baseline, self._context(text, template))
        top = f.drivers[0] if f.drivers else None
        why = f" The biggest driver: {top.detail} ({'+' if top.effect > 0 else ''}{top.effect:.2f} log-likes)." if top else ""
        hour = f" About {f.likes_1h:.0f} in the first hour." if f.likes_1h is not None else ""
        text_out = f"About {f.likes_1d:.0f} likes in a day, {f.relative_to_median:.1f}x the median.{hour}{why}"
        return ToolResult(text_out, (Attachment("forecast", {"text": text, "forecast": to_json(f)}),))

    # -----------------------------------------------------------------
    # Render, Ship, Learn
    # -----------------------------------------------------------------

    def _render(self, session: Session, args: dict[str, Any]) -> ToolResult:
        candidate = session.candidate(int(args.get("index", 1)))
        clip = render_tool(candidate, self._d.voice, self._d.visuals, None, self._d.clip_dir)
        session.clip = clip
        text = f"Rendered a {clip.duration_s:.0f}-second clip with {len(clip.captions)} captions, voice {clip.voice_used}, background {clip.visuals_used}."
        return ToolResult(text, (Attachment("clip", to_json(clip)),))

    def _ship(self, session: Session, args: dict[str, Any]) -> ToolResult:
        index = int(args.get("index", 1))
        candidate = session.candidate(index)
        post = self._d.publisher.post(candidate.text)
        session.post = post
        session.posted_forecast = session.forecasts[index - 1] if index - 1 < len(session.forecasts) else None
        if post.platform == "x":
            head = f"Posted draft {index} to X: {post.url}"
        elif post.id == "clipboard":
            head = f"Draft {index} is on your clipboard for {post.platform}; the X credentials are not set, so nothing was posted."
        else:
            head = f"Posted draft {index} to {post.platform} as {post.id}."
        return ToolResult(head, (Attachment("post", {"post": to_json(post), "text": candidate.text}),))

    def _learn(self, session: Session, args: dict[str, Any]) -> ToolResult:
        if session.post is None:
            raise ValueError("nothing has been posted yet")
        curve = observe(session.post, minutes=14 * 24 * 60, source=self._d.poller)
        forecast = session.posted_forecast or self._d.traction.predict(session.candidates[0].text, self._baseline, self._context(session.candidates[0].text, None))
        c = compare(curve, forecast)
        span = curve.points[-1].minutes / 60 if curve.points else 0
        text = f"{len(curve.points)} observations over {span:.0f} hours: {c.likes_at_30} likes against {c.predicted_at_30:.0f} forecast, {c.verdict}."
        return ToolResult(text, (Attachment("comparison", to_json(c)),))
