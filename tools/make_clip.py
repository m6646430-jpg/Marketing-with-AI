#!/usr/bin/env python3
"""Generate a talking-head clip from a photo and a spoken line.

    # always dry-run first -- it prints the cost and spends nothing
    python3 tools/make_clip.py --photo me.jpg --say "your line here" --dry-run
    python3 tools/make_clip.py --photo me.jpg --say "your line here"

This is the only tool here that costs real money. It refuses to run without
--yes if the cost exceeds --max-cost.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.openrouter import (OpenRouterError, generate_video, model_meta,  # noqa: E402
                                price_per_second, validate)
from reelkit.script import to_video_prompt  # noqa: E402

# Kling accepts real faces; Veo filters them. See list_models.py notes.
DEFAULT_MODEL = "kwaivgi/kling-v3.0-std"
SUBJECT = "A young man with dark hair wearing a grey hoodie"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", required=True, help="9:16 first frame (see crop_photo.py)")
    ap.add_argument("--say", required=True, help="the line he should speak")
    ap.add_argument("--subject", default=SUBJECT)
    ap.add_argument("--setting", default="a bright modern indoor space")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--duration", type=int, default=15)
    ap.add_argument("--resolution", default="720p")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--out", help="default: output/clips/<n>.mp4")
    ap.add_argument("--max-cost", type=float, default=2.00)
    ap.add_argument("--yes", action="store_true", help="skip the cost guard")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    meta = model_meta(args.model)
    problems = validate(meta, args.duration, args.resolution, args.aspect)
    if problems:
        print(f"{args.model} cannot do this:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    rate = price_per_second(meta, audio=True, resolution=args.resolution)
    cost = rate * args.duration if rate else None
    prompt = to_video_prompt(args.say, args.subject, args.setting)

    print(f"model      {args.model}")
    print(f"photo      {Path(args.photo).name}")
    print(f"spec       {args.duration}s  {args.resolution}  {args.aspect}  audio=on")
    print(f"cost       {'$%.2f' % cost if cost else 'unknown'}")
    print(f"\nprompt     {prompt}\n")

    if args.dry_run:
        print("(dry run -- nothing sent, nothing charged)")
        return

    if cost and cost > args.max_cost and not args.yes:
        sys.exit(f"cost ${cost:.2f} exceeds --max-cost ${args.max_cost:.2f}. Pass --yes to override.")

    out = Path(args.out) if args.out else None
    if out is None:
        d = OUTPUT_DIR / "clips"
        d.mkdir(parents=True, exist_ok=True)
        out = d / f"clip_{len(list(d.glob('clip_*.mp4'))) + 1:03d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    def status(s, elapsed):
        print(f"  [{elapsed:5.0f}s] {s}")

    try:
        data, usage = generate_video(
            args.model, prompt, photo=args.photo, duration=args.duration,
            resolution=args.resolution, aspect=args.aspect, audio=True,
            on_status=status,
        )
    except OpenRouterError as e:
        msg = str(e)
        print(f"\nfailed: {msg}", file=sys.stderr)
        if "filter" in msg.lower():
            print("\nThat looks like a content filter, not a bug. Google's models "
                  "refuse clear photos of real people; Kling does not.", file=sys.stderr)
        sys.exit(1)

    out.write_bytes(data)
    print(f"\nsaved {out}  ({len(data)/1024/1024:.2f} MB)")
    print(f"charged ${usage.get('cost', '?')}")
    print("\nWatch it before using it -- check the words are yours and the face holds.")

    if args.open:
        subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
