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
```

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

Two OpenRouter quirks the client already handles: video download URLs are API
endpoints and need the `Authorization` header, and the job record is eventually
consistent — status can read `completed` before the URLs land, and can briefly
report `pending` again afterwards.

## Strategy

Encoded in `reelkit/pillars.py`. Per 10 posts: 4 AI, 3 stocks, 2 jobs,
1 resume. Reach pillars (AI, stocks) run faceless and cost nothing to make;
trust pillars (jobs, resume) use a real face and cost ~$1.89 a clip. So a
typical week is ~$5.67 of generation, not $13.

Stock content is news and education only — never buy/sell calls, never price
targets. The disclaimer is in the template so it can't be forgotten.
