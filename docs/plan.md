# merok-bot: problem, development plan, sponsor prizes

Written September 18, 2026. Companion to prior-art.md and architecture.md.

## The problem

People who post for a living cannot see why some posts spread and most do not. The
platform's answer is a black box: an algorithm, a feed, a number after the fact. The tools on
the market (Tweet Hunter, Typefully, Hypefury) draft and predict but show no reasoning and no
data. The person posting learns nothing.

Memetics says the unit that spreads is not the post. It is the template: a text pattern that
many authors fill in. A post rides a template that is already replicating, or it does not.
That is measurable. In one hour of the X firehose, 28 distinct texts were posted verbatim by
five or more accounts, one by 128.

merok-bot is a chat assistant that helps someone post things that spread and shows its work. It
watches the firehose for templates that are replicating now, drafts in the user's voice from
their own past posts, predicts each draft against the user's baseline with the reasons, posts,
and shows the real first thirty minutes next to the prediction.

The finding is the deliverable. The app is how the judge sees it.

## Two findings the app demonstrates

1. Templates spread, not posts. Distinct authors per hour on one template is a meme's
   lifecycle, measured from the sponsor's firehose.
2. Government learned to meme. Official accounts adopting firehose templates and slang, by
   month, against each account's own baseline in the same month.

## Data handling

The firehose is 55.7 GB across 396 hour files. Nobody downloads or compresses it.

- DuckDB reads parquet over HTTPS with range requests. A query touching one hour pulls one
  file, about 140 MB, and prunes columns and row groups. Cold read is one to two minutes,
  cached read is seconds.
- The working set is one day of English originals, about 3.4 GB, materialised once into a
  local parquet cache and committed nowhere. A one-hour fixture, a few megabytes, lives in
  the repo for tests and for the demo if the venue wifi fails.
- The government file is 263 MB and reads whole.
- The app never touches the raw firehose. It reads tables the analysis scripts produce:
  templates with curves, author baselines, model weights.

### Which of the four sponsor sets we use

Three. The judge scores the phenomenon, so each one has to do a job in the pitch. Say which
three, why, and what parkour would add.

| Sponsor dataset | In the plan | Why |
|---|---|---|
| Firehose, last month of X | yes, primary | The only set that shows replication across the public, with engagement curves. Both findings and the traction model come from it. |
| Government tweets | yes | Finding 2, per-account baselines, the demo user's voice. |
| Parkour Instagram niche | no, stretch | Different platform, one subculture, daily snapshots. Could make Learn a cross-platform claim: early slope predicts final engagement there too. Two hours, after Score is done. |
| TikTok, 4.5B records | yes, one shard | A sound is a template: creators per hour on one music id is the same replication curve. Render names the trending sound the clip should ride. Music id columns only, over HTTPS from Hugging Face. |

### Why the firehose

"Firehose" is the sponsor's name for dataset 1, borrowed from Twitter's old term for the
full real-time stream: every tweet as it happens, all languages. We use it because it is the
only dataset that can show replication across the public. The government set is about 800
accounts, so a template cannot be seen spreading through it. The firehose also carries the
repeat snapshots that give engagement trajectories, which Score and Learn need, and it covers
the three weeks after the government set ends on August 24. The government set is the
calibration story: known followers, known party, known baseline.

## Status, Saturday September 19, early morning

Part 1 is built and runs on one laptop: 36 tests green on fixtures, the seven tools behind
the chat, the API, the Expo desktop app, both charts. Commits are on main.

Chart 2 as measured is a null result: the share of official congressional posts using the
slang and meme-format lexicon is flat at about one percent since 2019, and the lift of those
posts over the same account's other posts hovers around one. The dataset is Congress plus
executive principals; it excludes the White House and agency accounts (@WhiteHouse, DHS, ICE)
that the sponsor's slide and the Pew piece are about. Pitch options: present the contrast
(Congress did not learn to meme; the executive did, and the data we have shows the first
half), or pull those institutional accounts from the firehose by author id for the last
month. Ricky's call.

## Two parts

Decided September 19: Part 1 is a working MVP on one laptop, every seam on its local
adapter, no accounts and no keys beyond the Featherless model key. Part 2 swaps in real
adapters one config string at a time, in this order: ElevenLabs voice, Veo for the finale
shot, live X posting, the phone through a droplet or tunnel, the domain. The Friday-night keys list below
belongs to Part 2 except the month pull and the press office pick.

## Development plan

Repo created Friday 22:18. Devpost due Sunday 9 AM. About 34 working hours across the team.

| Phase | Hours | Done when |
|---|---|---|
| 0. Scaffold | Fri night | `uv` project, DuckDB reads one firehose hour over HTTPS, fixtures committed, the import-rule test, root and tool `CLAUDE.md` files, README with the problem statement |
| 1. Listen | Sat morning | Templates mined from one day, distinct-author curves plotted, spam split by author repetition, the 28-at-five-plus number reproduced. Opening chart exists. |
| 2. Score, Draft and Explain, in parallel | Sat midday | Traction model beats "predict the author's median" on held-out September tweets. Drafts in a press office's voice pass the embedding classifier at near chance. Explanations of the day's top twenty templates make sense to a teammate who has not seen them. |
| 3. Government chart | Sat afternoon | Per-account, per-month template share against the same account's non-template posts. Second chart exists. |
| 4. Ship and Learn | Sat evening | Post from a team account through the X API, thirty-minute curve on screen next to the forecast. Dry-run adapter for rehearsal. |
| 4b. Render | Sat afternoon to evening | Owned by the Draft owner. A scored draft becomes a 9:16 clip: ElevenLabs voice with word timestamps, captions and a background composed by ffmpeg, the trending sound named from one TikTok shard. Done when it renders in under a minute and the phone shares it into TikTok. |
| 5. App shell | Sat night | Expo web build wraps the chat. Same code on the phone through Expo Go or the iOS Simulator, with a clip card and a share button. Backend on a DigitalOcean droplet so the phone can reach it. |
| 6. Pitch and Devpost | Sun morning | Two charts, then the chat, then the clip on the phone as the finale. Devpost page uses the judge's own vocabulary. Submitted before 9 AM. |

Cut order if time runs out, first to last: live X posting (fall back to dry run), Explain
(fall back to the Listen card), the clip's voice (fall back to captions only), the government
chart (fall back to one account by hand). The template chart, the drafting loop and the clip
on the phone are never cut.

## The clip

Decided September 18, late: the TikTok-ready clip is the demo's finale. Render turns a scored
draft into a spoken, captioned 9:16 clip and names the trending sound; the phone plays it and
the share sheet opens TikTok. The background is a seam: shipped loops by default, one
generated still with motion for cents, or Veo 3.1 Fast through the Gemini API on request,
pre-rendered for the table because it takes minutes. Decided September 19: video generation
runs on free credits only. The MLH Google Program Benefits key ($10 a month on the Gemini
API) is the budget and the cap; no card-billed spend. The $300 Cloud trial is there if a
teammate wants headroom, not required. Posting stays a manual upload because TikTok and Instagram lock
unaudited apps out of their posting APIs. The two charts and the text loop still come first
in the pitch; the clip closes it.

## Naming

The project is merok-bot, in the pitch and on Devpost. There is no wrapper package: the
Python code is four top-level packages, `shared`, `tools`, `chat` and `api`, importing as
themselves.

## Who owns what

| Slot | Owns | Ships |
|---|---|---|
| A · Data and Listen | `shared/data`, fixtures, the month pull, `tools/listen` including sounds | Chart 1, the template feed, the sound of the day |
| B · Score and Learn | `tools/score`, baselines, `tools/learn`, `analysis/gov_memes.py` | Chart 2, the forecast with drivers, the thirty-minute curve |
| C · Draft, Explain, Render | `tools/draft`, `tools/explain`, `tools/render`, `shared/llm` | Five drafts that pass the Turing test, the explanation card, the clip |
| D · Chat, app, pitch | `chat/`, `api/`, `app/`, `tools/ship`, deploy, domain, Devpost, slides | The demo path end to end, laptop and phone |

With three people: Ship stays on the dry-run adapter, slot D's app work starts Saturday
afternoon, and whoever finishes first takes Render.

## Before anyone sleeps Friday night

- Keys: Gemini API through the MLH Google Program Benefits ($10, the whole video budget),
  ElevenLabs (free tier or the MLH offer), X developer account on a fresh team handle with
  $10 loaded, DigitalOcean through MLH.
- Repo: commit the docs and CLAUDE.md to main; phase 0 scaffold.
- Data: start the month pull in the background on one laptop.
- Pick the demo press office from the government set.

## Budget

| Item | Cost | Paid by |
|---|---|---|
| X posts | $0.015 each, $0.20 with a link | $10 on the team account |
| Veo shots | about $1.20 each, capped at $10 | MLH Gemini credits |
| Drafting and explaining | cents | the same Gemini key, or an Anthropic key if one exists |
| Voice | free tier | ElevenLabs |
| Droplet | credits | MLH DigitalOcean |
| Domain | about $10 | optional |

## Open decisions for Ricky

Part 1 only. Part 2's accounts wait until the MVP is tagged.

1. Team size and slots. Default: four.
2. The MVP model. Decided: Ricky's Featherless endpoint, an OpenAI-compatible base URL, key
   and model name in `.env`; without them the offline fake keeps the loop running with
   placeholder drafts.
3. The demo press office. Default: slot A picks the account with the most tweets and a
   consistent house style.

## Sponsor prizes worth wrapping in

Tracks are one per team and Memetics is ours, so SpacetimeDB, Bloomberg, Forge, OPEF and
Data Visualization are out. Best Overall is open to everyone. The sponsor prizes below are
not track-limited. Judged on whether the tool does real work in merok-bot or is bolted on.

| Prize | Fit | Cost | Take it? |
|---|---|---|---|
| DigitalOcean, deploy on their cloud | The FastAPI backend needs a host for the phone demo anyway | One droplet, an hour | Yes |
| GoDaddy Registry, best domain | Register the demo domain there | Minutes | Yes |
| Auctor AI, "From Conversation to Action" | Chat in, post out is the whole app | Zero, it is the pitch | Yes, submit |
| Gemini API, best use | Veo 3.1 Fast through the Gemini API is the generative adapter in Render's visuals seam, opt-in per clip and pre-rendered for the finale. Real work | Inside the Render phase | Yes |
| ElevenLabs, two prizes, one worth six months of Scale | The voice in Render, with word timestamps driving the captions. Real work, not bolted on | Inside the Render phase | Yes |
| Tiger Data | Engagement curves are time series and Learn stores thirty minutes of polls. Real fit, but DuckDB already does it in-process and this adds a server | Two hours plus ops | No, unless Learn needs persistence across restarts |
| Backboard, AI app state | Persistent user context for the chat. Unknown product, would need a workshop visit | Unknown | No |
| Snowflake API, RAG chatbots | Retrieval over past posts could run in Cortex. Heavy for what DuckDB plus nomic-embed already do | A day | No |
| Solana | No fit | | No |
| SpaceXAI, "Make it Legendary" | Needs a space theme | | Back pocket |

Rule: a sponsor tool goes in only if the LLM seam, the deploy target, or the domain would
have existed anyway. Nothing gets added to the architecture for a prize.
