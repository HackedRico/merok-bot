# merok-bot

A chat assistant that helps someone post things that spread, and shows its work. HopHacks
2026, Best Memetics Hack, sponsored by Calcifer Computing.

The claim: the unit that spreads on X is not the post, it is the template, a text pattern
many accounts fill in. That is measurable from the sponsor's firehose. In one hour, thirty
distinct texts were posted verbatim by five or more accounts; the top one by 686 accounts over
a day. Organic replication and paid replication look the same until you look at the accounts,
so the split is part of the finding. The second claim, official accounts adopting internet
formats, is measured per account per month against the account's own other posts.

The app is the instrument. Seven things you can say to it: what is spreading, explain a post,
draft five in my voice, score one, turn one into a clip, post it, how did it do.

## Run it

```bash
uv sync
cp .env.example .env            # every value has a local default; add a model key when you have one
uv run python scripts/pull_month.py --from 290 --to 313   # about one day of the firehose, four minutes
uv run uvicorn api.main:create_app_from_env --factory --port 8000
cd app && npm install && npx expo start --web            # the desktop app at http://localhost:8081
```

Tests run on fixtures cut from the bucket and never touch the network:

```bash
uv run pytest
```

The two charts:

```bash
uv run python analysis/template_curves.py
uv run python scripts/pull_gov.py && uv run python analysis/gov_memes.py
```

## Layout

Four Python packages at the repo root, no wrapper. `shared/` is everything more than one tool
needs. `tools/<verb>/` is one directory per chat verb. `chat/` routes one message to one tool.
`api/` serves it. `app/` is the Expo chat. `docs/architecture.md` has every interface and the
reasons; `CLAUDE.md` has the rules and the data gotchas.

## Data

Three of the sponsor's four datasets: the X firehose (one hour file at a time over HTTPS,
never downloaded whole), the government tweet file, and one TikTok shard for sounds once a
Hugging Face token is at hand. Every seam has a local adapter, so the whole loop runs on one
laptop with wifi off.
