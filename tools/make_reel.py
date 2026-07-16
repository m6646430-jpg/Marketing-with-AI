#!/usr/bin/env python3
"""One finished reel, end to end: script -> clip -> transcribe -> captions.

    # always dry-run first: shows the script, the plan, and the total cost
    python3 tools/make_reel.py --pillar stocks --frame output/frames/trading_desk.jpg \
        --content "what an index fund is and why beginners start there" --dry-run

    # then for real
    python3 tools/make_reel.py --pillar stocks --frame output/frames/trading_desk.jpg \
        --content "..." --open

Only the clip step costs money ($1.89 for 15s). Script, transcription and
captions are free. The --frame is a styled first frame from style_photo.py --
rotate different location frames across reels for variety with a consistent
face.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.captions import build_ass  # noqa: E402
from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.models import for_task  # noqa: E402
from reelkit.openrouter import (OpenRouterError, generate_video, model_meta,  # noqa: E402
                                price_per_second, validate)
from reelkit.pillars import PILLARS  # noqa: E402
from reelkit.script import to_video_prompt, write_script  # noqa: E402
from reelkit.transcribe import DEFAULT_SIZE, all_words, ffmpeg_path, transcribe  # noqa: E402

SUBJECT = "A young man with dark hair wearing a grey tie-dye hoodie"


def step(n, total, msg):
    print(f"\n[{n}/{total}] {msg}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillar", required=True, choices=list(PILLARS))
    ap.add_argument("--frame", required=True, help="styled first frame (style_photo.py)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--content", help="raw notes -> script is written for you")
    g.add_argument("--say", help="an exact spoken line, skip script writing")
    ap.add_argument("--duration", type=int, default=15)
    ap.add_argument("--subject", default=SUBJECT)
    ap.add_argument("--model", help="override the video model")
    ap.add_argument("--name", help="output basename (default: <pillar>_reel)")
    ap.add_argument("--whisper-size", default=DEFAULT_SIZE)
    ap.add_argument("--margin-v", type=int, default=340, help="caption height off the bottom")
    ap.add_argument("--max-cost", type=float, default=2.50)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    frame = Path(args.frame)
    if not frame.is_file():
        sys.exit(f"frame not found: {frame} -- make one with style_photo.py")

    video_model = args.model or for_task("talking_head")
    meta = model_meta(video_model)
    problems = validate(meta, args.duration, "720p", "9:16")
    if problems:
        sys.exit("video model can't do this: " + "; ".join(problems))
    rate = price_per_second(meta, audio=True, resolution="720p")
    cost = rate * args.duration if rate else None
    name = args.name or f"{args.pillar}_reel"

    # ---- step 1: script (free) --------------------------------------------
    if args.say:
        spoken = args.say
        print(f"using provided line ({len(spoken.split())} words)", file=sys.stderr)
    else:
        step(1, 4, f"writing {args.pillar} script (free)...")
        out = write_script(args.content, args.pillar, duration=args.duration)
        spoken = out["script"]
        print(f"\nHOOK  {out['hook']}")
        print(f"\n{spoken}")
        print(f"\n{out['word_count']}/{out['budget']} words"
              + ("  OVER BUDGET" if out["over_budget"] else ""), file=sys.stderr)

    prompt = to_video_prompt(spoken, args.subject, "this scene")

    print(f"\n{'='*60}")
    print(f"plan:  script (free) -> clip (${cost:.2f}) -> transcribe (free) -> captions (free)")
    print(f"frame: {frame.name}")
    print(f"total cost: ${cost:.2f}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n(dry run -- nothing sent, nothing charged)")
        return

    if cost and cost > args.max_cost and not args.yes:
        sys.exit(f"cost ${cost:.2f} exceeds --max-cost ${args.max_cost:.2f}. Pass --yes.")

    clips = OUTPUT_DIR / "clips"; clips.mkdir(parents=True, exist_ok=True)
    raw = clips / f"{name}.mp4"

    # ---- step 2: clip (paid) ----------------------------------------------
    step(2, 4, f"generating {args.duration}s clip via {video_model} (${cost:.2f})...")
    try:
        data, usage = generate_video(
            video_model, prompt, photo=str(frame), duration=args.duration,
            resolution="720p", aspect="9:16", audio=True,
            on_status=lambda s, e: print(f"    [{e:4.0f}s] {s}", file=sys.stderr),
        )
    except OpenRouterError as e:
        sys.exit(f"clip failed: {e}")
    raw.write_bytes(data)
    print(f"    clip saved, charged ${usage.get('cost','?')}", file=sys.stderr)

    # ---- step 3: transcribe (free, also verifies the words) ---------------
    step(3, 4, "transcribing for caption timings (free)...")
    segments, info = transcribe(raw, size=args.whisper_size)
    words = all_words(segments)
    print(f"    {len(words)} words timed, {info['language']} "
          f"{info['language_probability']:.0%}", file=sys.stderr)
    for s in segments:
        print(f"    [{s['start']:5.1f}] {s['text']}", file=sys.stderr)
    if not words:
        sys.exit("no word timings -- clip saved without captions at " + str(raw))

    # ---- step 4: captions (free) ------------------------------------------
    step(4, 4, "burning captions (free)...")
    capd = OUTPUT_DIR / "captioned"; capd.mkdir(parents=True, exist_ok=True)
    ass_path = capd / f"{name}.ass"
    ass_path.write_text(build_ass(words, style={"margin_v": args.margin_v}))
    final = capd / f"{name}_final.mp4"
    escaped = str(ass_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    r = subprocess.run([
        ffmpeg_path(), "-y", "-i", str(raw), "-vf", f"ass='{escaped}'",
        "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(final),
    ], capture_output=True, text=True)
    ass_path.unlink(missing_ok=True)
    if r.returncode != 0:
        print(r.stderr[-1200:], file=sys.stderr)
        sys.exit("caption burn failed -- raw clip is at " + str(raw))

    print(f"\nDONE  {final}  ({final.stat().st_size/1024/1024:.1f} MB)")
    print(f"cost  ${usage.get('cost', cost):.2f}")
    print("watch it: check the audio matches and the face holds all the way through.")
    if args.open:
        subprocess.run(["open", str(final)], check=False)


if __name__ == "__main__":
    main()
