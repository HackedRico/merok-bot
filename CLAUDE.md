# merok-bot

HopHacks 2026 entry, Best Memetics Hack. The prize is for a phenomenon; the app is the
instrument that demonstrates it. Read docs/architecture.md before touching `shared/`,
`tools/`, `chat/` or `api/`. It holds every tool's interface and the reason behind the layout. docs/plan.md holds the schedule and
the cut order. docs/prior-art.md holds what the judge has read.

## Run

```
uv sync && cp .env.example .env
uv run pytest                                                   # fixtures only, no network
uv run uvicorn api.main:create_app_from_env --factory --port 8000
cd app && npm install && npx expo start --web                   # http://localhost:8081
```

## Layout

- Four Python packages at the repo root, no wrapper. They import as themselves:
  `from shared.types import Template`, `from tools.draft import draft`.
- `shared/` is everything more than one tool needs: `types.py` (frozen values that cross
  tool lines), `text.py`, `embed.py`, `slang.py`, `config.py`, `data/` (the lake seam),
  `llm/` (the model seam: any OpenAI-compatible endpoint, or the offline fake).
- `tools/<verb>/` one directory per chat verb: listen, explain, draft, score, render, ship,
  learn. Each carries a CLAUDE.md: interface, invariants, gotchas, test command.
- `chat/` routes one message to one tool. `api/` serves it and is the only place that reads
  config.
- `analysis/` the two pitch charts. `app/` Expo. `tests/fixtures/` one firehose hour, 200
  government rows, a few thousand TikTok rows. Full tree in docs/architecture.md.

## Rules

- A tool imports `shared` and nothing else in the repo. Only `chat/` and `analysis/` call
  more than one tool. `tests/test_imports.py` enforces this, and also fails if a dependency
  installs a top-level `shared`, `tools`, `chat` or `api`.
- An interface change goes into `shared/types.py` or the tool's CLAUDE.md first, then the
  channel, then code.
- The tool's test over the fixture is its contract. Green before push. If it will not go
  green, say so and leave the test as it is.
- Side effects only at seams: data, LLM, voice, visuals, publisher, poller. Everything else
  takes values and returns values. Render writes one file and returns its path.
- Every line explainable at the table. Types on every signature, one-line doc comments on
  public functions, why-only comments, validate first.

## Data gotchas the schema does not confess

- Firehose rows repeat per `(id, version)`. Latest version for state, group by id for curves.
- Half the rows are retweets and 26 percent are English. Originals are `lang = 'en'`, body
  not starting `RT @`, `reply_to_status_id` null.
- In the government file `in_reply_to_tweet_id` is the string `'0'` for an original post, not
  null. Treat null, empty and `'0'` as "not a reply".
- Firehose repeat snapshots arrive days after a tweet is created (median first observation
  about two days in), so "the first thirty minutes" mostly does not exist in the data. Learn
  compares at whatever checkpoint the curve reaches and names it.
- 64 percent of tweets have zero likes. Predict log likes or beats-own-median.
- Tweets created after September 10 have not matured. Label only older ones.
- Airdrop spam tops naive template mining. Split by author repetition, links and zero views,
  and keep the verdict: the split is part of the pitch.
- Government engagement rose across the board after January 2025. Baselines are per author
  per month, or the meme effect is confounded with the regime change.
- TikTok is 27 shards on Hugging Face, about 11 GB each. Read one, music id columns only.
  The join key for a sound spreading across videos is `music_id`. The clip never downloads
  or mixes TikTok audio; the sound is named on the clip and added in TikTok's upload editor.
- Generated video is slow and paid: Veo 3.1 Fast is one to two minutes and about $0.15 a
  second, 8 seconds per generation, through the Gemini API. Default to the shipped loops,
  cap dollars in config, and render the demo finale ahead of time. Grok Imagine is
  image-to-video only, so it is not a text-to-video option. Credits: MLH's Google Program
  Benefits give $10 a month on the Gemini API key; a new Google Cloud account's $300 trial
  funds the Vertex backend. The Gemini app student plan does not fund the API. Free credits
  only: `MEROK_VEO_BACKEND=gemini`, `MEROK_VEO_BUDGET_USD=10`, and the adapter refuses a
  call that would cross the cap.
- Posting is live by default: `MEROK_PUBLISHER=x` with the four `X_*` credentials (OAuth 1.0a
  user context, write permission) posts for real on pay-per-use, inside `MEROK_X_BUDGET_USD`
  and a ledger at `.cache/x_ledger.json`. Without the credentials the publisher falls back to
  the clipboard and Learn to replay, and `/health` says so. The dry run exists for tests.
- The bucket is public, no credentials:
  `https://calcifer-hot.s3.us-east-2.amazonaws.com/hopkins-hackathon-2026/`. Read one hour
  file at a time over HTTPS; DuckDB does it in 8 seconds. The month is 55.7 GB and stays
  in the bucket.
