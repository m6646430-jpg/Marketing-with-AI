"""Score a long transcript for clip-worthy moments (the record-and-clip path).

This is the step tokens.py was built for. A 20-minute video is ~3,000 words of
transcript; prefilter() drops the filler and compact() halves the token cost
before the scorer ever sees it. The scorer is free-tier, so cost is zero -- the
token work is about latency and not tripping rate limits, not price.

A "highlight" is a self-contained 15-45s span that hooks in the first line and
resolves by the end. The scorer returns spans by segment index; we map those
back to timestamps from the original transcript.
"""
import json

from .models import for_task
from .openrouter import chat
from .tokens import compact, prefilter

SCORE_SYSTEM = """You find the most clip-worthy moments in a video transcript \
for short vertical Reels. A good clip:
- opens with a line that stops a scroll (a hook, a bold claim, a question)
- is self-contained: it makes sense without the rest of the video
- resolves a thought within 15-45 seconds
- carries one idea, opinion, story, or reveal -- not rambling

You are given numbered transcript lines. Return ONLY valid JSON:
{
  "clips": [
    {"start_line": int, "end_line": int, "hook": "the opening line",
     "why": "one phrase on why it works", "score": 1-10}
  ]
}
Rank best first. Prefer fewer strong clips over many weak ones."""


def find_highlights(segments, target_clips=5, model=None, key=None):
    """segments: whisper output [{start,end,text,...}]. Returns clips with
    real timestamps attached, best first."""
    kept = prefilter(segments)
    if not kept:
        return []
    # Map compact indices back to the kept segments.
    listing = compact(kept)
    model = model or for_task("score")

    out = chat(model, [
        {"role": "system", "content": SCORE_SYSTEM},
        {"role": "user", "content":
            f"Find up to {target_clips} clips.\n\nTranscript:\n{listing}"},
    ], key=key)

    text = out.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    clips = json.loads(text).get("clips", [])

    result = []
    for c in clips:
        try:
            i, j = int(c["start_line"]), int(c["end_line"])
            i, j = max(0, i), min(len(kept) - 1, j)
            if j < i:
                i, j = j, i
            result.append({
                "start": kept[i]["start"],
                "end": kept[j]["end"],
                "duration": round(kept[j]["end"] - kept[i]["start"], 1),
                "hook": c.get("hook", ""),
                "why": c.get("why", ""),
                "score": c.get("score", 0),
                "text": " ".join(kept[k]["text"] for k in range(i, j + 1)),
            })
        except (KeyError, ValueError, IndexError):
            continue

    result.sort(key=lambda r: r.get("score", 0), reverse=True)
    return result
