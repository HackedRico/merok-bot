# Handoff

For the next agent or person picking this up cold. State as of Sunday September 20, 2026,
2 PM Eastern. The hackathon deadline has passed; the owner is done with the project and wants
the public repo to be good enough for real. Read this, then README.md, then CLAUDE.md, then
docs/architecture.md, in that order.

## What this is, in three lines

A chat assistant that helps someone post things that spread and shows its work, built for
the Best Memetics Hack track at HopHacks 2026 on Calcifer Computing's X firehose and
government tweet datasets. Seven tools behind one chat: listen, explain, draft, score, render,
ship, learn. The finding it demonstrates: on X the unit that spreads is the template, not the
post.

## What works today

- `uv run pytest`: 44 tests on fixtures cut from the bucket, no network, green in CI on
  Ubuntu (`.github/workflows/ci.yml`, both jobs).
- The API (`uv run uvicorn api.main:create_app_from_env --factory --port 8000`) and the Expo
  web app (`cd app && npx expo start --web`) run the whole loop on one laptop. Verified by
  hand in a browser and by `scripts/pressure.py` (eight conversations at once plus fifteen
  hostile inputs, zero problems).
- Drafting and explaining use a real model through an OpenAI-compatible endpoint. The owner's
  `.env` has a Featherless key and `unsloth/Meta-Llama-3.1-8B-Instruct`; `.env` is gitignored
  and was never committed.
- Both charts render from real data: `analysis/template_curves.py` (one day of the firehose,
  cached under `.cache/`) and `analysis/gov_memes.py` (the government file, cached). The PNGs
  are committed under `analysis/out/`.

## What is a stand-in, by design

Each is one config string behind a seam that already has a real adapter or a documented slot.

| Seam | Now | Real adapter |
|---|---|---|
| Voice | `SilentVoice`, captions still word-timed | `tools/render/elevenlabs.py`, written, never run against the API |
| Background video | ffmpeg gradient | still image and Veo adapters not written; protocol in `tools/render/visuals.py` |
| Publisher | clipboard, because `X_*` credentials are unset | `tools/ship/x_api.py`, OAuth 1.0a, spend cap and ledger, tested against a fake transport only |
| Learn | replayed firehose trajectory | `tools/learn/x_poll.py`, one read per ask, tested against a fake transport only |
| TikTok sounds | synthetic table in tests | the dataset is gated on Hugging Face; `scripts/pull_sounds.py` needs `HF_TOKEN` and its column names are a guess until a shard is inspected |
| Phone | not exercised | same Expo code; needs `EXPO_PUBLIC_API_URL` pointing at a reachable API |

## Known rough edges

1. The firehose first observes a tweet hours to days after creation, so "the first thirty
   minutes" mostly does not exist in the data. Learn names the checkpoint it compares at.
   A live X poll is the only way to a real thirty-minute curve.
2. Chart 2 is a null result: official congressional accounts use internet formats about one
   percent of the time, flat since 2019. The meme turn is the White House and agencies, which
   the dataset excludes. The README says so plainly; do not soften it.
3. The forecast for a known account is anchored to its own median with the model supplying
   the multiplier (see `tools/score/model.py`). The baseline is the account's all-time median;
   a recency-weighted baseline would be more honest and is a small change in
   `tools/score/baseline.py`.
4. Near-duplicate templates fold at 0.75 cosine over character n-gram hashes
   (`tools/listen/cluster.py`). Merged hourly curves are summed, which can double-count an
   account that posted two variants in one hour.
5. The Expo app is a single screen with one card per attachment kind. On native the clip card
   opens a link instead of playing inline; `expo-video` would fix that.
6. `docs/plan.md` and `docs/pitch.md` are hackathon-internal planning documents. They are
   honest and dated but read as notes; they can stay or be trimmed.

## Cleanup for a public repo, in order

Each step has a done-when. Stop when the list is done; do not add features.

1. **Read the whole repo once as a stranger.** Done when every file you would not want a
   stranger to see is either explained in a doc comment or removed. Candidates: nothing known,
   but check `app/assets/` (Expo template icons, fine to keep) and `.claude/launch.json`
   (harmless; used by the Claude desktop app to start the two servers).
2. **Run the suite and CI.** `uv run pytest` green locally; the CI badge green on main. Done
   when both are true after your last commit.
3. **Verify the README from a clean clone.** Follow "See it in five minutes" on a fresh
   checkout, with and without a model key. Done when every command in it runs as written.
4. **Confirm nothing secret is in history.** `git log --all --diff-filter=A --name-only
   --format= | grep -E '\.env$'` prints nothing; grep the tree for `api_key` values. Done when
   both are clean (they were, as of this handoff).
5. **Set the GitHub repo description and topics** to match the README's first line, and add
   the plan page link if the owner wants it public. Done when the repo page reads well.
6. **Leave the rest alone.** Part 2 adapters, the phone, the TikTok shard and chart 2's
   executive-branch follow-up are roadmap items in the README, not work for this pass.

## Conventions that must survive

- A tool imports `shared` and nothing else in the repo; `tests/test_imports.py` enforces it.
- Every public function has a one-line doc comment; comments say why, never what.
- Frozen values in `shared/types.py` cross tool lines; side effects only at seams.
- No em-dashes anywhere, straight quotes, sentence-case headings. Conventional Commits,
  no AI attribution lines.
- Commit on main only when asked; never push main from an agent session. The owner pushes.

## Where things are

- Plan page (private artifact, the owner's): https://claude.ai/artifact/Xe6BNxoN6JncFTjoo3o6v3
- Sponsor datasets and README: https://calcifer-hot.s3.us-east-2.amazonaws.com/hopkins-hackathon-2026/README.md
- Local data cache: `.cache/` (gitignored): one day of English originals, the government
  file, rendered clips, the X spend ledger if posting ever runs.
