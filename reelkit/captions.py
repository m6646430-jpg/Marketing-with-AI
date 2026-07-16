"""Word-by-word animated captions in ASS format.

Most reels are watched muted, so captions aren't decoration -- they're the
difference between watched and scrolled. The style that works is a short
chunk of words on screen with the *current* word highlighted as it's spoken,
not a static block of text sitting there for four seconds.

ASS does this natively and ffmpeg burns it in one pass. No extra dependency,
no per-frame rendering.
"""

# ASS colours are &HAABBGGRR -- BGR order, not RGB. Getting this backwards
# silently swaps red and blue, which looks like a font bug.
WHITE = "&H00FFFFFF"
YELLOW = "&H0000FFFF"
BLACK = "&H00000000"

DEFAULT_STYLE = {
    "font": "Arial",
    "size": 58,
    "base_colour": WHITE,
    "highlight_colour": YELLOW,
    "outline": 4,       # heavy outline keeps text legible on any background
    "shadow": 2,
    "margin_v": 340,    # up from the bottom -- clear of the UI chrome
    "words_per_chunk": 4,
}


def _ts(seconds):
    """ASS timestamp: H:MM:SS.cc (centiseconds, single-digit hour)."""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def chunk_words(words, per_chunk=4):
    """Group the word stream into caption-sized chunks.

    Breaks on sentence-ending punctuation as well as length, so a chunk never
    straddles two sentences -- that reads badly even when the timing is right.
    """
    chunks, current = [], []
    for w in words:
        current.append(w)
        ends_sentence = w["word"].rstrip().endswith((".", "?", "!"))
        if len(current) >= per_chunk or ends_sentence:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def build_ass(words, style=None, play_res=(720, 1280)):
    """Render a word stream as an ASS subtitle file.

    Emits one event per word: the whole chunk is shown, with the active word
    recoloured. That's what produces the word-by-word "pop" without any
    frame-level animation work.
    """
    st = {**DEFAULT_STYLE, **(style or {})}
    w_res, h_res = play_res

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w_res}
PlayResY: {h_res}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{st['font']},{st['size']},{st['base_colour']},{st['highlight_colour']},{BLACK},{BLACK},-1,0,0,0,100,100,0,0,1,{st['outline']},{st['shadow']},2,40,40,{st['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = []
    for chunk in chunk_words(words, st["words_per_chunk"]):
        for i, active in enumerate(chunk):
            parts = []
            for j, w in enumerate(chunk):
                text = w["word"].strip().replace("{", "").replace("}", "")
                if j == i:
                    parts.append(f"{{\\c{st['highlight_colour']}}}{text}{{\\c{st['base_colour']}}}")
                else:
                    parts.append(text)
            body = " ".join(parts)

            start = active["start"]
            # Hold the last word of a chunk until the next word actually starts,
            # otherwise the caption blinks out during natural pauses.
            end = chunk[i + 1]["start"] if i + 1 < len(chunk) else active["end"]
            if end <= start:
                end = start + 0.15

            lines.append(
                f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{body}"
            )

    return head + "\n".join(lines) + "\n"


def build_srt(words, per_chunk=4):
    """Plain SRT -- no highlighting. For platforms that want a subtitle file
    rather than burned-in text (YouTube accepts these for accessibility)."""
    out = []
    for n, chunk in enumerate(chunk_words(words, per_chunk), 1):
        start, end = chunk[0]["start"], chunk[-1]["end"]

        def srt_ts(s):
            h = int(s // 3600); m = int((s % 3600) // 60)
            sec = int(s % 60); ms = int((s - int(s)) * 1000)
            return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

        text = " ".join(w["word"].strip() for w in chunk)
        out.append(f"{n}\n{srt_ts(start)} --> {srt_ts(end)}\n{text}\n")
    return "\n".join(out)
