#!/usr/bin/env python3
"""Crop a photo to a 9:16 head-and-shoulders first frame.

    python3 tools/crop_photo.py --src selfie.jpg --out output/frames/me.jpg
    python3 tools/crop_photo.py --src selfie.jpg --out me.jpg --cx 660 --top 355 --height 620

Free. Always open the result and look at it -- the auto-guess is only a guess.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.photo import crop_9x16  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cx", type=int, help="face center x in source pixels")
    ap.add_argument("--top", type=int, help="top of head y in source pixels")
    ap.add_argument("--height", type=int, help="crop height in source pixels")
    ap.add_argument("--open", action="store_true", help="open the result (macOS)")
    args = ap.parse_args()

    info = crop_9x16(args.src, args.out, args.cx, args.top, args.height)

    print(f"source   {info['source_size'][0]}x{info['source_size'][1]}")
    print(f"crop     {info['crop_box']} -> {info['crop_size'][0]}x{info['crop_size'][1]}")
    print(f"output   {info['output']}  (720x1280, {info['upscale']}x upscale)")
    if info["upscale"] > 2.5:
        print("\nwarning: heavy upscale -- the face was small in the source.")
        print("a closer shot will give the model much more to work with.")

    if args.open:
        subprocess.run(["open", info["output"]], check=False)


if __name__ == "__main__":
    main()
