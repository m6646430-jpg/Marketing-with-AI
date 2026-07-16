#!/usr/bin/env python3
"""Turn one long recording into several vertical Reels (the record-and-clip path).

    # see the highlights it would cut, spend nothing on cutting
    python3 tools/clip_video.py --src my_recording.mp4 --clips 5 --dry-run

    # cut them: face-cropped to 9:16, captioned, optionally upscaled to 1080p
    python3 tools/clip_video.py --src my_recording.mp4 --clips 5 --upscale --open

Free end to end: transcription, highlight scoring (free-tier LLM), cutting,
face-crop, captions and ffmpeg upscale all run locally / on the free tier.
This is the alternative to generating clips -- record once, harvest many.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.captions import build_ass  # noqa: E402
from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.facecrop import crop_filter  # noqa: E402
from reelkit.highlights import find_highlights  # noqa: E402
from reelkit.transcribe import DEFAULT_SIZE, all_words, ffmpeg_path, transcribe  # noqa: E402
from reelkit.upscale import ffmpeg_upscale  # noqa: E402


def cut(src, start, end, out, crop):
    """Cut [start,end], apply the face-crop, scale to 720x1280."""
    vf = f"{crop},scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,format=yuv420p"
    subprocess.run([
        ffmpeg_path(), "-y", "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", str(src),
        "-vf", vf, "-c:a", "aac", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        str(out),
    ], capture_output=True, check=True)
    return out


def caption(src, words, out, margin_v=340):
    capd = out.parent
    ass = capd / (out.stem + ".ass")
    ass.write_text(build_ass(words, style={"margin_v": margin_v}))
    esc = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    r = subprocess.run([ffmpeg_path(), "-y", "-i", str(src), "-vf", f"ass='{esc}'",
                        "-c:a", "copy", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "18", str(out)], capture_output=True, text=True)
    ass.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="a long recording (mp4/mov)")
    ap.add_argument("--clips", type=int, default=5)
    ap.add_argument("--whisper-size", default=DEFAULT_SIZE)
    ap.add_argument("--min-score", type=int, default=6, help="drop clips below this")
    ap.add_argument("--upscale", action="store_true", help="1080p ffmpeg upscale")
    ap.add_argument("--margin-v", type=int, default=340)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.is_file():
        sys.exit(f"not found: {src}")

    print(f"transcribing {src.name} (free, local)...", file=sys.stderr)
    segments, info = transcribe(src, size=args.whisper_size)
    print(f"  {info['duration']}s, {len(segments)} segments, "
          f"{info['language']} {info['language_probability']:.0%}", file=sys.stderr)
    if not segments:
        sys.exit("no speech found -- nothing to clip.")

    print("scoring highlights (free-tier LLM)...", file=sys.stderr)
    highs = find_highlights(segments, target_clips=args.clips)
    highs = [h for h in highs if h.get("score", 0) >= args.min_score]
    if not highs:
        sys.exit(f"no clips scored >= {args.min_score}. Lower --min-score to see more.")

    print(f"\n{len(highs)} clip(s):")
    for i, h in enumerate(highs, 1):
        print(f"\n#{i}  [{h['start']:.1f}-{h['end']:.1f}s, {h['duration']}s, score {h['score']}]")
        print(f"    hook: {h['hook']}")
        print(f"    why:  {h['why']}")

    if args.dry_run:
        print("\n(dry run -- nothing cut)")
        return

    outdir = OUTPUT_DIR / "clips_from_video" / src.stem
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nface-tracking crop window from {src.name}...", file=sys.stderr)
    crop, cinfo = crop_filter(src)
    print(f"  face_center={cinfo['face_center']}, crop_w={cinfo['crop_w']}, x={cinfo['x']}",
          file=sys.stderr)

    made = []
    for i, h in enumerate(highs, 1):
        print(f"[{i}/{len(highs)}] cut + crop...", file=sys.stderr)
        raw = outdir / f"clip{i}.mp4"
        cut(src, h["start"], h["end"], raw, crop)

        print(f"[{i}] captions...", file=sys.stderr)
        segs, _ = transcribe(raw, size=args.whisper_size)
        words = all_words(segs)
        capped = outdir / f"clip{i}_cc.mp4"
        if words:
            caption(raw, words, capped, args.margin_v)
        else:
            capped = raw

        final = capped
        if args.upscale:
            print(f"[{i}] upscaling to 1080p...", file=sys.stderr)
            final = outdir / f"clip{i}_1080.mp4"
            ffmpeg_upscale(capped, final)

        made.append(final)
        print(f"    -> {final}", file=sys.stderr)

    print(f"\nDONE  {len(made)} reels in {outdir}")
    for m in made:
        print(f"  {m}")
    if args.open and made:
        subprocess.run(["open", str(made[0].parent)], check=False)


if __name__ == "__main__":
    main()
