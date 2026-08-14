#!/usr/bin/env python3
"""Stage 1: scan run outputs for candidate degenerate-loop regions.

A candidate is a chunk of 4-200 chars repeated >=3 times back-to-back
spanning >=60 chars. Thresholds are deliberately loose -- the LLM judge
(judge_escapes.py) filters false positives and marks the escape point.

Usage:
    python3 analysis/loop_escape/find_loop_candidates.py \
        [--runs-root runs] [--out analysis/loop_escape/out/candidates.jsonl] \
        [--include aime24_fresh humaneval_fresh ...]

Output: one JSON row per candidate loop region:
    {case_key, arm, char_start, char_end, unit, reps, span, output_len}
case_key/arm match the viewer's addressing (viewer/server.py).
"""
import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# chunk of 4-200 chars, repeated at least 3x consecutively (1 + {2,})
LOOP_RE = re.compile(r"(.{4,200}?)(\1){2,}", re.S)
MIN_SPAN = 60


def trivial(unit):
    """Filler like '----', '   ', '9999' -- not a semantic loop."""
    return len(set(unit.strip())) <= 2


def find_candidates(text):
    out = []
    for m in LOOP_RE.finditer(text):
        unit = m.group(1)
        span = m.end() - m.start()
        if span < MIN_SPAN or trivial(unit):
            continue
        out.append({
            "char_start": m.start(),
            "char_end": m.end(),
            "unit": unit,
            "reps": span // len(unit),
            "span": span,
        })
    # merge overlapping/adjacent regions (keep the longest span's unit)
    out.sort(key=lambda c: c["char_start"])
    merged = []
    for c in out:
        if merged and c["char_start"] <= merged[-1]["char_end"]:
            prev = merged[-1]
            if c["span"] > prev["span"]:
                prev["unit"], prev["reps"], prev["span"] = c["unit"], c["reps"], c["span"]
            prev["char_end"] = max(prev["char_end"], c["char_end"])
        else:
            merged.append(c)
    return merged


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-root", default=os.path.join(REPO_ROOT, "runs"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "out", "candidates.jsonl"))
    ap.add_argument("--include", nargs="*", default=None,
                    help="only scan these top-level benchmark dirs")
    args = ap.parse_args()

    runs_root = os.path.abspath(args.runs_root)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    n_files = n_hits = 0
    with open(args.out, "w") as f:
        for dirpath, dirnames, filenames in os.walk(runs_root):
            if "output.txt" not in filenames:
                continue
            dirnames[:] = []
            rel = os.path.relpath(dirpath, runs_root)
            if args.include and rel.split(os.sep)[0] not in args.include:
                continue
            case_key, arm = os.path.split(rel)
            with open(os.path.join(dirpath, "output.txt"), errors="replace") as fh:
                text = fh.read()
            n_files += 1
            for c in find_candidates(text):
                c.update(case_key=case_key, arm=arm, output_len=len(text))
                f.write(json.dumps(c) + "\n")
                n_hits += 1

    print(f"scanned {n_files} outputs, wrote {n_hits} candidates -> {args.out}")


if __name__ == "__main__":
    main()
