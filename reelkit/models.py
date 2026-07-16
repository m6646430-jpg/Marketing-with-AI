"""One model per task, chosen deliberately.

Two things worth understanding before changing anything here.

1. Tokens and video quality are independent. Video is billed per second of
   output ($0.126/s on Kling), not per token. No amount of prompt trimming
   makes a clip cheaper, and no amount of prompt bloat makes it worse. So
   token work targets the LLM layer only -- it cannot touch the $1.89.

2. The cheapest tokens are the ones never sent. Transcription is the clearest
   case: faster-whisper runs locally for free, uses zero tokens, works
   offline, AND gives word-level timestamps that an LLM transcribing audio
   won't. Local wins on cost and quality at once. Prefer local whenever the
   task has a real local option.

Prices verified against the OpenRouter API on 2026-07-15. Do not trust them
after that -- `python3 tools/list_models.py` reads them live.
"""

# --- video -----------------------------------------------------------------
# Billed per second. Token optimisation is irrelevant here; duration is the
# only lever, and cutting duration costs quality. Leave these alone.

VIDEO_TALKING_HEAD = "kwaivgi/kling-v3.0-std"
# $0.126/s with audio. The only model proven to accept a real, identifiable
# face (Google's Veo filters them -- a side profile passed, a front-facing
# headshot did not) that also does 15s + audio + 9:16 in a single clip.

VIDEO_TALKING_HEAD_HQ = "kwaivgi/kling-v3.0-pro"
# $0.168/s. Same family, better fidelity. For the founder intro / pinned post,
# where one clip carries disproportionate weight.

VIDEO_BROLL = "alibaba/happyhorse-1.1"
# $0.0988/s, silent by design. Cheapest 15s vertical. For faceless pillars
# where the voiceover is added separately -- paying Kling's audio premium for
# audio you're going to discard is waste.


# --- audio in (transcription) ----------------------------------------------
# Local first. This is the single biggest token saving available: it takes a
# whole task from "thousands of tokens per video" to zero.

TRANSCRIBE_LOCAL = "faster-whisper:base"
# Free, offline, zero tokens, word-level timestamps. The right answer.
# Upgrade to :small or :medium if accent accuracy disappoints -- still free.

TRANSCRIBE_FALLBACK = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
# Free, accepts audio. Only if whisper won't install. No word-level timings,
# so captions degrade to segment-level -- acceptable, not good.

TRANSCRIBE_ACCURATE = "google/gemini-2.5-flash-lite"
# $0.0000003/audio token. Paid fallback if free-tier throttling blocks a batch.


# --- audio out (voiceover) -------------------------------------------------

TTS_BEST = "elevenlabs"
# Not on OpenRouter -- billed per character, not per token, so it sits outside
# the token budget entirely. Still the only option whose Indian-accent English
# holds up across a full 45s. ~$5/mo.

TTS_OPENROUTER = "openai/gpt-audio-mini"
# $0.0000024/audio-output token. In-stack alternative if you'd rather not add
# an ElevenLabs account. Cheap; voice quality is the tradeoff.


# --- image edit (styling the first frame) ----------------------------------
# Change the wrapper (background, framing, outfit), never the face. Google's
# Gemini image models ("Nano Banana") are the strongest at keeping the subject
# actually recognisable through an edit -- which is the whole point when the
# subject is a real founder.
#
# Cost note (measured 2026-07-15, correcting an earlier under-estimate): the
# per-image price is NOT the per-token figure in the model list. One Pro edit
# actually cost $0.14. So this is a rare, deliberate step -- make ONE brand
# frame and reuse it forever -- not something to run per post.

STYLE_PHOTO = "google/gemini-3-pro-image"
# Best identity preservation, ~$0.14/edit. Use once for the canonical brand
# frame, then reuse that frame as the first frame for every face reel.

STYLE_PHOTO_CHEAP = "google/gemini-2.5-flash-image"
# ~$0.04/edit. BUT tested 2026-07-15: it drifts the face -- a stocks frame
# came back slimmer, reading as a different person. Fine for throwaway
# background tests, NOT for any frame whose face reaches a reel. Identity
# preservation is the one thing that matters here, and the cheap model fails
# it. Use STYLE_PHOTO (Pro) for anything real.


# --- text ------------------------------------------------------------------
# The only layer where tokens are actually spent. See pillars.py for which
# pillar gets which.

SCRIPT_FREE = "nvidia/nemotron-3-super-120b-a12b:free"
SCRIPT_PAID = "anthropic/claude-sonnet-5"

SCORE_HIGHLIGHTS = SCRIPT_FREE
# Scoring a 20-min transcript is the one genuinely token-hungry task here
# (~4k tokens raw). Free tier makes the cost zero regardless, but prefilter()
# still halves the latency and the throttling risk.


TASKS = {
    "talking_head":   {"model": VIDEO_TALKING_HEAD,   "billing": "per_second", "tokens": False},
    "talking_head_hq": {"model": VIDEO_TALKING_HEAD_HQ, "billing": "per_second", "tokens": False},
    "broll":          {"model": VIDEO_BROLL,          "billing": "per_second", "tokens": False},
    "transcribe":     {"model": TRANSCRIBE_LOCAL,     "billing": "local",      "tokens": False},
    "tts":            {"model": TTS_BEST,             "billing": "per_char",   "tokens": False},
    "style_photo":    {"model": STYLE_PHOTO,          "billing": "per_image",  "tokens": False},
    "style_photo_cheap": {"model": STYLE_PHOTO_CHEAP, "billing": "per_image",  "tokens": False},
    "script_reach":   {"model": SCRIPT_FREE,          "billing": "per_token",  "tokens": True},
    "script_trust":   {"model": SCRIPT_PAID,          "billing": "per_token",  "tokens": True},
    "score":          {"model": SCORE_HIGHLIGHTS,     "billing": "per_token",  "tokens": True},
}


def for_task(task):
    if task not in TASKS:
        raise ValueError(f"unknown task {task!r}. Options: {list(TASKS)}")
    return TASKS[task]["model"]


def spends_tokens(task):
    """True only for tasks where prompt size actually costs something."""
    return TASKS[task]["tokens"]
