#!/usr/bin/env python3
"""Burn word-by-word captions into a video. Free, local, zero tokens.

    python3 tools/add_captions.py --src clip.mp4 --open
    python3 tools/add_captions.py --src clip.mp4 --transcript output/transcripts/clip.json
    python3 tools/add_captions.py --src clip.mp4 --srt-only

Transcribes with whisper unless you pass an existing --transcript.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.captions import DEFAULT_STYLE, build_ass, build_srt  # noqa: E402
from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.transcribe import DEFAULT_SIZE, all_words, ffmpeg_path, transcribe  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", help="default: output/captioned/<name>_cc.mp4")
    ap.add_argument("--transcript", help="reuse a saved transcript instead of re-running whisper")
    ap.add_argument("--size", default=DEFAULT_SIZE)
    ap.add_argument("--lang", default=None)
    ap.add_argument("--words-per-chunk", type=int, default=DEFAULT_STYLE["words_per_chunk"])
    ap.add_argument("--font-size", type=int, default=DEFAULT_STYLE["size"])
    ap.add_argument("--margin-v", type=int, default=DEFAULT_STYLE["margin_v"])
    ap.add_argument("--srt-only", action="store_true", help="write a .srt, don't touch the video")
    ap.add_argument("--keep-ass", action="store_true", help="keep the .ass for tweaking")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.is_file():
        sys.exit(f"not found: {src}")

    if args.transcript:
        segments = json.loads(Path(args.transcript).read_text())["segments"]
        print(f"using transcript {args.transcript}", file=sys.stderr)
    else:
        print(f"transcribing with whisper-{args.size} (local, free)...", file=sys.stderr)
        segments, _ = transcribe(src, size=args.size, language=args.lang)

    words = all_words(segments)
    if not words:
        sys.exit("no word-level timings -- cannot build animated captions.\n"
                 "Try a larger --size, or check the clip actually has speech.")
    print(f"{len(words)} words timed", file=sys.stderr)

    out_dir = OUTPUT_DIR / "captioned"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.srt_only:
        p = out_dir / f"{src.stem}.srt"
        p.write_text(build_srt(words, args.words_per_chunk))
        print(f"saved {p}")
        return

    ass = build_ass(words, style={
        "words_per_chunk": args.words_per_chunk,
        "size": args.font_size,
        "margin_v": args.margin_v,
    })
    ass_path = out_dir / f"{src.stem}.ass"
    ass_path.write_text(ass)

    out = Path(args.out) if args.out else out_dir / f"{src.stem}_cc.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    # ass filter needs an escaped path; re-encode video, copy audio untouched.
    escaped = str(ass_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    cmd = [
        ffmpeg_path(), "-y", "-i", str(src),
        "-vf", f"ass='{escaped}'",
        "-c:a", "copy",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        str(out),
    ]
    print("burning captions...", file=sys.stderr)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], file=sys.stderr)
        sys.exit("ffmpeg failed")

    if not args.keep_ass:
        ass_path.unlink(missing_ok=True)

    print(f"\nsaved {out}  ({out.stat().st_size/1024/1024:.2f} MB)")
    if args.open:
        subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
