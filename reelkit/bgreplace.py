"""Replace a recording's background with a looping background video.

Cuts the person out of each source frame (rembg u2net_human_seg) and composites
onto a background video that loops to cover the full length. Streams frames
straight into ffmpeg (no giant PNG dump), then muxes the original audio back.

Outputs ONE file: the finished composite. It never writes a separate
background-only file -- an earlier version did, and opening that by mistake
looked like "a blank video with no person in it".
"""
import subprocess
import time

import cv2
import numpy as np
from PIL import Image

from .transcribe import ffmpeg_path


def _bg_frames(bg_video, need, size):
    """Load background frames (looped/truncated to exactly `need` frames)."""
    W, H = size
    cap = cv2.VideoCapture(str(bg_video))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        f = cv2.resize(f, (W, H))
        frames.append(Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)))
    cap.release()
    if not frames:
        raise RuntimeError(f"no frames in background {bg_video}")
    # loop to cover the recording; ping-pong so the loop seam is less visible
    seq = frames + frames[-2:0:-1]
    return [seq[i % len(seq)] for i in range(need)]


def replace(recording, bg_video, out_path, size=(1080, 1920), on_progress=None):
    """Composite `recording` onto looping `bg_video`. Returns out_path.

    Only paid step is upstream (generating the bg); this is all local/free.
    """
    from rembg import remove, new_session
    W, H = size
    FF = ffmpeg_path()

    cap = cv2.VideoCapture(str(recording))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

    bgs = _bg_frames(bg_video, total, size)
    sess = new_session("u2net_human_seg")

    silent = str(out_path) + ".silent.mp4"
    enc = subprocess.Popen(
        [FF, "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
         "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t0 = time.time(); i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if rgb.size != (W, H):
            rgb = rgb.resize((W, H), Image.LANCZOS)
        fg = remove(rgb, session=sess)          # RGBA cutout
        comp = bgs[i].copy(); comp.paste(fg, (0, 0), fg)
        enc.stdin.write(cv2.cvtColor(np.asarray(comp), cv2.COLOR_RGB2BGR).tobytes())
        i += 1
        if on_progress and i % 60 == 0:
            rate = i / (time.time() - t0)
            on_progress(i, total, rate, (total - i) / rate)
    cap.release()
    enc.stdin.close(); enc.wait()

    # mux original audio into the single output file
    subprocess.run([FF, "-y", "-i", silent, "-i", str(recording),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-shortest", str(out_path)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["rm", "-f", silent])
    return out_path
