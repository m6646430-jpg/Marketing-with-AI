"""Turn raw content into a reel script."""
import json

from .openrouter import chat
from .pillars import GLOBAL_RULES, PILLARS, words_for_duration

DEFAULT_MODEL = "anthropic/claude-sonnet-5"

SYSTEM = """You write short-form vertical video scripts for an Instagram/YouTube \
reels page run by Mahesh, an AI developer and active stock investor who also runs \
DriftAI (a resume and job-application service).

His voice: technical but plain-spoken. He explains things people find confusing. \
He is not a hype account and not a news reader -- he builds with these tools and \
invests his own money, so he speaks from doing, not reporting.

Return ONLY valid JSON, no markdown fence, matching this shape:
{
  "hook": "the first spoken line, under 2 seconds",
  "script": "the full spoken script including the hook",
  "on_screen_text": ["3-5 short caption phrases for key beats"],
  "cta": "the closing call to action",
  "word_count": 0
}"""


def write_script(raw_content, pillar, duration=30, model=DEFAULT_MODEL, key=None):
    """raw_content: your notes/article/data. Returns a dict (see SYSTEM)."""
    if pillar not in PILLARS:
        raise ValueError(f"unknown pillar {pillar!r}. Options: {list(PILLARS)}")
    p = PILLARS[pillar]
    budget = words_for_duration(duration)

    prompt = f"""Pillar: {p['name']}
Angle: {p['angle']}
Structure: {p['structure']}
{"Must include this disclaimer verbatim somewhere: " + p['disclaimer'] if p.get('disclaimer') else ""}

Rules:{GLOBAL_RULES}
Hard limit: {budget} words for the spoken script ({duration}s at natural pace).
Going over means the video cuts him off mid-sentence.

Raw content to work from:
---
{raw_content}
---

Write the script."""

    out = chat(model, [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ], key=key)

    text = out.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(f"model did not return valid JSON:\n{out[:500]}")

    data["word_count"] = len(data.get("script", "").split())
    data["pillar"] = pillar
    data["over_budget"] = data["word_count"] > budget
    data["budget"] = budget
    return data


def to_video_prompt(script_line, subject_desc, setting="a bright modern indoor space"):
    """Wrap a spoken line as a scene prompt with quoted speech.

    Kling and Veo both produce dialogue when speech is quoted inside a scene
    description. Passing a bare script makes them generate a scene *about* it.
    """
    return (
        f"{subject_desc} stands in {setting}, looking directly into the camera "
        f"and speaking straight to it with a warm, confident smile and natural "
        f'head movement, saying: "{script_line}" Clear Indian English accent, '
        f"friendly energetic delivery, static camera, vertical portrait framing, "
        f"soft indoor lighting, shallow depth of field."
    )
