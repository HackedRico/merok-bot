<h1 align="center">merok-bot</h1>

<p align="center">
  <strong>A chat assistant that helps you post things that spread, and shows its work.</strong>
</p>

<p align="center">
  Developed for the Best Memetics Hack track at <a href="https://hophacks-fall-2026.devpost.com/">HopHacks 2026</a>,
  Johns Hopkins University, September 18 to 20, on datasets from
  <a href="https://www.calcifercomputing.com/hophacks">Calcifer Computing</a>.
</p>

<p align="center">
  <a href="https://github.com/HackedRico/merok-bot/actions/workflows/ci.yml"><img src="https://github.com/HackedRico/merok-bot/actions/workflows/ci.yml/badge.svg" alt="ci"></a>
  <img src="https://img.shields.io/badge/python-3.12-3776AB" alt="python 3.12">
  <img src="https://img.shields.io/badge/expo-57-000020" alt="expo 57">
  <img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0">
</p>

<p align="center">
  <img src="docs/img/app-draft.png" alt="Five drafts in a senator's voice, each with a forecast against the account's own median" width="820"><br>
  <sub>"Help me announce Thursday's town hall." Five drafts in the account's voice, two riding a live template, each scored against the account's own median with the reason.</sub>
</p>

## Why

On X, the thing that spreads is not the post. It is the **template**: a text pattern many
accounts fill in. In one hour of the firehose, thirty distinct texts were posted word for word
by five or more accounts. Over a day the largest reached 686. Some of that replication is
people; some of it is paid, and the accounts tell them apart.

<p align="center">
  <img src="analysis/out/template_curves.png" alt="Distinct accounts per hour for the top templates in one day of the firehose" width="820"><br>
  <sub>Distinct accounts per hour, one day of the firehose. Solid lines are organic memes; dashed lines are crypto copy that bursts and dies.</sub>
</p>

merok-bot turns that observation into a tool: find what is spreading now, write in your own
voice on top of it, know how it will do before you post, and see what happened after.

## What you can ask

Seven verbs, one chat. Every button in the app sends one of these sentences.

| Say | Tool | You get |
|---|---|---|
| What are people posting this hour? | listen | Templates spreading now, each with its curve and an organic-or-paid verdict with reasons |
| What is this: "..." | explain | The template a post rides, when it was first seen, who started it, and a gloss written only from those facts |
| Help me announce Thursday's town hall. | draft | Five posts in the account's voice, from its own history, two riding a live template |
| score draft 2 | score | Likes in a day against the account's median, with the drivers that moved the number |
| turn draft 3 into a clip | render | A captioned 9:16 clip for TikTok, in about five seconds |
| post the third one | ship | Posted to X inside a spend cap, or copied for platforms that lock apps out |
| How did it do? | learn | The real curve against the forecast |

<details>
<summary>Screenshots of listen and explain</summary>
<p align="center">
  <img src="docs/img/app-listen.png" alt="The listen card" width="400">
  &nbsp;
  <img src="docs/img/app-explain.png" alt="The explain card" width="400" align="top">
</p>
</details>

## Quickstart

Needs [uv](https://docs.astral.sh/uv/), Node 22 and [ffmpeg](https://ffmpeg.org/).

```bash
git clone https://github.com/HackedRico/merok-bot && cd merok-bot
uv sync && cp .env.example .env
uv run python scripts/pull_month.py --from 290 --to 313    # one day of the firehose, about four minutes
uv run uvicorn api.main:create_app_from_env --factory --port 8000
```

In a second terminal:

```bash
cd app && npm install && npx expo start --web             # http://localhost:8081
```

The app runs with no keys, on placeholder drafts. For real ones, put any OpenAI-compatible
endpoint in `.env`:

```bash
MEROK_LLM_BASE_URL=https://api.featherless.ai/v1
MEROK_LLM_API_KEY=your-key
MEROK_LLM_MODEL=unsloth/Meta-Llama-3.1-8B-Instruct
```

## How it works

Each tool is one directory under `tools/`, with one test that says when it is done, and none
imports another. Everything that touches the outside world sits behind a seam with a local
adapter, so the whole loop runs on one laptop with wifi off. `/health` says which adapter
each seam is on.

| Tool | Method | Outside dependency | Local default |
|---|---|---|---|
| listen | Exact-match clustering on normalised text, near-duplicates folded, distinct accounts per hour, a spam verdict from account behaviour | the firehose, one hour file at a time over HTTPS | cached day, or the test fixture |
| explain | Match by normalised text, then by embedding; the model glosses from the facts it is handed | a model | offline fake |
| draft | The Digital Twin of Congress method: persona prompt from retrieved exemplars, judged by a statistical Turing test | a model | offline fake |
| score | Gradient boosting over log-likes; drivers by counterfactual swap; a known account is anchored to its own median | none | none |
| render | Script, voice, background, captions, one ffmpeg pass | a voice, a video model | silent voice, gradient background |
| ship | X through OAuth 1.0a, a spend ledger and a cap checked before any request | X credentials | clipboard |
| learn | One like-count read per ask | X credentials | a replayed firehose trajectory |

The methods are borrowed and credited. Template curves are
[MemeTracker](https://snap.stanford.edu/memetracker/) run on X in 2026, with the organic and
paid split argued for by [Shafin and Ahmed (2026)](https://arxiv.org/abs/2609.13671).
Drafting is the [Digital Twin of Congress](https://arxiv.org/abs/2505.00006) method.

## Results

**Templates spread, not posts.** The chart above, from a day of the firehose: two organic
memes ride all day, people asking Grok for a report card and X's join-date share card, while
crypto copy spikes for two hours and vanishes.

**Did government learn to meme?** Measured per account per month against the same account's
other posts, official congressional accounts did not: their use of internet formats has sat
near one percent since 2019. The accounts that did are the White House and the agencies,
which the dataset does not include. A null result, stated as one; the chart and the reasoning
are in [docs/plan.md](docs/plan.md).

## Repository

```
merok-bot/
├── shared/                everything more than one tool needs
│   ├── types.py           frozen values that cross tool lines
│   ├── text.py            one normaliser for the whole app
│   ├── embed.py           hashing by default, nomic-embed behind the same protocol
│   ├── slang.py           the lexicon the government chart counts
│   ├── config.py          environment to settings
│   ├── data/              the lake seam: bucket, local cache, fixture
│   └── llm/               the model seam: any OpenAI-compatible endpoint, or the offline fake
├── tools/                 one directory per verb, each with a CLAUDE.md and a test
│   ├── listen/            templates, curves, the spam verdict
│   ├── explain/           match a post to a template, gloss it from the facts
│   ├── draft/             retrieve exemplars, generate five, the Turing test
│   ├── score/             features, the model, the author baseline
│   ├── render/            script, voice, background, ffmpeg composition
│   ├── ship/              X with OAuth 1.0a and a cap, clipboard, dry run
│   └── learn/             live polling, replay, the comparison
├── chat/                  one message routes to one tool: rules first, the model second
├── api/                   FastAPI, the only place that reads config
├── app/                   Expo, one codebase for the browser and the phone
│   └── src/               api client, the chat screen, one card per attachment kind
├── analysis/              the two charts, computed by the same functions the app calls
├── scripts/               data pulls, fixtures, a pressure test
├── tests/                 fixtures cut from the bucket; nothing here touches the network
└── docs/                  architecture, plan, prior art, pitch
```

Four Python packages at the repo root and one rule: a tool imports `shared` and nothing else
in the repo, enforced by a test. [docs/architecture.md](docs/architecture.md) holds every
interface and the reasons behind the layout; [CLAUDE.md](CLAUDE.md) holds the rules and what
the data schemas do not confess; [HANDOFF.md](HANDOFF.md) is where to start if you are
picking the project up.

```bash
uv run pytest                        # 44 tests, no network
uv run python scripts/pressure.py    # against a running API: many conversations at once, plus hostile inputs
```

**Data.** Three of the sponsor's four datasets: the X firehose (395 million rows over a
month, never downloaded whole), the government tweet file (2.16 million posts by official
accounts, with engagement), and one TikTok shard for sounds once a Hugging Face token is at
hand. Data belongs to its sources.

**Next.** ElevenLabs voice on the clip, a generated hero shot through Veo, live posting once
the X credentials exist, and Expo Go on a phone with the clip's share sheet opening TikTok.
Each is a config flip behind a seam that already exists.

## Licence

Apache 2.0. See [LICENSE](LICENSE).
