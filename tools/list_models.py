#!/usr/bin/env python3
"""What video models are available, what they cost, what they can do.

    python3 tools/list_models.py [--duration 15]

Pricing is read live from OpenRouter -- do not trust hardcoded numbers.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.openrouter import price_per_second, video_models  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=15, help="cost is quoted for this length")
    args = ap.parse_args()

    rows = []
    for m in video_models():
        rate = price_per_second(m, audio=True)
        rows.append({
            "id": m["id"],
            "rate": rate,
            "cost": rate * args.duration if rate else None,
            "audio": m.get("generate_audio"),
            "max_dur": max(m.get("supported_durations") or [0]),
            "vertical": "9:16" in (m.get("supported_aspect_ratios") or []),
        })
    rows.sort(key=lambda r: (r["cost"] is None, r["cost"] or 0))

    print(f"{'model':<32}{'$/s':>8}{f'{args.duration}s':>8}{'audio':>7}{'maxlen':>8}{'9:16':>6}")
    print("-" * 69)
    for r in rows:
        rate = f"{r['rate']:.4f}" if r["rate"] else "-"
        cost = f"${r['cost']:.2f}" if r["cost"] else "-"
        audio = {True: "yes", False: "no", None: "n/a"}.get(r["audio"], "?")
        fits = "" if r["max_dur"] >= args.duration else "  (too short)"
        print(f"{r['id']:<32}{rate:>8}{cost:>8}{audio:>7}{r['max_dur']:>8}"
              f"{'yes' if r['vertical'] else 'no':>6}{fits}")

    print("\nNotes from testing (2026-07-15):")
    print("  google/veo-*      filters clear photos of real people -- unusable for face reels")
    print("  kwaivgi/kling-*   accepts real faces, 15s + audio in one clip")


if __name__ == "__main__":
    main()
