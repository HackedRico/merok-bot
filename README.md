<p align="center">
  <img src="docs/img/app-draft.png" alt="merok-bot drafting five posts in a senator's voice, each with a forecast" width="820">
</p>

<h1 align="center">merok-bot</h1>

<p align="center">
  A chat assistant that helps you post things that spread, and shows its work.<br>
  Built for HopHacks 2026, Best Memetics Hack, on Calcifer Computing's datasets.
</p>

<p align="center">
  <a href="https://github.com/HackedRico/merok-bot/actions/workflows/ci.yml"><img src="https://github.com/HackedRico/merok-bot/actions/workflows/ci.yml/badge.svg" alt="ci"></a>
  <img src="https://img.shields.io/badge/python-3.12-3776AB" alt="python 3.12">
  <img src="https://img.shields.io/badge/expo-57-000020" alt="expo 57">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
</p>

---

## The idea

The unit that spreads on X is not the post. It is the **template**: a text pattern that many
accounts fill in. In one hour of the firehose, thirty distinct texts were posted verbatim by
five or more accounts; the top one by 686 accounts over a day. That is measurable, and
merok-bot is the instrument that measures it and then puts it to work.

You talk to it. It listens to the firehose for templates that are replicating right now,
tells them apart from paid replication by looking at the accounts, drafts five posts in your
own voice from your own past posts, predicts how each will do against your median with the
reasons, turns one into a captioned clip, posts it, and shows you the curve.

<p align="center">
  <img src="analysis/out/template_curves.png" alt="Distinct authors per hour for the top templates in one day of the firehose" width="820">
</p>

Two organic memes ride all day: people asking Grok for a report card, and X's join-date
share card. The dashed lines are crypto copy, hundreds of accounts in a two-hour burst, and
the verdict that separates them is part of the finding, never a filter.

## Seven things you can say to it

| Say | Tool | You get |
|---|---|---|
| What are people posting this hour? | listen | Templates replicating now, each with its curve and an organic or paid verdict with reasons |
| What is this: "..." | explain | The template a post rides, when it was first seen, who started it, and a gloss written only from those facts |
| Help me announce Thursday's town hall. | draft | Five posts in the account's voice, retrieved from its own history, two riding a live template |
| score draft 2 | score | Likes in a day against the account's median, with the drivers that moved the number |
| turn draft 3 into a clip | render | A captioned 9:16 clip, ready for TikTok, in about five seconds |
| post the third one | ship | Posted to X inside a spend cap, or copied for platforms that lock apps out |
| How did it do? | learn | The real curve against the forecast |

Every button in the app sends one of these sentences, so the app and a typed message do the
same thing.

<p align="center">
  <img src="docs/img/app-listen.png" alt="The listen card: templates spreading now with curves and verdicts" width="400">
  &nbsp;
  <img src="docs/img/app-explain.png" alt="The explain card: what a pasted post rides" width="400" align="top">
</p>

## Run it

You need `uv`, Node 22 and `ffmpeg`.

```bash
git clone https://github.com/HackedRico/merok-bot && cd merok-bot
uv sync
cp .env.example .env
```

Every setting has a local default. The app runs with no keys at all, on placeholder drafts;
add a model to get real ones:

```bash
# .env, any OpenAI-compatible endpoint
MEROK_LLM_BASE_URL=https://api.featherless.ai/v1
MEROK_LLM_API_KEY=...
MEROK_LLM_MODEL=unsloth/Meta-Llama-3.1-8B-Instruct
```

Pull one day of the firehose, about four minutes, then start the API and the app:

```bash
uv run python scripts/pull_month.py --from 290 --to 313
uv run uvicorn api.main:create_app_from_env --factory --port 8000
```

```bash
cd app && npm install && npx expo start --web
```

Open http://localhost:8081. On a phone, Expo Go runs the same code; point
`EXPO_PUBLIC_API_URL` at your laptop.

## What is real and what is a stand-in

Every outside dependency sits behind a seam with a local adapter, so the whole loop runs on
one laptop with wifi off. `/health` says which adapter each seam is on.

| Seam | Default | Flip |
|---|---|---|
| Data | the sponsor's public bucket, read one hour file at a time over HTTPS, cached locally | `MEROK_DATA_SOURCE=fixture` for the test slice |
| Model | any OpenAI-compatible endpoint | unset: an offline fake with visibly marked drafts |
| Embeddings | character n-gram hashing, no download | `MEROK_EMBEDDER=nomic` after `uv sync --extra nomic` |
| Voice | silent, captions still word-timed | `MEROK_VOICE=elevenlabs` with `ELEVENLABS_API_KEY` |
| Video | a drifting gradient from ffmpeg | generated stills and Veo, behind the same protocol, are next |
| Publisher | X with OAuth 1.0a and a `$10` cap | falls back to the clipboard until the four `X_*` credentials are set |
| Learn | one like-count read per ask on X | falls back to replaying a real firehose trajectory |

## How it is built

Four Python packages at the repo root, no wrapper, and one rule that keeps four people out
of each other's way: **a tool imports `shared` and nothing else in the repo.** A test fails
the build if it does.

```
shared/    types, text, embeddings, config, the data seam, the model seam
tools/     listen · explain · draft · score · render · ship · learn, one directory per verb
chat/      one message routes to one tool; rules first, the model second
api/       FastAPI, the only place that reads config
app/       Expo, one codebase for the browser and the phone
analysis/  the two charts, computed by the same functions the app calls
```

Each tool carries a ten-line `CLAUDE.md` with its interface, invariants and test, and
[docs/architecture.md](docs/architecture.md) holds every interface and the reasons behind
the layout, including what was learned building it. Tests run on fixtures cut from the bucket
and never touch the network:

```bash
uv run pytest
uv run python scripts/pressure.py     # against a running API: many conversations at once, plus hostile inputs
```

## The methods, and whose they are

- **Template curves** are MemeTracker (Leskovec, Backstrom and Kleinberg, 2009) run on X in
  2026, with the organic and paid split that Shafin and Ahmed's September 2026 paper on
  duplicate campaigns argues for.
- **Drafting** is the Digital Twin of Congress method (Helm, Duderstadt et al., 2026): a
  persona prompt from retrieved exemplars, judged by a statistical Turing test, a
  cross-validated classifier over embeddings where 0.5 means indistinguishable.
- **Scoring** is gradient boosting over log-likes with counterfactual drivers; for an account
  with history the model supplies the multiplier and the level comes from the account's own
  median, because the firehose almost never shows accounts with thousands of likes.
- **The government chart** measures format adoption per account per month against the same
  account's other posts, because engagement rose for nearly every official account after
  January 2025 for reasons unrelated to format. As measured, official congressional accounts
  did not learn to meme; the executive branch did, and it is not in the dataset. The chart
  and the finding are in [docs/plan.md](docs/plan.md).

## Data

Three of the sponsor's four datasets: the X firehose (395 million rows, read one hour file
at a time and never downloaded whole), the government tweet file (2.16 million tweets by
official accounts, with engagement), and one TikTok shard for sounds once a Hugging Face
token is at hand. The gotchas the schemas do not confess are in [CLAUDE.md](CLAUDE.md).

## Licence

MIT. Data belongs to its sources; see Calcifer Computing's dataset page.
