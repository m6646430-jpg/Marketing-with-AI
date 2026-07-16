#!/usr/bin/env python3
"""Batch-generate a set of scripts and save them for review.

Reads a plan file: a JSON list of {"pillar": ..., "content": ..., "duration": ...}.
Writes each script to output/scripts/<batch>/<pillar>_NN.json, ready to feed to
make_reel.py --script-file. Free for reach pillars, fractions of a cent for
Sonnet ones.

    python3 tools/batch_scripts.py --plan week1.json --batch week1
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelkit.config import OUTPUT_DIR  # noqa: E402
from reelkit.script import write_script  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="JSON list of {pillar, content, duration?}")
    ap.add_argument("--batch", default="batch", help="subfolder name under output/scripts/")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    outdir = OUTPUT_DIR / "scripts" / args.batch
    outdir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, item in enumerate(plan, 1):
        pillar = item["pillar"]
        dur = item.get("duration", 30)
        print(f"[{i}/{len(plan)}] {pillar} ...", file=sys.stderr)
        try:
            out = write_script(item["content"], pillar, duration=dur)
        except Exception as e:
            print(f"    FAILED: {e}", file=sys.stderr)
            continue
        p = outdir / f"{pillar}_{i:02d}.json"
        p.write_text(json.dumps(out, indent=2))
        results.append((i, pillar, out, p))

    print(f"\n{'='*70}")
    print(f"batch '{args.batch}': {len(results)}/{len(plan)} scripts -> {outdir}")
    print(f"{'='*70}")
    for i, pillar, out, p in results:
        flag = " [OVER]" if out.get("over_budget") else ""
        print(f"\n#{i:02d} {pillar:8} ({out['word_count']}/{out['budget']}w{flag})  {p.name}")
        print(f"    HOOK: {out['hook']}")
        print(f"    CTA:  {out['cta']}")


if __name__ == "__main__":
    main()
