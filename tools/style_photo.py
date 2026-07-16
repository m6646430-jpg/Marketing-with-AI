#!/usr/bin/env python3
"""Turn a selfie into an on-brand first frame -- same face, styled surroundings.

    # see the prompt and cost, spend nothing
    python3 tools/style_photo.py --src selfie.jpg --pillar brand --dry-run

    # make the canonical brand frame (reuse this for every face reel)
    python3 tools/style_photo.py --src selfie.jpg --pillar brand --open

    # per-pillar background, cheaper model
    python3 tools/style_photo.py --src output/frames/brand.jpg --pillar stocks --cheap

The face is never edited -- only the background and framing. That guardrail is
built into every prompt (see reelkit/style.py), not left to the flags.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.models import STYLE_PHOTO, STYLE_PHOTO_CHEAP  # noqa: E402
from reelkit.openrouter import OpenRouterError, edit_image  # noqa: E402
from reelkit.style import BRAND_FRAMES, build_prompt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="a real selfie, front-facing")
    ap.add_argument("--pillar", default="brand", choices=list(BRAND_FRAMES))
    ap.add_argument("--extra", help="extra styling notes (surroundings only)")
    ap.add_argument("--restyle-outfit", action="store_true",
                    help="also normalise the top to a plain professional colour")
    ap.add_argument("--cheap", action="store_true",
                    help="use the ~10x cheaper model (fine once brand frame exists)")
    ap.add_argument("--out", help="default: output/frames/<pillar>.jpg")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.is_file():
        sys.exit(f"not found: {src}")

    model = STYLE_PHOTO_CHEAP if args.cheap else STYLE_PHOTO
    prompt = build_prompt(args.pillar, extra=args.extra,
                          restyle_outfit=args.restyle_outfit)

    print(f"model    {model}")
    print(f"source   {src.name}")
    print(f"pillar   {args.pillar}")
    print(f"face     locked (surroundings only)")
    print(f"\nprompt   {prompt}\n")

    if args.dry_run:
        print("(dry run -- nothing sent, nothing charged)")
        return

    out = Path(args.out) if args.out else OUTPUT_DIR / "frames" / f"{args.pillar}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        data, usage = edit_image(model, prompt, src)
    except OpenRouterError as e:
        sys.exit(f"failed: {e}")

    out.write_bytes(data)
    print(f"saved {out}  ({len(data)/1024:.0f} KB)")
    print(f"charged ${usage.get('cost', '?')}")
    print("\nCheck the face is still yours before using it as a first frame.")

    if args.open:
        subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
