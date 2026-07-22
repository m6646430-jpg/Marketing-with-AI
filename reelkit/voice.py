"""Voice synthesis: Voicebox (local, cloned voice) with edge-tts fallback.

Voicebox (https://github.com/jamiepine/voicebox) runs a local REST API at
127.0.0.1:17493 and can speak in a *cloned* voice, MLX-accelerated on Apple
Silicon, fully offline. If the app is running and a profile exists, faceless
reels get narrated in your real voice instead of a generic TTS.

If Voicebox isn't running, this falls back to edge-tts (see tts.py) so the
pipeline never breaks.

Honest limitation, verified against Voicebox's API on 2026-07-22: its TTS
languages are zh/en/ja/ko/de/fr/ru/pt/es/it/he/ar/da/el/fi/hi/ms/nl/no/pl/sv/
sw/tr -- NO Telugu (te). Use it for English reels; Telugu narration must come
from your own recording.
"""
import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:17493"
# Voicebox's supported TTS languages (from backend/models.py GenerationRequest).
SUPPORTED = {"zh", "en", "ja", "ko", "de", "fr", "ru", "pt", "es", "it", "he",
             "ar", "da", "el", "fi", "hi", "ms", "nl", "no", "pl", "sv", "sw", "tr"}


class VoiceboxError(RuntimeError):
    pass


def _req(path, payload=None, timeout=60):
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if payload is not None else "GET")
    return urllib.request.urlopen(req, timeout=timeout)


def is_running():
    """True if the Voicebox app's local API is up."""
    try:
        _req("/health", timeout=3)
        return True
    except (urllib.error.URLError, OSError):
        return False


def list_profiles():
    """Voice profiles available (created by cloning a voice in the app).
    Returns [] if none or the app is down."""
    try:
        # channels carry voices/profiles in Voicebox's model
        d = json.load(_req("/channels"))
        out = []
        for ch in (d if isinstance(d, list) else d.get("channels", [])):
            for v in ch.get("voices", []) or []:
                out.append({"id": v.get("id"), "name": v.get("name"),
                            "channel": ch.get("name")})
        return out
    except Exception:
        return []


def synthesize_voicebox(text, out_path, profile=None, language="en",
                        engine="qwen", timeout=300):
    """Generate speech via Voicebox in a cloned voice. Returns out_path.

    profile: voice profile name or id. If None, Voicebox uses its default/bound
    profile. Raises VoiceboxError if the app is down or language unsupported.
    """
    if not is_running():
        raise VoiceboxError("Voicebox app not running (start it; API expected at :17493)")
    if language not in SUPPORTED:
        raise VoiceboxError(f"Voicebox has no TTS for language {language!r} "
                            f"(supported: {sorted(SUPPORTED)})")

    # /speak is the simple REST wrapper (accepts a profile *name*); prefer it.
    # It returns immediately with status "generating"; poll /history/{id} for
    # completion (the /generate/{id}/status route is an SSE stream, not JSON).
    resp = json.load(_req("/speak", {
        "text": text, "profile": profile, "engine": engine,
    }))
    gen_id = resp.get("id")
    if not gen_id:
        raise VoiceboxError(f"no generation id from /speak: {resp}")

    started = time.time()
    while True:
        st = json.load(_req(f"/history/{gen_id}"))
        status = st.get("status")
        if status == "completed" and st.get("audio_path"):
            break
        if status in ("failed", "error", "cancelled"):
            raise VoiceboxError(f"Voicebox generation {status}: {st.get('error')}")
        if time.time() - started > timeout:
            raise VoiceboxError(f"Voicebox generation timed out (first run downloads "
                                f"the TTS model, which can be slow)")
        time.sleep(2)

    # Fetch the rendered audio bytes and write them out.
    audio = _req(f"/audio/{gen_id}", timeout=120).read()
    with open(out_path, "wb") as f:
        f.write(audio)
    return str(out_path)


def synthesize(text, out_path, profile=None, language="en", engine="qwen",
               prefer="voicebox"):
    """Best-available voice: Voicebox if up (cloned voice), else edge-tts.

    Returns (out_path, backend_used). Never raises for a missing Voicebox --
    it degrades to edge-tts so the pipeline always produces audio.
    """
    if prefer == "voicebox" and language in SUPPORTED and is_running():
        try:
            return synthesize_voicebox(text, out_path, profile, language, engine), "voicebox"
        except VoiceboxError:
            pass  # fall through to edge-tts
    from .tts import synthesize as edge_synth
    return edge_synth(text, out_path), "edge-tts"
