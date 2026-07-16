"""Text-to-speech for faceless reels. Free, local-ish, no per-use cost.

edge-tts uses Microsoft's neural voices over a free endpoint -- good quality,
including Indian English (en-IN-PrabhatNeural, male). macOS `say` is the
zero-dependency fallback if edge-tts isn't installed or the network is down;
it's robotic but always works.

Neither spends money. For top-tier voice, ElevenLabs is the paid upgrade
(billed per character, outside the token budget) -- wire it in later if the
free voice proves to be the thing holding a reel back.
"""
import subprocess
import sys

VOICE = "en-IN-PrabhatNeural"   # male Indian English


def synthesize(text, out_path, voice=VOICE):
    """Write speech for `text` to out_path (mp3). Returns the path.

    Tries edge-tts first, falls back to macOS `say`. Raises if neither works.
    """
    out_path = str(out_path)
    try:
        import edge_tts  # noqa: F401
        # Run as a module so we don't depend on the console script being on PATH.
        r = subprocess.run(
            [sys.executable, "-m", "edge_tts", "--voice", voice,
             "--text", text, "--write-media", out_path],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            return out_path
        print(f"edge-tts failed, falling back to `say`: {r.stderr[-200:]}",
              file=sys.stderr)
    except ImportError:
        print("edge-tts not installed, using macOS `say` (robotic). "
              "pip install edge-tts for a better voice.", file=sys.stderr)

    # Fallback: macOS say -> aiff -> mp3 via ffmpeg
    from .transcribe import ffmpeg_path
    aiff = out_path.rsplit(".", 1)[0] + ".aiff"
    if subprocess.run(["say", "-o", aiff, text]).returncode != 0:
        raise RuntimeError("both edge-tts and macOS `say` failed")
    subprocess.run([ffmpeg_path(), "-y", "-i", aiff, out_path],
                   capture_output=True)
    return out_path


def duration_of(audio_path):
    """Seconds of audio, read from the container via ffmpeg."""
    from .transcribe import ffmpeg_path
    r = subprocess.run([ffmpeg_path(), "-i", str(audio_path)],
                       capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"could not read duration of {audio_path}")
