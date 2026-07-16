"""Thin OpenRouter client for video generation and chat completions."""
import base64
import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import load_env

BASE = "https://openrouter.ai/api/v1"


class OpenRouterError(RuntimeError):
    pass


def _request(url, key, payload=None, method=None, timeout=120):
    headers = {"Authorization": f"Bearer {key}"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method=method or ("POST" if payload is not None else "GET"),
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise OpenRouterError(f"HTTP {e.code} from {url}: {e.read().decode()[:1000]}") from None


def get_json(url, key=None, payload=None):
    return json.load(_request(url, key or load_env(), payload))


def photo_to_data_uri(path):
    p = Path(path)
    if not p.is_file():
        raise OpenRouterError(f"photo not found: {p}")
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def video_models(key=None):
    d = get_json(f"{BASE}/videos/models", key)
    return d.get("data", d)


def model_meta(model_id, key=None):
    meta = next((m for m in video_models(key) if m.get("id") == model_id), None)
    if not meta:
        raise OpenRouterError(f"unknown video model: {model_id}")
    return meta


def price_per_second(meta, audio=True, resolution="720p"):
    """Best-effort rate lookup. SKU naming is inconsistent across providers."""
    sku = meta.get("pricing_skus") or {}
    for candidate in (
        f"duration_seconds_with_audio_{resolution}" if audio else f"duration_seconds_without_audio_{resolution}",
        "duration_seconds_with_audio" if audio else "duration_seconds_without_audio",
        f"image_to_video_duration_seconds_{resolution}",
        f"duration_seconds_{resolution}",
        "duration_seconds",
    ):
        if candidate and sku.get(candidate):
            return float(sku[candidate])
    return None


def validate(meta, duration, resolution, aspect):
    """Check a request against the model's advertised capabilities."""
    problems = []
    for field, val, allowed in [
        ("duration", duration, meta.get("supported_durations")),
        ("resolution", resolution, meta.get("supported_resolutions")),
        ("aspect_ratio", aspect, meta.get("supported_aspect_ratios")),
    ]:
        if allowed and val not in allowed:
            problems.append(f"{field}={val!r} not supported (allowed: {allowed})")
    return problems


def generate_video(model, prompt, photo=None, duration=15, resolution="720p",
                   aspect="9:16", audio=True, key=None, on_status=None, timeout=900):
    """Submit a video job, poll to completion, return (bytes, usage).

    Raises OpenRouterError on refusal, failure, or timeout.
    """
    key = key or load_env()
    payload = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "aspect_ratio": aspect,
        "generate_audio": audio,
    }
    if photo:
        payload["frame_images"] = [{
            "type": "image_url",
            "image_url": {"url": photo_to_data_uri(photo)},
            "frame_type": "first_frame",
        }]

    job = get_json(f"{BASE}/videos", key, payload)
    poll_url = job.get("polling_url") or f"{BASE}/videos/{job['id']}"

    started = time.time()
    while True:
        time.sleep(10)
        st = get_json(poll_url, key)
        status = st.get("status")
        if on_status:
            on_status(status, time.time() - started)

        if status == "completed":
            urls = st.get("unsigned_urls") or []
            if not urls:
                # The job record is eventually consistent -- status can flip to
                # completed a beat before the URLs land. Give it one retry.
                time.sleep(5)
                st = get_json(poll_url, key)
                urls = st.get("unsigned_urls") or []
            if not urls:
                raise OpenRouterError(f"completed but no video URL: {json.dumps(st)[:500]}")
            # Download URLs are OpenRouter API endpoints -- they need auth.
            data = _request(urls[0], key, timeout=300).read()
            return data, st.get("usage", {})

        if status in ("failed", "cancelled"):
            raise OpenRouterError(st.get("error") or f"job {status}")

        if time.time() - started > timeout:
            raise OpenRouterError(f"timed out after {timeout}s (job {job.get('id')})")


def chat(model, messages, key=None, temperature=0.7):
    d = get_json(f"{BASE}/chat/completions", key, {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    })
    return d["choices"][0]["message"]["content"]
