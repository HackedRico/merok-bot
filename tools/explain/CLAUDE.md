# tools/explain

Explain: what is this. `explain(text, templates, llm, embedder) -> Explanation` matches a
pasted post to a mined template, by normalised text first and by embedding second, and asks
the model for a gloss written only from the facts it is handed.

Invariants: `similarity` is 1.0 for an exact normalised match, the cosine otherwise, and
`template` is None below the threshold. The gloss prompt contains every number the reply may
cite; the model is told to use nothing else.

Gotchas: the offline fake returns a placeholder gloss; the match still works without a model.

Test: `uv run pytest tests/test_explain.py`. Done when a teammate who has not seen the day's
top twenty templates can say what each meme is from the explanation.
