# tools/draft

Draft: say it my way. `retrieve(posts, author, intent, k, embedder) -> Exemplars` picks the
author's own past posts nearest the intent; `draft(intent, exemplars, template, llm) ->
list[Candidate]` asks the model for five posts in that voice, riding the template if one is
given; `turing_test(candidates, real, embedder) -> AUC` is the done-when as a number.

Invariants: exactly five candidates or a `ValueError`; every candidate is at most 280
characters; the persona prompt quotes the exemplars verbatim and nothing else about the
author. The Turing test is a cross-validated linear classifier over embeddings; 0.5 means
indistinguishable, 1.0 means trivially separable.

Gotchas: replies and retweets are dropped before retrieval, they are not the author's voice.
The offline fake model returns placeholders; `draft` still parses them, so the app runs.

Test: `uv run pytest tests/test_draft.py`.
