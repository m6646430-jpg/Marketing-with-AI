"""Content pillars for the page.

Encodes the strategy: reach pillars (ai, stocks) earn attention and run
faceless; trust pillars (jobs, resume) need a face and cost money per clip.
Ratio target per 10 posts: 4 ai / 3 stocks / 2 jobs / 1 resume.
"""

DISCLAIMER = "Not investment advice. Educational content only."

# Reach pillars run on the free tier -- volume matters more than polish, and
# they are 7 of every 10 posts. Trust pillars carry the face and the funnel,
# so they get a paid model: the free one is accurate but flat, and a flat hook
# loses the first two seconds. ~3 scripts/week on paid is under a cent.
from .models import SCRIPT_FREE as FREE_MODEL  # noqa: E402
from .models import SCRIPT_PAID as PAID_MODEL  # noqa: E402

PILLARS = {
    "ai": {
        "name": "AI updates",
        "model": FREE_MODEL,
        "faceless": True,
        "target_per_10": 4,
        "angle": (
            "What changed in AI this week and what it means for a normal "
            "person's job or money. Written by a developer who builds with "
            "these tools, not a news reader."
        ),
        "structure": "hook -> 3 concrete beats -> 'what this means for you' closer",
    },
    "stocks": {
        "name": "Stock market",
        "model": FREE_MODEL,
        "faceless": True,
        "target_per_10": 3,
        "angle": (
            "Market news, data and mechanics explained plainly. Never a buy "
            "or sell call, never a price target -- news and education only."
        ),
        "structure": "hook -> chart/data point -> 2 supporting facts -> takeaway",
        "disclaimer": DISCLAIMER,
    },
    "jobs": {
        "name": "Jobs / career",
        "model": PAID_MODEL,
        "faceless": False,
        "target_per_10": 2,
        "angle": (
            "Hiring reality for international students and job seekers -- ATS, "
            "referrals, applications. Practical, specific, no generic advice."
        ),
        "structure": "problem hook -> why it happens -> the fix -> soft CTA",
    },
    "resume": {
        "name": "Resume / DriftAI",
        "model": PAID_MODEL,
        "faceless": False,
        "target_per_10": 1,
        "angle": (
            "Resume and application help, leading to DriftAI. Give the actual "
            "value away in the reel; the CTA is earned, never a pitch."
        ),
        "structure": "problem hook -> real tip they can use today -> comment-gated CTA",
    },
}

# The reel is 9:16 and read muted -- these constraints are non-negotiable.
GLOBAL_RULES = """
- Spoken script only. No stage directions, no emoji, no hashtags.
- First line must stop a scroll in under 2 seconds. No throat-clearing.
- Short sentences. Speak like a person, not a press release.
- Never claim to be a financial advisor. Never give buy/sell calls.
- End with one clear action, not three.
"""


def words_for_duration(seconds):
    """Natural speech is ~2.4 words/second. Overshooting means it gets cut off."""
    return int(seconds * 2.4)
