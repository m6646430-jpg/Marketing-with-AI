"""Local transcription with word-level timestamps.

Runs faster-whisper on your machine: free, offline, zero tokens. See
models.py for why this beats sending audio to an LLM -- word-level timings
are the thing captions need and the thing an LLM won't reliably give you.

Model sizes (first use downloads the weights, then they're cached):
    tiny    ~75 MB   fastest, sloppy on accents
    base    ~145 MB  the default -- fine for clear speech
    small   ~480 MB  noticeably better on Indian English
    medium  ~1.5 GB  better still, slow on CPU
"""
import shutil

DEFAULT_SIZE = "base"


def ffmpeg_path():
    """A usable ffmpeg, whether from PATH or the pip-bundled binary."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError(
            "ffmpeg not found. Either install it, or:\n"
            "    pip install imageio-ffmpeg"
        )


def transcribe(audio_path, size=DEFAULT_SIZE, language=None, vad=True):
    """Transcribe a media file. Returns (segments, info).

    segments: [{"start", "end", "text", "words": [{"start","end","word"}]}]
    Word timings are what captions.py needs -- without them you only get
    segment-level captions, which read as sluggish on a reel.

    language=None auto-detects. Pass "en" to skip detection when you know.
    vad=True skips silence, which is faster and avoids Whisper hallucinating
    text into dead air -- a real failure mode on long recordings.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper not installed:\n"
            "    pip install faster-whisper"
        )

    model = WhisperModel(size, device="cpu", compute_type="int8")
    seg_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=vad,
    )

    segments = []
    for s in seg_iter:  # generator -- transcription happens as we iterate
        segments.append({
            "start": round(s.start, 3),
            "end": round(s.end, 3),
            "text": s.text.strip(),
            "words": [
                {"start": round(w.start, 3), "end": round(w.end, 3),
                 "word": w.word.strip()}
                for w in (s.words or [])
            ],
        })

    return segments, {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
        "model": size,
    }


def all_words(segments):
    """Flatten to a single word stream -- what caption timing works from."""
    return [w for s in segments for w in s["words"]]


def plain_text(segments):
    return " ".join(s["text"] for s in segments).strip()
