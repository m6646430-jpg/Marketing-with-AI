"""Instagram Reels publishing via the Graph API.

This is the last mile: an approved local reel -> a live post. It is NOT
unattended. The tool that uses it (tools/publish.py) requires an explicit
--confirm, and you run it yourself. AI-paraphrased market and news content
posting itself under your name is exactly the failure to avoid.

Prerequisites you must set up once (none of this exists yet):
  1. An Instagram Business or Creator account, linked to a Facebook Page.
  2. A Meta developer app with the instagram_content_publish permission.
  3. A long-lived access token and your IG user id, in .env:
        IG_ACCESS_TOKEN=...
        IG_USER_ID=...
  4. Public hosting for the mp4 -- the Graph API pulls from a URL, it will
     NOT accept a local file. Cloudflare R2, S3, or Cloudinary all work.

Until those exist, publish.py runs in --dry-run only and posts nothing.

The publish flow is two steps: create a media container from the video URL,
poll until Instagram finishes ingesting it, then publish the container.
"""
import json
import time
import urllib.parse
import urllib.request

from .config import load_env

GRAPH = "https://graph.facebook.com/v21.0"


class InstagramError(RuntimeError):
    pass


def _post(path, params):
    data = urllib.parse.urlencode(params).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(f"{GRAPH}/{path}", data=data), timeout=60)
        return json.load(r)
    except urllib.error.HTTPError as e:
        raise InstagramError(f"Graph API {e.code}: {e.read().decode()[:600]}") from None


def _get(path, params):
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        return json.load(urllib.request.urlopen(url, timeout=60))
    except urllib.error.HTTPError as e:
        raise InstagramError(f"Graph API {e.code}: {e.read().decode()[:600]}") from None


def credentials():
    """(user_id, token) from .env. Raises if unset -- so publish.py can tell
    the user what to configure rather than failing cryptically."""
    return load_env("IG_USER_ID"), load_env("IG_ACCESS_TOKEN")


def create_reel_container(video_url, caption, user_id=None, token=None):
    """Step 1: hand Instagram the public video URL. Returns a container id."""
    user_id = user_id or load_env("IG_USER_ID")
    token = token or load_env("IG_ACCESS_TOKEN")
    out = _post(f"{user_id}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": token,
    })
    if "id" not in out:
        raise InstagramError(f"no container id: {out}")
    return out["id"]


def wait_until_ready(container_id, token=None, timeout=300, on_status=None):
    """Step 2: poll the container until Instagram finishes ingesting the video.

    Publishing before status_code == FINISHED fails, so this is not optional.
    """
    token = token or load_env("IG_ACCESS_TOKEN")
    started = time.time()
    while True:
        st = _get(container_id, {"fields": "status_code,status", "access_token": token})
        code = st.get("status_code")
        if on_status:
            on_status(code, time.time() - started)
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise InstagramError(f"container failed to process: {st}")
        if time.time() - started > timeout:
            raise InstagramError(f"container not ready after {timeout}s (last: {code})")
        time.sleep(5)


def publish_container(container_id, user_id=None, token=None):
    """Step 3: go live. Returns the published media id."""
    user_id = user_id or load_env("IG_USER_ID")
    token = token or load_env("IG_ACCESS_TOKEN")
    out = _post(f"{user_id}/media_publish", {
        "creation_id": container_id,
        "access_token": token,
    })
    if "id" not in out:
        raise InstagramError(f"publish failed: {out}")
    return out["id"]
