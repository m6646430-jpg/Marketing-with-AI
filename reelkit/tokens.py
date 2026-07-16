"""Token accounting and reduction.

Read this before optimising anything: measured on 2026-07-15, one script call
is ~400 tokens, so 10 scripts/week is ~4k tokens -- $0.00 on the free tier and
$0.008 on Sonnet. Video, by contrast, runs ~$5.67/week. Trimming script
prompts is optimising a rounding error.

Token work only pays off on ONE task: scoring a long transcript for highlights
(the record-and-clip path). A 20-minute video is ~3,000 words of transcript
(~4,000 tokens) per scoring pass. That's where prefilter() earns its keep --
not on cost (the scorer is free-tier) but on latency and throttling, since
free models 429 under load and a smaller prompt retries faster.

The largest saving available is architectural, not textual: transcribe locally
with faster-whisper. That takes a task from thousands of tokens to zero, and
gives better output (word-level timestamps) than any LLM would.
"""

# Filler that carries no highlight signal. Segments that are *only* filler are
# dropped before the LLM ever sees them.
FILLER = {
    "um", "uh", "erm", "hmm", "ah", "oh", "like", "so", "yeah", "yes", "no",
    "okay", "ok", "right", "actually", "basically", "literally", "you know",
    "i mean", "sort of", "kind of",
}

MIN_WORDS = 4       # shorter than this cannot contain a usable hook
MIN_SECONDS = 1.5   # shorter than this cannot be cut into anything


def estimate(text):
    """Rough token count. ~4 chars/token for English -- good enough to budget."""
    return len(text) // 4


def is_filler(text):
    words = [w.strip(".,!?").lower() for w in text.split()]
    return bool(words) and all(w in FILLER for w in words)


def prefilter(segments):
    """Drop segments that cannot become a highlight, before spending tokens.

    segments: [{"start": float, "end": float, "text": str}, ...]
    Returns the same shape, filtered. Pure heuristics -- costs nothing.

    Measured on a realistic spoken transcript: drops ~70% of segments but only
    ~20% of tokens, because filler segments are short. The point is signal, not
    savings -- the scorer stops wading through "um" and "right" to find the
    three sentences that matter. compact() saves more tokens (~31%) than this
    does.
    """
    kept = []
    for s in segments:
        text = (s.get("text") or "").strip()
        if len(text.split()) < MIN_WORDS:
            continue
        if (s.get("end", 0) - s.get("start", 0)) < MIN_SECONDS:
            continue
        if is_filler(text):
            continue
        kept.append(s)
    return kept


def compact(segments):
    """Render segments for an LLM as tersely as possible without losing meaning.

    JSON costs ~2x: every key is repeated on every row. An indexed line format
    carries the same information in roughly half the tokens, and models read it
    fine. The index is what the model refers back to, so timestamps never need
    to make the round trip.
    """
    return "\n".join(f"{i}|{s['text'].strip()}" for i, s in enumerate(segments))


def savings_report(before, after):
    """What prefilter actually bought. Print it -- silent optimisation is a lie."""
    b, a = estimate(before), estimate(after)
    pct = (1 - a / b) * 100 if b else 0
    return {
        "before_tokens": b,
        "after_tokens": a,
        "saved_tokens": b - a,
        "saved_pct": round(pct, 1),
    }
