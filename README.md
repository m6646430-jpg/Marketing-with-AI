# Marketing-with-AI

Tooling for an Instagram / YouTube reels page covering AI updates, the stock
market, and jobs — funnelling to [DriftAI](https://driftai.co).

These are tools you run, not a pipeline that runs itself. Nothing posts
automatically. Nothing spends money without printing the cost first.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then paste your OpenRouter key into .env
```

`.env` is gitignored. **This repo is public — never commit a key.**

## Tools

```bash
# what's available and what it costs (live pricing, free)
python3 tools/list_models.py

# raw notes -> reel script (fractions of a cent)
python3 tools/write_script.py --pillar ai --duration 30 --content "..." --save

# photo -> 9:16 head-and-shoulders first frame (free)
python3 tools/crop_photo.py --src selfie.jpg --out output/frames/me.jpg --open

# first frame + line -> talking-head clip (COSTS MONEY — dry-run first)
python3 tools/make_clip.py --photo output/frames/me.jpg --say "..." --dry-run
python3 tools/make_clip.py --photo output/frames/me.jpg --say "..." --open

# selfie -> on-brand first frame, same face, styled background (~$0.14, do once)
python3 tools/style_photo.py --src selfie.jpg --pillar brand --dry-run
python3 tools/style_photo.py --src selfie.jpg --pillar brand --open

# transcribe locally with word timings (free, offline, zero tokens)
python3 tools/transcribe.py --src clip.mp4 --save

# burn word-by-word captions (free, local)
python3 tools/add_captions.py --src clip.mp4 --open
```

Captions are not optional. Most reels are watched muted — they're the
difference between watched and scrolled.

**Visual consistency.** The first frame *is* the look of a reel — its
background, framing and outfit come from that image. Random selfies make every
post look like a different account. So make one canonical brand frame with
`style_photo.py` (same face, clean styled background) and reuse it as the first
frame for every face reel. It edits the wrapper only — the face is locked in
every prompt, because a reel showing a face that isn't yours is the same
authenticity problem as an avatar. At ~$0.14 an edit it's a once-off, not a
per-post step.

## One model per task

Defined in `reelkit/models.py`, with the reasoning next to each choice.

| Task | Model | Billing | Tokens? |
|---|---|---|---|
| Talking head | `kwaivgi/kling-v3.0-std` | $0.126/s | no |
| Talking head (hero) | `kwaivgi/kling-v3.0-pro` | $0.168/s | no |
| Silent b-roll | `alibaba/happyhorse-1.1` | $0.0988/s | no |
| Transcribe / captions | `faster-whisper` **local** | free | **zero** |
| Voiceover | ElevenLabs | per char | no |
| Script (AI, stocks) | Nemotron Super | free | yes |
| Script (jobs, resume) | Claude Sonnet 5 | $2/Mtok | yes |
| Highlight scoring | Nemotron Super | free | yes |

## On reducing tokens

Measured, not assumed:

- **Video is billed per second, not per token.** No prompt change makes a clip
  cheaper or worse. The two are unrelated, so there is no quality/token
  tradeoff to manage on video at all.
- **A script call is ~400 tokens.** Ten a week is ~4k tokens: $0.00 free,
  $0.008 on Sonnet. Video is ~$5.67/week — about 700× more. Trimming script
  prompts optimises a rounding error.
- **The biggest saving is architectural.** Transcribing locally with
  faster-whisper takes a task from thousands of tokens to zero *and* produces
  better output (word-level timestamps) than any LLM would. Prefer local
  whenever a real local option exists.
- **Where tokens genuinely bite** is scoring a 20-minute transcript (~4k tokens
  a pass). `reelkit/tokens.py` handles that: `compact()` cuts ~31% versus JSON
  by not repeating keys on every row, and `prefilter()` drops ~70% of segments
  (though only ~20% of tokens — filler is short; its real value is signal, not
  savings).

Net: the lever that moves your bill is seconds of video, and cutting those
costs quality. Everything else is already free.

## Model notes

Established by testing on 2026-07-15, at a total cost of $2.29:

| Model | Real face | Max length | Audio | 15s cost |
|---|---|---|---|---|
| `google/veo-3.1-lite` | **filtered** | 8s | yes | — |
| `kwaivgi/kling-v3.0-std` | works | 15s | yes | $1.89 |
| `alibaba/happyhorse-1.1` | untested | 15s | **none** | $1.48 |

Google's `personGeneration` policy refuses clear photos of identifiable real
people. A side profile passed; a front-facing headshot was filtered. Kling has
no such restriction. Default is Kling for that reason, not quality.

**Kling recites a script verbatim** if you put the spoken line in quotes inside
the scene description — that's what `to_video_prompt()` does. Confirmed by
transcribing a generated clip back with whisper and getting the input script
returned word for word. Passing a bare script as the prompt does *not* work:
the model generates a scene *about* the text instead of someone saying it.

Two OpenRouter quirks the client already handles: video download URLs are API
endpoints and need the `Authorization` header, and the job record is eventually
consistent — status can read `completed` before the URLs land, and can briefly
report `pending` again afterwards.

## Strategy

Encoded in `reelkit/pillars.py`. Per 10 posts: 4 AI, 3 stocks, 2 jobs,
1 resume.

| | Pillars | Face | Script model | Cost per clip |
|---|---|---|---|---|
| Reach | AI, stocks | no | free | $0 |
| Trust | jobs, resume | yes | Sonnet | ~$1.89 |

Reach pillars are 7 of 10 posts and cost nothing to make — volume matters more
than polish. Trust pillars carry the face and the DriftAI funnel, so they get a
paid script model: the free one is accurate but flat, and a flat hook loses the
first two seconds. That's ~3 paid scripts a week, well under a cent.

Each pillar names its own model, so `--pillar resume` just does the right
thing. `--model` overrides when you want it.

A typical week: ~$5.67 of video generation, ~$0.01 of scripts.

Stock content is news and education only — never buy/sell calls, never price
targets. The disclaimer is in the template so it can't be forgotten.
