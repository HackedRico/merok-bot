# tools/listen

Listen: what is spreading now. `listen(tweets, min_authors=5) -> list[Template]` over a
firehose table from `shared.data`; `sounds(videos, min_creators=5) -> list[Sound]` over a
TikTok table. Pure: same table in, same list out.

Invariants: a template is keyed on `shared.text.normalise`; `authors` counts distinct
`author_id`; the curve is distinct authors per UTC hour and its posts sum to `posts`;
`spam.score` is in [0, 1] with at least one reason either way.

Gotchas: airdrop copy tops the list unfiltered, so the verdict is returned, never applied.
Repeat snapshots are collapsed with `shared.data.latest` first. The TikTok shard is gated,
so `sounds` is tested on a synthetic table.

Test: `uv run pytest tests/test_listen.py`. Done when the fixture hour yields at least 25
templates at five authors and the join-date template outranks the airdrop copy on organic.
