"""Turn raw content into a reel script."""
import json

from .openrouter import chat
from .pillars import GLOBAL_RULES, PILLARS, words_for_duration

from .pillars import FREE_MODEL, PAID_MODEL  # noqa: F401  (re-exported)

# Each pillar names its own model (see pillars.py). This is only the fallback
# for callers that pass neither a pillar model nor an explicit override.
DEFAULT_MODEL = FREE_MODEL

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


def write_script(raw_content, pillar, duration=30, model=None, key=None):
    """raw_content: your notes/article/data. Returns a dict (see SYSTEM).

    model=None uses the pillar's own model -- free for reach pillars, paid for
    the ones carrying the face and the funnel.
    """
    if pillar not in PILLARS:
        raise ValueError(f"unknown pillar {pillar!r}. Options: {list(PILLARS)}")
    p = PILLARS[pillar]
    model = model or p.get("model", DEFAULT_MODEL)
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
    data["model"] = model
    data["over_budget"] = data["word_count"] > budget
    data["budget"] = budget
    return data


# Cinematic defaults. Principle-level (shot, light, camera, delivery), not any
# one platform's syntax. Deliberately tight: a few strong directives read
# better than a wall of adjectives, which over-constrains the model and can
# make output worse. Tune these knobs rather than piling on more.
SHOT = "medium close-up, head and shoulders, subject centered"
LIGHT = "soft key light with gentle rim separation, flattering and clean"
CAMERA = "locked-off camera with a very subtle slow push-in"
GRADE = "natural cinematic colour, crisp, not oversaturated"


def to_video_prompt(script_line, subject_desc, setting="the scene",
                    energy="warm, confident, conversational"):
    """Wrap a spoken line as a cinematic scene prompt with quoted speech.

    Kling and Veo produce dialogue when speech is quoted inside the scene
    description -- a bare script makes them generate a scene *about* it, so the
    quotes are load-bearing and must stay. The cinematic direction (shot, light,
    camera, delivery) lifts output quality at no extra cost; the first frame
    already carries the background, so `setting` is a light cue, not the anchor.
    """
    return (
        f"{subject_desc}, in {setting}. {SHOT}. "
        f"The subject looks directly into the lens and speaks straight to camera "
        f"with {energy} delivery, natural head movement and genuine "
        f'micro-expressions, saying: "{script_line}" '
        f"Lips accurately synced to the spoken words. Clear Indian English accent. "
        f"{LIGHT}. {CAMERA}. {GRADE}. Vertical 9:16 framing, shallow depth of field."
    )
