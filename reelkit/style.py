"""Style a selfie into an on-brand first frame -- without changing the face.

The first frame you feed Kling *is* the look of the reel: its background,
framing, and outfit come straight from this image. Reusing one consistent
brand frame is what makes a page recognisable; feeding random selfies makes
every post look like a different account.

The one rule that must not bend: edit the wrapper, never the face. The moment
a reel shows a face that isn't the real one, a founder selling trust has the
same authenticity problem as an avatar. Every prompt here carries that
instruction, so it can't be forgotten from the command line.
"""

# Prepended to every edit. This is the guardrail -- keep it first and explicit.
IDENTITY_LOCK = (
    "Keep the person's face, facial features, skin tone, expression, hair and "
    "identity EXACTLY as in the source image -- do not alter, beautify, slim, "
    "or restyle the face or hair in any way. Only change the requested "
    "surroundings. The person must remain instantly recognisable as the same "
    "individual. "
)

# Per-pillar backgrounds. The brand frame is the neutral base; the others give
# each pillar a matching context while keeping the same you.
BRAND_FRAMES = {
    "brand": (
        "Place the person against a clean, softly-lit neutral studio background "
        "in a subtle dark tone. Head-and-shoulders framing, centered, vertical "
        "9:16. Modern, professional, uncluttered."
    ),
    "ai": (
        "Place the person in a modern tech workspace, softly blurred, with a "
        "hint of screens or abstract blue light behind. Head-and-shoulders, "
        "vertical 9:16, professional and clean, background well out of focus."
    ),
    "stocks": (
        "Place the person against a softly blurred financial setting -- muted "
        "market charts or a trading-desk ambience, dark and subtle, never "
        "garish. Head-and-shoulders, vertical 9:16, background out of focus."
    ),
    "jobs": (
        "Place the person in a bright, blurred modern office setting. "
        "Head-and-shoulders, vertical 9:16, warm and approachable, background "
        "well out of focus."
    ),
    "resume": (
        "Place the person against a clean, warm, professional background with a "
        "subtle desk or interview ambience, softly blurred. Head-and-shoulders, "
        "vertical 9:16, trustworthy and calm, background out of focus."
    ),
}

OUTFIT_HINT = (
    " Keep the clothing simple and consistent: a plain, solid-colour top that "
    "reads as neat and professional."
)


def build_prompt(pillar="brand", extra=None, restyle_outfit=False):
    base = BRAND_FRAMES.get(pillar)
    if not base:
        raise ValueError(f"unknown pillar {pillar!r}. Options: {list(BRAND_FRAMES)}")
    prompt = IDENTITY_LOCK + base
    if restyle_outfit:
        prompt += OUTFIT_HINT
    if extra:
        prompt += " " + extra.strip()
    return prompt
