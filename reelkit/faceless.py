"""Faceless reel assembly: multi-scene script -> images -> Ken Burns video.

The cheap path for the reach pillars (AI, stocks) -- 7 of every 10 posts. No
Kling clip, so no $1.89: a faceless reel is a handful of generated images with
a Ken Burns zoom and a free voiceover. Cost is just the images (a few cents),
not two dollars.

Scene shape: {"narration": str, "image_prompt": str}. Narration is spoken;
image_prompt drives one still per scene. Word-level caption timings come from
running whisper over the finished voiceover -- the same caption pipeline the
face reels use.
"""
import json
import subprocess
from pathlib import Path

from .openrouter import chat
from .pillars import PILLARS, words_for_duration
from .transcribe import ffmpeg_path

SCENE_SYSTEM = """You script short faceless vertical videos for Mahesh's page \
(AI + markets + careers, funnelling to DriftAI). Faceless means narration over \
images -- no presenter on screen.

Return ONLY valid JSON, no markdown fence:
{
  "hook": "first spoken line, under 2 seconds, must stop a scroll",
  "cta": "closing call to action",
  "scenes": [
    {"narration": "one or two spoken sentences",
     "image_prompt": "a vivid, concrete visual to show while this is narrated. \
Describe it cinematically: subject, composition, lighting, mood, depth. Prefer \
real-world scenes, objects, and metaphors over UI/screens/charts -- AI image \
models render garbled fake text on those. Absolutely NO text, letters, numbers, \
words, logos, or watermarks anywhere in the image. Vertical 9:16."}
  ]
}"""


def write_scene_script(content, pillar, duration=30, n_scenes=4, model=None, key=None):
    """Raw content -> a scene-by-scene faceless script (dict, see SCENE_SYSTEM)."""
    if pillar not in PILLARS:
        raise ValueError(f"unknown pillar {pillar!r}")
    p = PILLARS[pillar]
    model = model or p.get("model")
    budget = words_for_duration(duration)

    prompt = f"""Pillar: {p['name']}
Angle: {p['angle']}
{"Include this disclaimer verbatim in the narration: " + p['disclaimer'] if p.get('disclaimer') else ""}
Total spoken budget: {budget} words across ~{n_scenes} scenes ({duration}s).
Each scene: 1-2 sentences of narration + one concrete image to show.
First scene's narration must open with the hook.

Raw content:
---
{content}
---
Write it."""

    out = chat(model, [
        {"role": "system", "content": SCENE_SYSTEM},
        {"role": "user", "content": prompt},
    ], key=key)

    text = out.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    data = json.loads(text)

    data["pillar"] = pillar
    data["model"] = model
    narration = " ".join(s["narration"] for s in data["scenes"])
    data["word_count"] = len(narration.split())
    data["budget"] = budget
    data["over_budget"] = data["word_count"] > budget
    return data


def ken_burns_scene(image, out, seconds, size=(720, 1280), zoom_to=1.15, fps=30):
    """Render one still as a Ken Burns clip (slow zoom) for `seconds`.

    zoompan wants the frame count; we compute it from duration * fps and ease
    the zoom linearly to zoom_to.
    """
    frames = max(1, int(seconds * fps))
    w, h = size
    # Scale up first so the zoom has pixels to eat, then zoompan, then output size.
    vf = (
        f"scale={w*4}:{h*4}:force_original_aspect_ratio=increase,"
        f"crop={w*4}:{h*4},"
        f"zoompan=z='min(zoom+{(zoom_to-1)/frames:.6f},{zoom_to})':"
        f"d={frames}:s={w}x{h}:fps={fps},"
        f"format=yuv420p"
    )
    subprocess.run([
        ffmpeg_path(), "-y", "-loop", "1", "-i", str(image),
        "-t", f"{seconds:.3f}", "-vf", vf, "-r", str(fps), str(out),
    ], capture_output=True, check=True)
    return out


def concat_clips(clip_paths, out):
    """Concatenate video-only clips (same size/fps) via the concat demuxer."""
    listfile = Path(out).parent / "_concat.txt"
    listfile.write_text("".join(f"file '{Path(c).resolve()}'\n" for c in clip_paths))
    subprocess.run([
        ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c", "copy", str(out),
    ], capture_output=True, check=True)
    listfile.unlink(missing_ok=True)
    return out


def concat_audio(audio_paths, out):
    """Concatenate per-scene audio into one narration track."""
    listfile = Path(out).parent / "_concat_a.txt"
    listfile.write_text("".join(f"file '{Path(a).resolve()}'\n" for a in audio_paths))
    subprocess.run([
        ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c", "copy", str(out),
    ], capture_output=True, check=True)
    listfile.unlink(missing_ok=True)
    return out


def mux(video, audio, out):
    """Combine a video track and an audio track into the final mp4."""
    subprocess.run([
        ffmpeg_path(), "-y", "-i", str(video), "-i", str(audio),
        "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
    ], capture_output=True, check=True)
    return out
