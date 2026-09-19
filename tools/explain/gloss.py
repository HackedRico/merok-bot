from __future__ import annotations

from shared.types import Template

# =============================================================================
# Module Overview
# =============================================================================
# The gloss prompt. Every number the reply may use is in the request; the
# system prompt forbids anything else, so an explanation is only ever as
# wrong as the data.


def gloss_system() -> str:
    """The system prompt: explain a meme to someone who does not get it, from the facts only."""
    return (
        "You explain internet posts to someone who does not get them. Use only the facts given. "
        "Three sentences at most: what the post is, how it is spreading, and whether it looks organic or paid. "
        "If no template matched, say that it is not a pattern seen spreading and describe the post plainly."
    )


def gloss_request(text: str, template: Template | None, similarity: float) -> str:
    """The user turn: the post and the facts about the template it rides, if any."""
    if template is None:
        return f'Post: "{text}"\nFacts: no template in the current window matched it (best similarity {similarity:.2f}).'
    peak = max(template.curve, key=lambda h: h.authors) if template.curve else None
    peak_line = f"peak hour {peak.hour:%Y-%m-%d %H:00} UTC with {peak.authors} accounts" if peak else "no hourly curve"
    verdict = "paid replication" if template.spam.is_spam else "organic"
    return (
        f'Post: "{text}"\n'
        f"Facts: it matches a template (similarity {similarity:.2f}) whose representative text is \"{template.text}\". "
        f"{template.authors} distinct accounts posted it {template.posts} times, first seen {template.first_seen:%Y-%m-%d %H:%M} UTC, "
        f"{peak_line}. Verdict: {verdict}, because {'; '.join(template.spam.reasons)}."
    )
