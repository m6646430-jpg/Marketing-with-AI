#!/usr/bin/env python3
"""Generate a reusable animated background from a still image. Pay once, reuse forever.

    python3 tools/make_background.py --still backgrounds/home_office_still.png \
        --name home_office --dry-run
    python3 tools/make_background.py --still backgrounds/studio_still.png --name studio

Defaults to Kling v3.0 STD at 720p -- the cheaper option ($0.126/s vs $0.168 pro,
720p vs 1080p). A background gets blurred behind the subject, so 720p std is
plenty. Output is saved to backgrounds/<name>.mp4 for reuse across every reel.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.config import ROOT  # noqa: E402
from reelkit.openrouter import (OpenRouterError, generate_video, model_meta,  # noqa: E402
                                price_per_second)

# std + 720p = the cheap default. Pass --pro / --1080p only if you can see the difference.
DEFAULT_MODEL = "kwaivgi/kling-v3.0-std"
DEFAULT_PROMPT = ("Subtle, professional ambient motion: soft shifting light, gentle depth, "
                  "a very slow barely-there camera push-in. Calm, premium, understated. "
                  "No fast motion, no text, no people.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", required=True, help="a background still (see backgrounds/*_still.png)")
    ap.add_argument("--name", required=True, help="library name -> backgrounds/<name>.mp4")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--seconds", type=int, default=8)
    ap.add_argument("--pro", action="store_true", help="use kling pro (dearer, marginally better)")
    ap.add_argument("--1080p", dest="hd", action="store_true", help="1080p instead of 720p")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    still = Path(args.still)
    if not still.is_file():
        sys.exit(f"still not found: {still}")
    model = "kwaivgi/kling-v3.0-pro" if args.pro else DEFAULT_MODEL
    res = "1080p" if args.hd else "720p"
    meta = model_meta(model)
    # backgrounds are generated silently (audio=False), so use the cheaper no-audio rate
    cost = price_per_second(meta, audio=False, resolution=res) * args.seconds

    print(f"model  {model}")
    print(f"spec   {args.seconds}s  {res}  9:16")
    print(f"cost   ${cost:.2f}   (one-time -- reused across all reels)")

    if args.dry_run:
        print("\n(dry run -- nothing generated)")
        return

    out = ROOT / "backgrounds" / f"{args.name}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        data, usage = generate_video(model, args.prompt, photo=str(still),
            duration=args.seconds, resolution=res, aspect="9:16", audio=False,
            on_status=lambda s, e: print(f"  [{e:4.0f}s] {s}", file=sys.stderr))
    except OpenRouterError as e:
        sys.exit(f"failed: {e}")
    out.write_bytes(data)
    print(f"\nsaved {out}  charged ${usage.get('cost')}")
    print("reuse it: python3 tools/replace_bg.py --recording <clip> --background "
          f"backgrounds/{args.name}.mp4")


if __name__ == "__main__":
    main()
