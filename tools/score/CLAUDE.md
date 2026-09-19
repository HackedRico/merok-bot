# tools/score

Score: will it travel. `Traction.fit(labelled, embedder) -> Traction`, then
`Traction.predict(text, author: AuthorBaseline, context: Context) -> Forecast` with likes at a
day, likes at an hour when the training data had hour snapshots, the ratio to the author's
median, and the drivers that moved the number.

Invariants: the target is log1p(likes), never raw likes (64 percent are zero). The author
baseline is leave-one-out: a row never sees its own likes in its feature. Drivers are
counterfactual: each named feature is swapped for the training median and the change in the
prediction is its effect, so they sum roughly to the distance from a typical post.

Gotchas: most firehose authors have one post, so their baseline is unknown and flagged, not
zero. The firehose almost never shows an account with thousands of likes, so for a known
account (twenty posts or more of history) the model supplies a multiplier against a typical
post by that account and the level comes from the account's own median. Tweets created after September 10 have not matured; `fit` is given older rows.

Test: `uv run pytest tests/test_score.py`. Done when the model beats "predict the author's
median" on held-out rows of the fixture hour, by mean absolute error in log space.
