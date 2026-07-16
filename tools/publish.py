#!/usr/bin/env python3
"""Publish an approved reel to Instagram. You run this; it is not automatic.

    # see exactly what would post -- always do this first
    python3 tools/publish.py --video-url https://cdn.example.com/reel.mp4 \
        --caption "..." --dry-run

    # actually post (requires --confirm AND typing yes)
    python3 tools/publish.py --video-url https://cdn.example.com/reel.mp4 \
        --caption "..." --confirm

Needs Instagram credentials in .env and the video hosted at a PUBLIC url --
the Graph API pulls from a URL, not a local file. See reelkit/instagram.py for
the one-time Meta setup. Until that's done, only --dry-run works.

There is no scheduling and no unattended posting here on purpose: a human
approves every post. That is the guardrail against AI-paraphrased market or
news content going live under your name with a mistake in it.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.instagram import (InstagramError, create_reel_container,  # noqa: E402
                               credentials, publish_container, wait_until_ready)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-url", required=True, help="PUBLIC https url to the mp4")
    ap.add_argument("--caption", required=True)
    ap.add_argument("--confirm", action="store_true", help="required to actually post")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.video_url.startswith("https://"):
        sys.exit("video-url must be a public https URL -- Instagram can't read a local file.")

    print("about to publish to Instagram:")
    print(f"  video:   {args.video_url}")
    print(f"  caption: {args.caption[:120]}{'...' if len(args.caption) > 120 else ''}")

    if args.dry_run or not args.confirm:
        print("\n(dry run -- nothing posted)"
              if args.dry_run else
              "\nnot posted. This publishes PUBLICLY. Re-run with --confirm when ready.")
        return

    # credentials check with a helpful message rather than a stack trace
    try:
        uid, _ = credentials()
    except SystemExit:
        sys.exit("Instagram not configured. Set IG_USER_ID and IG_ACCESS_TOKEN in "
                 ".env (see reelkit/instagram.py for the Meta setup).")

    # final human gate -- typed, not just a flag
    ans = input('\nType "yes" to post this publicly now: ').strip().lower()
    if ans != "yes":
        sys.exit("aborted -- nothing posted.")

    try:
        print("creating media container...", file=sys.stderr)
        cid = create_reel_container(args.video_url, args.caption, user_id=uid)
        print(f"container {cid}; waiting for Instagram to ingest...", file=sys.stderr)
        wait_until_ready(cid, on_status=lambda c, e: print(f"  [{e:4.0f}s] {c}", file=sys.stderr))
        print("publishing...", file=sys.stderr)
        media_id = publish_container(cid, user_id=uid)
    except InstagramError as e:
        sys.exit(f"publish failed: {e}")

    print(f"\nPOSTED. media id {media_id}")


if __name__ == "__main__":
    main()
