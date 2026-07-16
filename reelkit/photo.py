"""Prepare a photo as a talking-head first frame.

The models regenerate the pixels, so sharpness matters less than pose and
framing: face front-on, filling a good share of a 9:16 frame.
"""
from pathlib import Path

from PIL import Image

TARGET = (720, 1280)  # 9:16 at 720p


def crop_9x16(src, out, face_center_x=None, head_top=None, height=None):
    """Crop to a 9:16 head-and-shoulders frame and scale to 720x1280.

    Coordinates are in source pixels. Defaults assume the head is horizontally
    centered in the upper third -- true for most standing phone shots, but
    check the output rather than trusting it.
    """
    im = Image.open(src)
    W, H = im.size

    cx = face_center_x if face_center_x is not None else W // 2
    top = head_top if head_top is not None else int(H * 0.22)
    h = height if height is not None else int(H * 0.39)
    w = int(h * 9 / 16)

    left = max(0, min(cx - w // 2, W - w))
    top = max(0, min(top, H - h))
    box = (left, top, left + w, top + h)

    crop = im.crop(box)
    up = crop.resize(TARGET, Image.LANCZOS)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    up.save(out, quality=95)

    return {
        "source_size": (W, H),
        "crop_box": box,
        "crop_size": crop.size,
        "output": str(out),
        "upscale": round(TARGET[0] / crop.size[0], 2),
    }
