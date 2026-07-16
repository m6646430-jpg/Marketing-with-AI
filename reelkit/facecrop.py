"""Face-aware 9:16 crop for landscape footage.

When you record wide (16:9) and clip it to vertical, a naive center crop can
cut your head off if you're not dead-center. This samples frames, finds where
the face actually sits, and computes one stable crop window that keeps it in
frame -- stable on purpose, because a window that jitters per-frame looks worse
than a slightly off-center static one.

Uses OpenCV 5's FaceDetectorYN (a small DNN). The model (~350KB) downloads once
to output/.cache. Everything degrades to a center crop (0.5) if the model can't
be fetched or no face is found -- the pipeline never fails on this step.
"""
import sys
import urllib.request
from statistics import median

import cv2

from .config import OUTPUT_DIR

TARGET_AR = 9 / 16

YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
             "face_detection_yunet/face_detection_yunet_2023mar.onnx")
YUNET_PATH = OUTPUT_DIR / ".cache" / "face_detection_yunet_2023mar.onnx"


def _detector(size):
    """FaceDetectorYN for a given input (w, h). Returns None if unavailable."""
    if not YUNET_PATH.is_file():
        YUNET_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            print("fetching face-detection model (once, ~350KB)...", file=sys.stderr)
            urllib.request.urlretrieve(YUNET_URL, YUNET_PATH)
        except Exception as e:
            print(f"couldn't fetch face model ({e}); using center crop", file=sys.stderr)
            return None
    try:
        return cv2.FaceDetectorYN_create(str(YUNET_PATH), "", size)
    except Exception as e:
        print(f"face detector init failed ({e}); using center crop", file=sys.stderr)
        return None


def face_center_x(video_path, samples=40):
    """Median horizontal face position across sampled frames, as a 0..1 fraction.

    Returns 0.5 (center) if the model is unavailable or no faces are found, so
    the crop degrades to a plain center crop rather than failing.
    """
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1

    det = _detector((width, height))
    if det is None:
        cap.release()
        return 0.5

    step = max(1, total // samples)
    centers = []
    for f in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, frame = cap.read()
        if not ok:
            continue
        n, faces = det.detect(frame)
        if faces is not None and len(faces):
            # faces[i] = [x, y, w, h, ...landmarks..., score]; pick the biggest
            x, y, w, h = max(faces, key=lambda b: b[2] * b[3])[:4]
            centers.append((x + w / 2) / width)
    cap.release()

    return median(centers) if centers else 0.5


def crop_filter(video_path, samples=40):
    """Build an ffmpeg -vf crop expression for a face-centered 9:16 window.

    Returns the filter string, e.g. "crop=ih*9/16:ih:x=...:0", clamped so the
    window never runs off the frame edge.
    """
    cx = face_center_x(video_path, samples)
    cap = cv2.VideoCapture(str(video_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1
    cap.release()

    crop_w = min(w, int(h * TARGET_AR))
    x = int(cx * w - crop_w / 2)
    x = max(0, min(x, w - crop_w))  # clamp inside the frame
    return f"crop={crop_w}:{h}:{x}:0", {"face_center": round(cx, 3), "crop_w": crop_w, "x": x}
