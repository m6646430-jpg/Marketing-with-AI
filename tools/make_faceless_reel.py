#!/usr/bin/env python3
"""A faceless reel: scenes -> images -> Ken Burns + voiceover + captions.

The cheap path for reach pillars (AI, stocks). No Kling clip -> no $1.89: cost
is just the per-scene images (a few cents). Voice and captions are free.

    python3 tools/make_faceless_reel.py --pillar ai \
        --content "how to actually prompt an AI well" --dry-run
    python3 tools/make_faceless_reel.py --pillar stocks \
        --content "what an index fund is" --open

--dry-run writes the scene script and prints the image cost before spending.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.captions import build_ass  # noqa: E402
from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.faceless import (concat_audio, concat_clips, ken_burns_scene,  # noqa: E402
                              mux, write_scene_script)
from reelkit.models import STYLE_PHOTO_CHEAP  # noqa: E402
from reelkit.openrouter import OpenRouterError, edit_image  # noqa: E402
from reelkit.pillars import PILLARS  # noqa: E402
from reelkit.tts import VOICE, duration_of, synthesize  # noqa: E402
from reelkit.transcribe import DEFAULT_SIZE, all_words, ffmpeg_path, transcribe  # noqa: E402

# Faceless images don't carry a real face, so the cheap image model is fine
# here (its face-drift problem is irrelevant when there's no face).
IMAGE_MODEL = STYLE_PHOTO_CHEAP
IMAGE_COST_EST = 0.04  # per image, refined by the actual charge at runtime


def generate_image(prompt, out, model=IMAGE_MODEL):
    """Text-to-image via the /images endpoint (edit_image with no source works
    as pure generation when input_references is empty -- but here we always
    have a prompt, so call the images endpoint directly)."""
    from reelkit.openrouter import BASE, get_json
    import base64
    d = get_json(f"{BASE}/images", None, {
        "model": model,
        "prompt": prompt + (" Cinematic, professional colour grade, shallow depth "
                            "of field, vertical 9:16. No text, letters, numbers, "
                            "logos or watermarks anywhere."),
    })
    items = d.get("data") or []
    if not items or not items[0].get("b64_json"):
        raise OpenRouterError(f"no image: {json.dumps(d)[:300]}")
    Path(out).write_bytes(base64.b64decode(items[0]["b64_json"]))
    return d.get("usage", {}).get("cost")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillar", required=True, choices=list(PILLARS))
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--content", help="raw notes -> scene script (fresh each run)")
    grp.add_argument("--script-file", help="a saved scene-script JSON (reproducible)")
    ap.add_argument("--scenes", type=int, default=4)
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--name")
    ap.add_argument("--margin-v", type=int, default=340)
    ap.add_argument("--max-cost", type=float, default=1.00)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    # ---- scene script (free) ----------------------------------------------
    if args.script_file:
        data = json.loads(Path(args.script_file).read_text())
        print(f"using saved scene script {Path(args.script_file).name}", file=sys.stderr)
    else:
        print(f"writing {args.pillar} scene script (free)...", file=sys.stderr)
        data = write_scene_script(args.content, args.pillar,
                                  duration=args.duration, n_scenes=args.scenes)
    scenes = data["scenes"]
    name = args.name or f"{args.pillar}_faceless"

    print(f"\nHOOK  {data['hook']}")
    for i, s in enumerate(scenes, 1):
        print(f"\nscene {i}")
        print(f"  say:  {s['narration']}")
        print(f"  show: {s['image_prompt']}")
    print(f"\nCTA   {data['cta']}")
    est = len(scenes) * IMAGE_COST_EST
    print(f"\n{len(scenes)} images x ~${IMAGE_COST_EST:.2f} = ~${est:.2f}  (voice + captions free)")
    if data.get("over_budget"):
        print(f"NOTE over budget: {data['word_count']}/{data['budget']} words", file=sys.stderr)

    if args.dry_run:
        print("\n(dry run -- nothing sent, nothing charged)")
        return
    if est > args.max_cost and not args.yes:
        sys.exit(f"est ${est:.2f} exceeds --max-cost ${args.max_cost:.2f}. Pass --yes.")

    work = OUTPUT_DIR / "faceless" / name
    work.mkdir(parents=True, exist_ok=True)

    # ---- per-scene image + voice ------------------------------------------
    clips, audios, spent = [], [], 0.0
    for i, s in enumerate(scenes):
        print(f"[scene {i+1}/{len(scenes)}] image...", file=sys.stderr)
        img = work / f"scene{i}.jpg"
        c = generate_image(s["image_prompt"], img)
        spent += c or 0
        print(f"[scene {i+1}] voice...", file=sys.stderr)
        aud = work / f"scene{i}.mp3"
        synthesize(s["narration"], aud, voice=args.voice)
        dur = duration_of(aud) + 0.25  # small tail so the zoom doesn't snap
        clip = work / f"scene{i}.mp4"
        ken_burns_scene(img, clip, dur)
        clips.append(clip)
        audios.append(aud)

    # ---- stitch -----------------------------------------------------------
    print("stitching...", file=sys.stderr)
    video = work / "_video.mp4"; concat_clips(clips, video)
    audio = work / "_audio.mp3"; concat_audio(audios, audio)
    silent = work / "_muxed.mp4"; mux(video, audio, silent)

    # ---- captions from the voiceover (free) -------------------------------
    print("transcribing voiceover for captions...", file=sys.stderr)
    segments, _ = transcribe(silent, size=DEFAULT_SIZE)
    words = all_words(segments)
    capd = OUTPUT_DIR / "captioned"; capd.mkdir(parents=True, exist_ok=True)
    final = capd / f"{name}_final.mp4"
    if words:
        ass = work / "cc.ass"
        ass.write_text(build_ass(words, style={"margin_v": args.margin_v}))
        esc = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        import subprocess
        r = subprocess.run([ffmpeg_path(), "-y", "-i", str(silent), "-vf", f"ass='{esc}'",
                            "-c:a", "copy", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "20", str(final)], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-800:], file=sys.stderr)
            sys.exit("caption burn failed; silent reel at " + str(silent))
    else:
        final.write_bytes(silent.read_bytes())
        print("no word timings -- reel has no captions", file=sys.stderr)

    print(f"\nDONE  {final}  ({final.stat().st_size/1024/1024:.1f} MB)")
    print(f"cost  ${spent:.3f} (images only)")
    if args.open:
        import subprocess
        subprocess.run(["open", str(final)], check=False)


if __name__ == "__main__":
    main()
