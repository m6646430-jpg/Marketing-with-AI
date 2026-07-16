"""Upscale a reel to 1080p. Zero new dependencies.

Kling outputs 720p; Instagram serves up to 1080p vertical, and sharper video
reads as higher production value. This uses ffmpeg's lanczos scaler plus a
light unsharp pass -- free, already installed, fast, and a real improvement on
720p source.

It is NOT the neural upscaler from the reference repo (Real-ESRGAN + GFPGAN).
Those give better faces but need PyTorch + model weights (~400MB) and are
fragile on Python 3.9 / Apple Silicon. If you ever set that environment up,
`neural_upscale` is left as the seam to plug it into -- same signature, and
clip_video.py will pick it up. Until then ffmpeg is the honest default.
"""
import subprocess

from .transcribe import ffmpeg_path

TARGET_1080 = (1080, 1920)


def ffmpeg_upscale(src, out, size=TARGET_1080, sharpen=0.8):
    """720p -> 1080p with lanczos + a gentle unsharp. Keeps audio untouched."""
    w, h = size
    vf = (
        f"scale={w}:{h}:flags=lanczos,"
        f"unsharp=5:5:{sharpen}:5:5:0.0,"
        f"format=yuv420p"
    )
    subprocess.run([
        ffmpeg_path(), "-y", "-i", str(src), "-vf", vf,
        "-c:a", "copy", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        str(out),
    ], capture_output=True, check=True)
    return out


def neural_upscale(src, out, size=TARGET_1080):
    """Seam for Real-ESRGAN/GFPGAN. Not implemented -- needs the torch stack.

    Left here deliberately so clip_video.py's --neural flag has somewhere to go
    the day that environment exists, without reworking the call sites.
    """
    raise NotImplementedError(
        "neural upscaling needs Real-ESRGAN + GFPGAN (PyTorch + weights). "
        "Not set up on this machine. Use ffmpeg_upscale, or install the torch "
        "stack and implement this seam."
    )


def upscale(src, out, size=TARGET_1080, neural=False):
    return neural_upscale(src, out, size) if neural else ffmpeg_upscale(src, out, size)
