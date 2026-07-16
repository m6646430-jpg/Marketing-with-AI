#!/usr/bin/env python3
"""Transcribe a video or audio file locally. Free, offline, zero tokens.

    python3 tools/transcribe.py --src clip.mp4
    python3 tools/transcribe.py --src clip.mp4 --size small --lang en --save

First run downloads the model weights (~145 MB for base), then they're cached.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.transcribe import DEFAULT_SIZE, all_words, plain_text, transcribe  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="video or audio file")
    ap.add_argument("--size", default=DEFAULT_SIZE,
                    help="tiny|base|small|medium -- bigger is better on accents")
    ap.add_argument("--lang", default=None, help="e.g. en. omit to auto-detect")
    ap.add_argument("--no-vad", action="store_true",
                    help="disable silence skipping (slower, risks hallucinated text)")
    ap.add_argument("--save", action="store_true", help="write JSON to output/transcripts/")
    ap.add_argument("--text-only", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.is_file():
        sys.exit(f"not found: {src}")

    print(f"transcribing {src.name} with whisper-{args.size} (local, free)...",
          file=sys.stderr)
    segments, info = transcribe(src, size=args.size, language=args.lang,
                                vad=not args.no_vad)

    if args.text_only:
        print(plain_text(segments))
        return

    words = all_words(segments)
    print(f"\nlanguage   {info['language']} ({info['language_probability']:.0%} confident)")
    print(f"duration   {info['duration']}s")
    print(f"segments   {len(segments)}")
    print(f"words      {len(words)}")
    if not words:
        print("\nno word-level timings came back -- captions will be segment-level only.")
    print()
    for s in segments:
        print(f"  [{s['start']:6.2f} -> {s['end']:6.2f}]  {s['text']}")

    if args.save:
        d = OUTPUT_DIR / "transcripts"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{src.stem}.json"
        p.write_text(json.dumps({"info": info, "segments": segments}, indent=2))
        print(f"\nsaved {p}")


if __name__ == "__main__":
    main()
