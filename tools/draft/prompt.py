from __future__ import annotations

import json
import re

from shared.types import Exemplars, Template

# =============================================================================
# Module Overview
# =============================================================================
# The persona prompt and the parser for what comes back. The prompt carries
# the exemplars verbatim and asks for JSON; the parser accepts JSON first and
# numbered lines second, because small models drift.

DRAFT_COUNT = 5
MAX_CHARS = 280


def persona_system(exemplars: Exemplars) -> str:
    """The system prompt: be this account, shown by its own posts."""
    shown = "\n".join(f"- {p}" for p in exemplars.posts)
    return (
        f"You write posts for the X account @{exemplars.author}. Match its voice exactly: sentence length, "
        f"punctuation, capitalisation, the way it names people and policies, whether it uses emoji. "
        f"Here are real posts by the account:\n{shown}\n"
        f"Write only in that voice. Never mention that you are imitating anyone."
    )


def request(intent: str, template: Template | None) -> str:
    """The user turn: what to say, and the template to ride if one is live."""
    ride = ""
    if template is not None:
        ride = (
            f"\nA text template is spreading on X right now, posted by {template.authors} accounts in the last hours:\n"
            f'"{template.text}"\nAt least two of the five posts should ride that template: keep its structure and swap in the message.'
        )
    return (
        f"Write {DRAFT_COUNT} different posts that: {intent.strip()}{ride}\n"
        f"Each post is at most {MAX_CHARS} characters, with no links and no placeholders. Return JSON only: "
        f'a list of {DRAFT_COUNT} objects with keys "text" and "why", where "why" is one short sentence on the choice made.'
    )


def parse_candidates(raw: str) -> list[tuple[str, str]]:
    """Five (text, why) pairs from the model's answer, or a `ValueError` naming what came back."""
    pairs = _parse_json(raw) or _parse_lines(raw)
    pairs = [(t[:MAX_CHARS].strip(), w.strip()) for t, w in pairs if t.strip()]
    if len(pairs) < DRAFT_COUNT:
        raise ValueError(f"expected {DRAFT_COUNT} candidates, parsed {len(pairs)} from: {raw[:200]!r}")
    return pairs[:DRAFT_COUNT]


_TEXT_FIELD = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"')
_WHY_FIELD = re.compile(r'"why"\s*:\s*"((?:[^"\\]|\\.)*)"')


def _parse_json(raw: str) -> list[tuple[str, str]]:
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end <= start:
        return []
    body = raw[start : end + 1]
    items = None
    # Small models write \' inside strings, which JSON does not allow; the second try repairs just that.
    for attempt in (body, body.replace("\\'", "'")):
        try:
            items = json.loads(attempt)
            break
        except json.JSONDecodeError:
            continue
    if items is None:
        # Last resort: pull the "text" and "why" fields out by pattern, which survives most broken quoting.
        texts = [json.loads(f'"{m}"') if '\\' in m else m for m in _TEXT_FIELD.findall(body)]
        whys = _WHY_FIELD.findall(body)
        return [(t, whys[i] if i < len(whys) else "") for i, t in enumerate(texts)]
    out: list[tuple[str, str]] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append((item["text"], str(item.get("why", ""))))
        elif isinstance(item, str):
            out.append((item, ""))
    return out


_NUMBERED = re.compile(r"^\s*(?:\d+[.)]|-)\s+(.*\S)\s*$")


def _parse_lines(raw: str) -> list[tuple[str, str]]:
    return [(m.group(1).strip('"'), "") for line in raw.splitlines() if (m := _NUMBERED.match(line))]
