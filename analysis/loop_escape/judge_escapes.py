#!/usr/bin/env python3
"""Stage 2: LLM judge -- confirm each candidate is a degenerate loop and
quote the escape point (the first text that breaks out of the repetition).

The judge quotes escape text verbatim rather than giving a char offset
(models are unreliable at counting characters); we locate the quote with
str.find and validate it. Requires `pip install anthropic` and credentials
(ANTHROPIC_API_KEY or `ant auth login`).

Usage:
    python3 analysis/loop_escape/judge_escapes.py \
        [--candidates out/candidates.jsonl] [--out out/judged.jsonl] \
        [--model claude-sonnet-5] [--limit N] [--dry-run]

Output rows: candidate fields plus
    {is_degenerate_loop, events: [{escape_char, escape_quote, escape_kind}],
     judge_status}
escape_char is an absolute offset into output.txt, ready for
escape_composition.py / the viewer's /api/trace_at.
"""
import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PRE_CTX = 300    # chars of context before the loop region
POST_CTX = 800   # chars after -- must contain the escape

SCHEMA = {
    "type": "object",
    "properties": {
        "is_degenerate_loop": {
            "type": "boolean",
            "description": "True if the flagged region is pathological repetition "
                           "(the model stuck repeating itself), false if the "
                           "repetition is legitimate (e.g. expected output, "
                           "restating a problem, a table).",
        },
        "onset_quote": {
            "type": "string",
            "description": "VERBATIM quote (20-60 chars, copied exactly) of where "
                           "the degenerate repetition actually begins -- the last "
                           "normal text or the first repeated text at the point the "
                           "model gets stuck. This may be BEFORE the marked "
                           "<<<LOOP_START>>> if the model was already stuck earlier "
                           "(e.g. near-repeats the scanner missed). Empty string if "
                           "not a degenerate loop.",
        },
        "events": {
            "type": "array",
            "description": "One entry per loop->escape event in the window. "
                           "Empty if not a degenerate loop or the text ends "
                           "while still looping.",
            "items": {
                "type": "object",
                "properties": {
                    "escape_quote": {
                        "type": "string",
                        "description": "VERBATIM quote (20-60 chars, copied exactly "
                                       "including whitespace/punctuation) of the first "
                                       "text that breaks out of the repetition.",
                    },
                    "escape_kind": {
                        "type": "string",
                        "enum": ["self_correction", "content_shift",
                                 "completes_computation", "re_enters_loop", "truncation"],
                        "description": "self_correction: 'Wait'/'Actually'/'Anyway'-style "
                                       "interjection; content_shift: moves to new content; "
                                       "completes_computation: the stuttered computation "
                                       "finally resolves; re_enters_loop: brief break then "
                                       "loops again; truncation: output just ends.",
                    },
                },
                "required": ["escape_quote", "escape_kind"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["is_degenerate_loop", "onset_quote", "events"],
    "additionalProperties": False,
}

PROMPT = """You are analyzing raw language-model generation transcripts for degenerate \
loops: places where the model got stuck repeating the same text and then (sometimes) \
escaped.

Below is an excerpt from one transcript. An automatic scanner flagged a repeated \
region inside it. The repeated unit is shown first, then the excerpt with the flagged \
region marked between <<<LOOP_START>>> and <<<LOOP_END>>>.

Flagged repeated unit (may be approximate): {unit!r}

Excerpt:
---
{window}
---

Decide:
1. Is the flagged repetition a DEGENERATE loop (pathological repetition -- the model \
stuck), as opposed to legitimate repetition (expected output of the task, restating \
the problem, a list/table that is naturally repetitive)?
2. If degenerate: quote VERBATIM (copy exactly, 20-60 chars) the ONSET -- the point \
where the degenerate repetition actually begins. This may be earlier than the marked \
<<<LOOP_START>>> if the model was already stuck before the exactly-repeated part \
(e.g. near-repeats with small variations).
3. If degenerate: find every loop->escape event visible in this excerpt. For each, \
quote VERBATIM (copy exactly, 20-60 chars) the first text that breaks the repetition \
-- the point where the output stops repeating and does something else. If the loop \
briefly escapes and re-enters, that is a separate event with kind re_enters_loop. If \
the excerpt ends while still repeating, return no event for it."""


def build_window(text, c):
    a = max(0, c["char_start"] - PRE_CTX)
    b = min(len(text), c["char_end"] + POST_CTX)
    return (a,
            text[a:c["char_start"]] + "<<<LOOP_START>>>"
            + text[c["char_start"]:c["char_end"]] + "<<<LOOP_END>>>"
            + text[c["char_end"]:b])


def locate(quote, text, search_from):
    """Absolute offset of the escape quote in output.txt, searching from the
    loop start. Returns (offset, status)."""
    i = text.find(quote, search_from)
    if i == -1:
        # tolerate the judge normalizing whitespace
        i = text.replace("\n", " ").find(quote.replace("\n", " "), search_from)
        if i == -1:
            return None, "quote_not_found"
    if text.find(quote, i + 1) != -1 and text.find(quote, i + 1) < search_from + 5000:
        status = "quote_ambiguous_first_used"
    else:
        status = "ok"
    return i, status


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--candidates", default=os.path.join(here, "out", "candidates.jsonl"))
    ap.add_argument("--out", default=os.path.join(here, "out", "judged.jsonl"))
    ap.add_argument("--runs-root", default=os.path.join(REPO_ROOT, "runs"))
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="print prompts instead of calling the API")
    args = ap.parse_args()

    cands = [json.loads(l) for l in open(args.candidates)]
    if args.limit:
        cands = cands[: args.limit]

    client = None
    if not args.dry_run:
        try:
            import anthropic
        except ImportError:
            sys.exit("pip install anthropic (or use --dry-run)")
        client = anthropic.Anthropic()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    text_cache = {}
    with open(args.out, "w") as out:
        for n, c in enumerate(cands):
            path = os.path.join(args.runs_root, c["case_key"], c["arm"], "output.txt")
            if path not in text_cache:
                with open(path, errors="replace") as fh:
                    text_cache[path] = fh.read()
            text = text_cache[path]
            win_start, window = build_window(text, c)
            prompt = PROMPT.format(unit=c["unit"][:120], window=window)

            if args.dry_run:
                print(f"--- [{n}] {c['case_key']}/{c['arm']} @{c['char_start']} "
                      f"({len(prompt)} chars) ---")
                continue

            resp = client.messages.create(
                model=args.model,
                max_tokens=1024,
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[{"role": "user", "content": prompt}],
            )
            if resp.stop_reason == "refusal":
                verdict = {"is_degenerate_loop": None, "events": [],
                           "judge_status": "refusal"}
            else:
                data = json.loads(next(b.text for b in resp.content if b.type == "text"))
                onset_char, onset_status = None, "no_onset"
                if data["is_degenerate_loop"] and data.get("onset_quote"):
                    onset_char, onset_status = locate(
                        data["onset_quote"], text, max(0, c["char_start"] - PRE_CTX))
                events = []
                for ev in data["events"]:
                    off, status = locate(ev["escape_quote"], text, c["char_start"])
                    events.append({"escape_char": off,
                                   "escape_quote": ev["escape_quote"],
                                   "escape_kind": ev["escape_kind"],
                                   "locate_status": status})
                verdict = {"is_degenerate_loop": data["is_degenerate_loop"],
                           "onset_char": onset_char,
                           "onset_quote": data.get("onset_quote", ""),
                           "onset_locate_status": onset_status,
                           "events": events, "judge_status": "ok"}
            row = dict(c)
            row.update(verdict)
            out.write(json.dumps(row) + "\n")
            out.flush()
            print(f"[{n + 1}/{len(cands)}] {c['case_key']}/{c['arm']} "
                  f"loop={verdict['is_degenerate_loop']} "
                  f"events={len(verdict['events'])}")

    if args.dry_run:
        print(f"\n{len(cands)} prompts (dry run, nothing written)")
    else:
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
