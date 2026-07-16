#!/usr/bin/env python3
"""Turn raw content into a reel script.

    python3 tools/write_script.py --pillar ai --duration 30 --content "..."
    python3 tools/write_script.py --pillar stocks --file notes.txt --save

Costs a fraction of a cent. Writes JSON to output/scripts/ with --save.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.pillars import PILLARS  # noqa: E402
from reelkit.script import DEFAULT_MODEL, write_script  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillar", required=True, choices=list(PILLARS))
    ap.add_argument("--content", help="raw notes/article text")
    ap.add_argument("--file", help="read raw content from a file instead")
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    if not args.content and not args.file:
        ap.error("need --content or --file")
    raw = args.content or Path(args.file).read_text()

    out = write_script(raw, args.pillar, duration=args.duration, model=args.model)

    print(f"\nHOOK   {out['hook']}\n")
    print(out["script"])
    print(f"\nCTA    {out['cta']}")
    print(f"\nON-SCREEN")
    for t in out.get("on_screen_text", []):
        print(f"  - {t}")
    flag = "  OVER BUDGET -- will get cut off" if out["over_budget"] else ""
    print(f"\n{out['word_count']} words / {out['budget']} budget ({args.duration}s){flag}")

    if args.save:
        d = OUTPUT_DIR / "scripts"
        d.mkdir(parents=True, exist_ok=True)
        n = len(list(d.glob(f"{args.pillar}_*.json"))) + 1
        p = d / f"{args.pillar}_{n:03d}.json"
        p.write_text(json.dumps(out, indent=2))
        print(f"saved {p}")


if __name__ == "__main__":
    main()
