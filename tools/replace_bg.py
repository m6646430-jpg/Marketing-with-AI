#!/usr/bin/env python3
"""Put a recording onto a reusable background. Free (all local). ONE output file.

    python3 tools/replace_bg.py --recording intro.mp4 \
        --background backgrounds/home_office.mp4 --open

The background loops to cover the recording, so one 8s background works for a
90s clip. Reuse the same background across every reel -- you already paid to
make it once. Output is a single finished file; there is no separate
background-only file to open by mistake.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.bgreplace import replace  # noqa: E402
from reelkit.config import OUTPUT_DIR  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recording", required=True, help="your talking-head video")
    ap.add_argument("--background", required=True, help="a background video (backgrounds/*.mp4)")
    ap.add_argument("--out", help="default: output/final/<recording>_bg.mp4")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    rec = Path(args.recording); bg = Path(args.background)
    for p, label in [(rec, "recording"), (bg, "background")]:
        if not p.is_file():
            sys.exit(f"{label} not found: {p}")

    out = Path(args.out) if args.out else OUTPUT_DIR / "final" / f"{rec.stem}_bg.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"recording   {rec.name}")
    print(f"background  {bg.name} (loops to cover length)")
    print("compositing (local, free)... this is ~7 fps on CPU\n")

    def prog(i, total, rate, eta):
        print(f"  {i}/{total}  {rate:.1f} fps  ETA {eta/60:.1f} min", file=sys.stderr)

    replace(rec, bg, out, on_progress=prog)

    print(f"\nDONE  {out}  ({out.stat().st_size/1024/1024:.1f} MB)")
    print("this single file has you composited on the background.")
    if args.open:
        subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
