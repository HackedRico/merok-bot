from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# =============================================================================
# Module Overview
# =============================================================================
# The frozen values that cross tool lines. A tool takes these as arguments and
# returns them; it never imports another tool. `to_json` turns any of them into
# the plain dict the API sends to the app.


# =============================================================================
# Listen
# =============================================================================


@dataclass(frozen=True, slots=True)
class HourCount:
    """One point on a replication curve: distinct authors and posts in one UTC hour."""

    hour: datetime
    authors: int
    posts: int


SPAM_THRESHOLD = 0.5


@dataclass(frozen=True, slots=True)
class SpamVerdict:
    """How much a template's replication looks paid rather than organic, with the reasons."""

    score: float
    reasons: tuple[str, ...]
    # Stored, not a property, so it serialises with the rest; set from `score` at construction.
    is_spam: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "is_spam", self.score >= SPAM_THRESHOLD)


@dataclass(frozen=True, slots=True)
class Template:
    """A text pattern many authors posted, with its curve and its verdict."""

    text: str
    normalised: str
    authors: int
    posts: int
    first_seen: datetime
    first_authors: tuple[str, ...]
    sample_ids: tuple[str, ...]
    curve: tuple[HourCount, ...]
    spam: SpamVerdict


@dataclass(frozen=True, slots=True)
class Sound:
    """A TikTok sound spreading across creators; the same curve as a text template."""

    music_id: str
    title: str
    creators: int
    videos: int
    first_seen: datetime
    curve: tuple[HourCount, ...]


# =============================================================================
# Explain
# =============================================================================


@dataclass(frozen=True, slots=True)
class Explanation:
    """What a pasted post rides, where it came from, and a gloss grounded in those facts."""

    text: str
    template: Template | None
    similarity: float
    gloss: str


# =============================================================================
# Draft
# =============================================================================


@dataclass(frozen=True, slots=True)
class Exemplars:
    """An author's own past posts, retrieved for an intent, plus their median likes."""

    author: str
    posts: tuple[str, ...]
    median_likes: float


@dataclass(frozen=True, slots=True)
class Candidate:
    """One drafted post and the one-line reason the model gave for it."""

    text: str
    rationale: str
    template_text: str | None


# =============================================================================
# Score
# =============================================================================


@dataclass(frozen=True, slots=True)
class AuthorBaseline:
    """Median likes for an author in a period; the bar every forecast is measured against."""

    author: str
    median_likes: float
    posts: int


@dataclass(frozen=True, slots=True)
class Context:
    """What is true at posting time that the text alone does not say."""

    posted_at: datetime
    has_media: bool
    has_link: bool
    template_velocity: float


@dataclass(frozen=True, slots=True)
class Driver:
    """One feature's signed contribution to a forecast, in log-likes."""

    name: str
    effect: float
    detail: str


@dataclass(frozen=True, slots=True)
class Forecast:
    """Predicted likes, relative to the author's median, with the drivers that moved it."""

    likes_1d: float
    likes_1h: float | None
    relative_to_median: float
    drivers: tuple[Driver, ...]


# =============================================================================
# Render
# =============================================================================


@dataclass(frozen=True, slots=True)
class Caption:
    """A few words on screen between two timestamps."""

    text: str
    start_s: float
    end_s: float


@dataclass(frozen=True, slots=True)
class Clip:
    """A rendered 9:16 clip on disk and what went into it."""

    path: str
    duration_s: float
    captions: tuple[Caption, ...]
    sound: Sound | None
    voice_used: str
    visuals_used: str


# =============================================================================
# Ship and Learn
# =============================================================================


@dataclass(frozen=True, slots=True)
class PostId:
    """Where a post went and how to find it again."""

    platform: str
    id: str
    url: str | None


@dataclass(frozen=True, slots=True)
class CurvePoint:
    """Likes observed a number of minutes after posting."""

    minutes: float
    likes: int


@dataclass(frozen=True, slots=True)
class Curve:
    """Observed likes over the first minutes of a post's life."""

    post: PostId
    points: tuple[CurvePoint, ...]


@dataclass(frozen=True, slots=True)
class Comparison:
    """The observed curve against the forecast at the thirty-minute mark."""

    curve: Curve
    forecast: Forecast
    likes_at_30: int
    predicted_at_30: float
    verdict: str


# =============================================================================
# Chat
# =============================================================================


@dataclass(frozen=True, slots=True)
class Message:
    """One turn of the conversation, role is `user` or `assistant`."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Which tool the orchestrator ran and with what arguments."""

    tool: str
    args: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Attachment:
    """A value the app renders as a card; `kind` picks the card."""

    kind: str
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Reply:
    """The assistant's turn: text that quotes the numbers, plus what it ran and what to render."""

    text: str
    tool_calls: tuple[ToolCall, ...]
    attachments: tuple[Attachment, ...]


# =============================================================================
# Serialisation
# =============================================================================


def to_json(value: Any) -> Any:
    """Turn a frozen value, or a container of them, into JSON-ready plain data."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_json(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value
