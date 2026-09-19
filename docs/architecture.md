# merok-bot module design

Vocabulary from the codebase-design skill: module, interface, seam, adapter, depth. A module
is deep when a caller gets a lot of behaviour for a small interface. A seam is real only when
two adapters sit at it.

The event rule "every line explainable by the team" and the house rule "defend every line"
are the same bar. Four people vibe coding one repo for 36 hours need the rules below more
than they need any framework.

## What merok-bot is

A chat. The user types, the assistant answers with numbers it computed, drafts it wrote and
a clip it rendered. The assistant is one model turn that picks a tool. Each tool is one
directory under `tools/`, named by the verb the chat uses. The chat layer is thin; the tools
are deep.

Surfaces: Expo web in a laptop browser is the judging surface. The same Expo code runs on a
phone through Expo Go or the iOS Simulator for the demo, where the finale is the clip: the
phone plays it and the share sheet opens TikTok with it. The phone reaches the backend over
the network, which is why FastAPI runs on a DigitalOcean droplet from Saturday night.

## Layout

The Python code is four top-level packages, no wrapper. `shared/` is everything more than one
tool needs. `tools/` is one directory per chat verb. `chat/` routes. `api/` serves. They
import as themselves: `from shared.types import Template`, `from tools.draft import draft`.
Two consequences: `pyproject.toml` lists the four as packages, and no third-party dependency
may install a top-level `shared`, `tools`, `chat` or `api`, which `tests/test_imports.py`
also checks.

```
merok-bot/
├── CLAUDE.md                    agents read this first: rules, gotchas, pointers
├── README.md                    problem statement, how to run, the Devpost copy
├── pyproject.toml               uv project; packages = shared, tools, chat, api; duckdb, litellm, fastapi, lightgbm,
│                                sentence-transformers, elevenlabs, pytest; ffmpeg on the host
├── uv.lock
├── .python-version
├── .env.example                 ANTHROPIC_API_KEY, GEMINI_API_KEY, ELEVENLABS_API_KEY, X_API_KEY, MEROK_LLM_MODEL, MEROK_DATA_SOURCE
├── .gitignore                   .cache/, .env, *.duckdb, analysis/out/, app/node_modules/
│
├── shared/                      everything more than one tool needs
│   ├── CLAUDE.md
│   ├── __init__.py
│   ├── types.py                 frozen values that cross tool lines: Template, Sound, SpamVerdict, Explanation,
│   │                            Candidate, Exemplars, Forecast, Driver, Clip, PostId, Curve, Comparison, Reply
│   ├── text.py                  normalise(): lower, strip URLs, handles, hashtags
│   ├── embed.py                 embed(texts) -> vectors; hashing by default, nomic-embed behind the same protocol
│   ├── slang.py                 the slang and meme-format lexicon chart 2 counts
│   ├── config.py                env -> Settings; read only by api/ and scripts/, passed in everywhere else
│   ├── data/                    the lake seam
│   │   ├── __init__.py          firehose(), gov_tweets(), tiktok(), latest(), curves()
│   │   ├── bucket.py            adapter: DuckDB httpfs over the public S3 and the Hugging Face TikTok shard
│   │   ├── fixture.py           adapter: tests/fixtures parquet, same interface
│   │   └── cache.py             materialise into .cache/merok.duckdb
│   └── llm/                     the model seam
│       ├── __init__.py          LLM protocol: complete(system, messages) -> str
│       ├── openai_compat.py     any OpenAI-compatible endpoint: base URL, key, model name from config
│       └── fake.py              canned replies so no test hits the network; offline placeholders for a keyless demo
│
├── tools/                       one directory per chat verb; a tool imports shared and nothing else in the repo
│   ├── __init__.py
│   ├── listen/                  -> Template, Sound
│   │   ├── CLAUDE.md
│   │   ├── __init__.py          listen(tweets, min_authors) -> list[Template]; sounds(videos) -> list[Sound]
│   │   ├── cluster.py           exact match first, MinHash for mutations
│   │   ├── curve.py             distinct authors per hour; creators per hour by music id
│   │   └── spam.py              SpamVerdict from author repetition, links, zero views
│   ├── explain/                 -> Explanation
│   │   ├── CLAUDE.md
│   │   ├── __init__.py          explain(text, templates, llm) -> Explanation
│   │   ├── match.py             pasted text -> Template, by normalised text then embedding
│   │   └── gloss.py             the prompt: write from the facts given, cite them
│   ├── draft/                   -> Candidate
│   │   ├── CLAUDE.md
│   │   ├── __init__.py          draft(intent, exemplars, template, llm) -> list[Candidate]; retrieve(); turing_test()
│   │   ├── retrieve.py          exemplars by embedding over the author's past posts
│   │   ├── prompt.py            persona prompt, the Digital Twin method
│   │   └── turing.py            embedding classifier AUC; near 0.5 is done
│   ├── score/                   -> Forecast
│   │   ├── CLAUDE.md
│   │   ├── __init__.py          Traction.fit(), Traction.predict() -> Forecast
│   │   ├── features.py          Features (frozen) + FeatureBuilder
│   │   ├── model.py             gradient boosting over log likes, drivers per prediction
│   │   └── baseline.py          AuthorBaseline: median per author per month
│   ├── render/                  -> Clip
│   │   ├── CLAUDE.md
│   │   ├── __init__.py          render(candidate, voice, visuals, sound) -> Clip
│   │   ├── script.py            post text -> spoken script, caption chunks, a visual brief
│   │   ├── tts.py               Voice protocol: speak(text) -> audio + word timestamps
│   │   ├── elevenlabs.py        adapter: real voice, timestamps from the API
│   │   ├── silent.py            adapter: no audio, uniform timings, for tests
│   │   ├── visuals.py           Visuals protocol plus LoopsVisuals: an ffmpeg gradient, instant, free, offline
│   │   ├── compose.py           ffmpeg: 1080x1920, Pillow-drawn captions overlaid, voice or silence as the audio track
│   │   └── (Part 2)             still.py and veo.py behind the same Visuals protocol
│   ├── ship/                    -> PostId
│   │   ├── CLAUDE.md
│   │   ├── __init__.py          Publisher protocol: post(text) -> PostId
│   │   ├── x_api.py             adapter: pay per use, budget cap validated before the call
│   │   ├── clipboard.py         adapter: TikTok, Instagram, LinkedIn export
│   │   └── dry_run.py           adapter: rehearsal, returns a fake PostId
│   └── learn/                   -> Curve, Comparison
│       ├── CLAUDE.md
│       ├── __init__.py          observe(post, minutes, source) -> Curve; compare(curve, forecast) -> Comparison
│       ├── x_poll.py            adapter: X API once a minute
│       └── replay.py            adapter: a firehose trajectory from shared.data.curves()
│
├── chat/                        the orchestrator
│   ├── CLAUDE.md
│   ├── __init__.py              respond(message, session, tools, llm) -> Reply
│   ├── router.py                rules first, the model as a JSON choice second, draft third
│   ├── session.py               what a conversation remembers, so "post the third one" resolves
│   └── tools.py                 seven declarations bound to their adapters; reply text is built from the values
│
├── api/                         FastAPI
│   ├── CLAUDE.md
│   ├── __init__.py
│   ├── main.py                  app factory: builds adapters from config, warms templates and the model
│   └── routes.py                /chat, /health, /tools, /clips/{name}
│
├── analysis/                    the two pitch charts; imports tools and shared, adds only plotting
│   ├── template_curves.py       chart 1: distinct authors per hour, organic vs paid
│   ├── gov_memes.py             chart 2: template share per account per month vs own baseline
│   └── out/                     PNG + JSON, gitignored except the two final charts
│
├── tests/
│   ├── conftest.py              fixture data source, fake LLM, silent voice, dry-run publisher, replay poller
│   ├── fixtures/
│   │   ├── firehose_hour.parquet   one hour of English originals, about 5 MB
│   │   ├── gov_sample.parquet      200 rows from one press office
│   │   └── tiktok_sample.parquet   a few thousand rows from one shard, for sounds
│   ├── test_imports.py          the import rule as a test: no tool imports another tool, chat or api
│   ├── test_shared.py           data, text, embed
│   ├── test_listen.py           reproduces 30 templates at 5+ authors from the fixture
│   ├── test_explain.py
│   ├── test_draft.py            turing_test near 0.5
│   ├── test_score.py            beats predict-the-median on held-out rows
│   ├── test_render.py           silent voice, a clip renders under a minute, captions match the script
│   ├── test_ship.py
│   ├── test_learn.py
│   └── test_chat.py             each example message routes to the right tool
│
├── app/                         Expo, one codebase for laptop web and phone
│   ├── app.json
│   ├── package.json
│   ├── App.tsx
│   ├── .env.example             EXPO_PUBLIC_API_URL: localhost on the laptop, the droplet on the phone
│   └── src/
│       ├── api.ts               one client for /chat
│       ├── screens/Chat.tsx
│       └── components/          CurveCard, DraftCard, ExplainCard, ForecastBadge, ClipCard (plays, share sheet)
│
├── scripts/
│   ├── pull_month.py            background pull of English originals into .cache, resumable
│   ├── pull_gov.py              the government file, one download
│   ├── pull_sounds.py           one TikTok shard, music id columns only; needs HF_TOKEN, the set is gated
│   └── make_fixture.py          cut the fixtures from a bucket file
│
└── docs/
    ├── architecture.md
    ├── plan.md
    ├── prior-art.md
    └── pitch.md                 the ten minutes, slide by slide
```

Every tool directory carries a `CLAUDE.md` of about ten lines: the interface, its invariants,
the gotchas, and the test command that is its done-when. An agent opening that directory
reads it before the code. `shared/` has one too.

## Rules that keep four people out of each other's way

1. **A tool imports `shared` and nothing else in the repo.** Tools talk through the frozen
   values in `shared/types.py`. Draft needs a template: it takes a `Template` as an
   argument. Score needs template velocity: it is a field on `Context`. Only `chat/` and
   `analysis/` call more than one tool. `tests/test_imports.py` fails the build when a tool
   imports another tool, `chat` or `api`.
2. **The interface changes first, in writing.** Edit `shared/types.py` or the tool's
   `CLAUDE.md`, say so in the channel, then code. Interfaces freeze Saturday 9 AM.
3. **The test is the contract.** Each tool has one test file over the fixture that encodes
   its done-when. Green before push. An agent that cannot make it green says so and leaves
   the test as it is.
4. **Side effects only at seams.** Data, LLM, voice, visuals, publisher, poller. Everything
   else takes values and returns values. Render writes one file and returns its path.
5. **One owner per tool.** Owners review each other's PRs in minutes, not hours. Main always
   runs the demo.

## Tools and their interfaces

Each interface is the whole contract: signature, invariants, error modes, and what it costs.
Return frozen values. Accept dependencies as arguments. Never construct a client inside.

### `shared.data`, the lake seam

```
firehose(hours: HourRange, lang: str | None = "en", originals_only: bool = True) -> Relation
gov_tweets(handles: list[str] | None = None) -> Relation
tiktok(shard: int = 0) -> Relation          # music id columns only
latest(rel: Relation) -> Relation           # one row per id, max version
curves(rel: Relation) -> Relation           # (id, version, like_count, ...) ordered
```

Hides: HTTPS range reads through DuckDB httpfs, file-to-hour mapping, retweet and reply
filters, the version dedupe, the local DuckDB cache. Two adapters: the public bucket plus the
Hugging Face shard, and the fixtures directory for tests and for the demo table if the venue
wifi dies. Measured cost: one hour file is about 140 MB and 8 seconds over HTTPS; a day is
about four minutes.

Deletion test: remove this module and every caller re-learns the version quirk, the retweet
share and the language mix. It earns its keep.

### `shared.llm`, the model seam

```
LLM.complete(system: str, messages: list[Message]) -> str
```

One method. Two adapters: `OpenAICompatLLM`, which speaks to any OpenAI-compatible endpoint
(Featherless, Gemini, Anthropic, OpenAI) so a base URL, a key and a model name are the whole
configuration, and `FakeLLM`, which keeps tests off the network and gives a keyless demo
visibly marked placeholders. Explain, Draft and the chat all take an `LLM` as an argument.
LiteLLM was in the first plan and was dropped: the endpoint the team has is OpenAI-compatible
and the plain client drops about a hundred transitive dependencies. LangChain was rejected
for the same reason, plus abstractions the app does not use.

### `shared.text`, `shared.embed`, `shared.types`

Module-level functions with no state. Listen, Explain, Draft and Score all need identical
normalisation and identical vectors; `types.py` holds every frozen value that crosses a tool
line. The default embedder is character n-gram hashing through scikit-learn: deterministic,
offline, 100k posts a second; nomic-embed sits behind the same protocol for Part 2. Splitting
these out is what stops four people writing four normalisers.

### `tools.listen`

```
listen(tweets: Relation, min_authors: int = 5) -> list[Template]
sounds(videos: Relation, min_creators: int = 5) -> list[Sound]
Template: text, normalised, curve: tuple[HourCount, ...], authors: int, first_seen, spam: SpamVerdict
Sound: music_id, title, curve: tuple[HourCount, ...], creators: int, first_seen
SpamVerdict: score, reasons: tuple[str, ...]
```

Hides: normalisation via `shared.text`, exact match first then MinHash for mutations, the
distinct-author curve, the spam split by author repetition, link share and zero views.
Pure over the relation it is handed. The verdict carries reasons because the split is part
of the pitch, not a filter to hide. A sound is a template on TikTok: creators per hour on
one music id is the same curve. Done when the feed shows curves over the month with spam
split from organic.

### `tools.explain`

```
explain(text: str, templates: list[Template], llm: LLM) -> Explanation
Explanation: template: Template | None, gloss: str, first_seen, first_authors: tuple[str, ...], verdict: SpamVerdict
```

Hides: matching a pasted post to a mined template by normalised text then by embedding, the
origin lookup (first hour, first authors), and the plain-language gloss the model writes from
those facts. The gloss cites the numbers it was given, nothing else. This is the dropped
slang-translator idea done right: grounded in the curve, not guessed. Done when a teammate who
has not seen the day's top twenty templates reads each explanation and can say what the meme is.

### `tools.draft`

```
draft(intent: str, exemplars: Exemplars, template: Template | None, llm: LLM) -> list[Candidate]
retrieve(author: str, intent: str, k: int = 5) -> Exemplars
turing_test(candidates: list[Candidate], real: list[str]) -> float   # classifier AUC
```

Hides: the persona prompt, exemplar retrieval by embedding, the model call. This is the
sponsor's Digital Twin method. `turing_test` is the completion criterion as a function: near
0.5 means done.

### `tools.score`

```
Traction.fit(labelled: Relation, embed: Embedder) -> Traction
Traction.predict(text: str, author: AuthorBaseline, context: Context) -> Forecast
Forecast: likes_1h, likes_1d, relative_to_median, drivers: tuple[Driver, ...]
```

Hides: feature building (embedding, hour of day, length, media flag, template velocity at post
time, author median), gradient boosting, the log target. Features use the immutable value plus
builder split: `Features` is frozen, `FeatureBuilder` accumulates. The completion criterion,
beats "predict the author's median" on held-out September tweets, is a test, not a notebook.

### `tools.render`

```
render(candidate: Candidate, voice: Voice, visuals: Visuals, sound: Sound | None) -> Clip
Clip: path, duration_s, captions: tuple[Caption, ...], sound: Sound | None, visuals_used: str
```

Hides: turning a post into a spoken script, caption chunks and a one-line visual brief; the
voice call; the background; and the ffmpeg composition: 1080 by 1920, about twenty seconds,
word-timed captions burned over the background, the voice as the audio track. The pipeline
inside is script, then voice, then visuals, then compose, and each of the middle two is a seam.

`Voice` is a protocol of one method, `speak(text) -> audio + word timestamps`, with two
adapters: ElevenLabs, which returns timestamps from its API, and a silent fake with uniform
timings so the test renders offline.

`Visuals` is the video generation layer: one method, `generate(brief, seconds) -> path`,
returning a 9:16 background video. Three adapters, cheapest first, and the caller picks:

| Adapter | What it does | Time | Cost | When |
|---|---|---|---|---|
| `loops` | one of three shipped loops, picked by mood | instant | free | default, and the test adapter |
| `still` | one generated image, then ffmpeg zoom and pan | seconds | cents | "give it a picture" |
| `veo` | Veo 3.1 Fast through the Gemini API, text to video, 8 s per generation, so one hero shot plus a loop | one to two minutes | about $0.15 a second, about $1.20 a shot | "make it cinematic", and the pre-rendered finale |

The `veo` adapter uses the `google-genai` SDK, which talks to the Gemini API with a key or
to Vertex AI with a project and location behind one flag, so `MEROK_VEO_BACKEND=gemini|vertex`
is a config string, not code. Credits: the MLH Google Program Benefits give $10 a month on
the Gemini API, about eight Fast shots, enough for the finale and a few tests; a new Google
Cloud account's $300 trial funds the Vertex path for iterating on prompts. The Gemini app
student plan is a consumer subscription and does not fund the API; it is a manual fallback
for one hero shot through Flow if the API path fails.

The clip's done-when, under a minute, holds for `loops` and `still`. `veo` is opt-in per
clip, the chat says it will take a couple of minutes, and the finale clip for the table is
rendered ahead of time, never live against a video API. The Veo adapter validates a dollar
cap from config before calling, the same way the X adapter does. Grok Imagine on the xAI API
was checked and left out: as of June 2026 it is image-to-video only, so it would sit behind
`still`, and it adds nothing the Veo adapter does not.

The trending sound is named on the clip, not mixed in: TikTok's upload editor adds it, and
that keeps the render free of anyone's audio. Posting is a manual upload through the phone's
share sheet because TikTok and Instagram lock unaudited apps out of their posting APIs.
Done when a clip renders from a draft in under a minute with `loops` and the phone shares it
into TikTok.

Owner: the Draft owner, since the clip is the draft spoken. This is the one tool that can
move to whoever finishes first on Saturday afternoon.

### `tools.ship`

```
Publisher.post(text: str) -> PostId
```

Three adapters: X pay-per-use API, clipboard export for TikTok, Instagram and LinkedIn,
dry-run fake. Real seam. The X adapter is the only code that spends money; it validates a
budget cap up front and raises before calling out.

### `tools.learn`

```
observe(post: PostId, minutes: int = 30, source: Poller) -> Curve
compare(curve: Curve, forecast: Forecast) -> Comparison
```

Hides polling cadence and rate limits. `Poller` has the X adapter and a replay adapter that
serves a firehose trajectory from `shared.data.curves`, so the demo screen can be rehearsed
without posting.

### `chat`, the orchestrator

```
respond(history: list[Message], tools: Tools, llm: LLM) -> Reply
Reply: text, tool_calls: tuple[ToolCall, ...], attachments: tuple[Attachment, ...]
```

One model turn with the seven tools declared. The model picks a tool, the orchestrator runs
it, the model writes a reply that quotes the returned value. Attachments carry what the app
renders: a curve, five candidates with forecasts, an explanation card, a clip. No logic of
its own. If a branch appears here, it belongs in a tool.

### `api`

Thin by design. `/chat` plus one route per tool. `main.py` is the only place that reads
config and builds adapters. If a route grows logic, the logic belongs in the tool.

## Analysis scripts

`analysis/template_curves.py` and `analysis/gov_memes.py` produce the two opening charts.
They import from `tools` and `shared` and add nothing of their own beyond plotting. If a script needs a
computation the package lacks, add it to the package. This keeps the pitch charts and the app
reading the same numbers, which is the claim the judge is buying.

Match the sponsor's script register: argparse, a module docstring that records what was
learned (his firehose script does this well), typed signatures, one file per job.

## House style, applied to a weekend

Keep: strict typing, one-line doc comments on public functions, the module overview banner,
validate-first errors with the fix named in backticks, why-only comments, no debug prints.

Skip: module-end summary banners, overloads, anything that reads as ceremony. A stranger
reading a function should get its reason from names and one comment, not from a header.

Uncommitted notebooks are fine as scratch. Nothing in `shared/`, `tools/`, `chat/` or `api/`
ships from a notebook.

## What was learned building it

- The firehose first observes a tweet hours to days after creation (median about two days),
  so a "first thirty minutes" curve does not exist in the data. Learn replays the real
  trajectory in real hours and names the checkpoint it compares at.
- The firehose almost never shows an account with thousands of likes, so a known account's
  forecast is anchored to its own median with the model as the multiplier against a typical
  post by that account.
- The government file writes `'0'` for an original post's `in_reply_to_tweet_id`.
- Homebrew's ffmpeg has no text filter; captions are Pillow PNGs overlaid per time window.
- The TikTok dataset is gated on Hugging Face; sounds wait for a token.
- Three crypto templates in chart 1 are near-duplicates of one another. Merging mutations
  (MinHash or an embedding threshold before aggregation) is the next Listen improvement.

## The local MVP configuration

Part 1 of the plan is the whole loop on one laptop with every seam on its local adapter.
`.env.example` ships with these defaults, and the tests use the same ones:

```
MEROK_DATA_SOURCE=local        # local DuckDB file; "fixture" in tests
MEROK_LLM_BASE_URL=https://api.featherless.ai/v1   # any OpenAI-compatible endpoint
MEROK_LLM_API_KEY=                                  # unset: the offline fake, drafts are placeholders
MEROK_LLM_MODEL=
MEROK_VOICE=silent
MEROK_VISUALS=loops
MEROK_PUBLISHER=dry_run
MEROK_POLLER=replay
EXPO_PUBLIC_API_URL=http://localhost:8000
```

Part 2 flips one string at a time: `elevenlabs`, a hosted model name, `veo`, `x`, a droplet
URL. No tool's code changes. The MVP is tagged `mvp` when the ten-minute script runs with
wifi off.

## Build order

1. `shared/` with the fixtures and `tests/test_imports.py`, plus the root and tool
   `CLAUDE.md` files. Everything else blocks on this.
2. `tools/listen` and `analysis/template_curves.py`. This is the opening chart.
3. `tools/score`, `tools/draft` and `tools/explain` in parallel; all consume `shared.embed`.
4. `analysis/gov_memes.py`. Needs listen and a per-author baseline from `shared.data`.
   In parallel, `tools/render` with the silent voice first, ElevenLabs second, and
   `listen.sounds` from one TikTok shard.
5. `tools/ship`, `tools/learn`, `chat/`, `api/`, then the Expo shell with the clip card and
   share button, then the droplet so the phone can reach it.
