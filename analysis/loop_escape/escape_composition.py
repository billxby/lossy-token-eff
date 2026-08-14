#!/usr/bin/env python3
"""Stage 3: label loop onset / interior / escape tokens and tally
emission_source composition (accepted_draft / recovered / bonus).

Reuses the viewer's char-span machinery (viewer/server.py: load_emitted,
align_spans, char_to_token_index) so char offsets map to trace rows exactly
as /api/trace_at does.

Reports:
  - composition at escape tokens (+-2 window), onset tokens (+-2 window),
    loop interior, and whole-trace base rate, with lift + Wilson CIs
  - inside-loop rule agreement: for loop-interior tokens, how often the
    strict rule would have accepted the same token anyway
    (strict_would_accept), vs tokens only the lossy rule accepted
    (lossy_only_accepted), vs recovered (already rejection-resampled)
    tokens that stayed in the loop -- i.e. whether falling back to the
    strict rule inside a loop could even change anything
  - per-token labels for every loop region -> out/loop_tokens.jsonl
    (role: onset | interior | escape)

Usage:
    python3 analysis/loop_escape/escape_composition.py \
        [--judged out/judged.jsonl] [--report out/report.md]
    # before the judge has run, approximate escape = end of detected region:
    python3 analysis/loop_escape/escape_composition.py \
        --from-candidates out/candidates.jsonl
"""
import argparse
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "viewer"))
import server  # noqa: E402  (viewer/server.py -- import-safe, no HTTP served)

SOURCES = ("accepted_draft", "recovered", "bonus")

TOKEN_FIELDS = (
    "output_position", "emission_source", "emitted_token_text",
    "strict_would_accept", "lossy_would_accept", "actually_accepted",
    "lossy_only_accepted", "token_marker_guard_active", "window_guard_active",
    "p", "q", "target_entropy", "pos_in_round",
)


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, center - half), min(1.0, center + half))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--judged", default=os.path.join(HERE, "out", "judged.jsonl"))
    ap.add_argument("--from-candidates", default=None,
                    help="skip the judge: treat each candidate's char_end as the escape")
    ap.add_argument("--runs-root", default=None)
    ap.add_argument("--report", default=os.path.join(HERE, "out", "report.md"))
    args = ap.parse_args()

    if args.runs_root:
        server.RUNS_ROOT = os.path.abspath(args.runs_root)

    # normalize input: loops (with onset) + escape events
    loops, escapes = [], []
    src_path = args.from_candidates or args.judged
    for line in open(src_path):
        row = json.loads(line)
        if args.from_candidates:
            row["onset_char"] = row["char_start"]
            loops.append(row)
            escapes.append({**row, "escape_char": row["char_end"],
                            "escape_kind": "approx_region_end"})
        else:
            if not row.get("is_degenerate_loop"):
                continue
            if row.get("onset_char") is None:
                row["onset_char"] = row["char_start"]
            loops.append(row)
            for ev in row["events"]:
                if ev.get("escape_char") is not None:
                    escapes.append({**row, **ev})

    arm_key = lambda r: (r["case_key"], r["arm"])
    arms = sorted({arm_key(r) for r in loops})

    trace_cache, skipped = {}, []
    base_comp = Counter()
    for case_key, arm in arms:
        try:
            emitted = server.load_emitted(case_key, arm)
        except Exception as e:
            skipped.append((case_key, arm, str(e)))
            emitted = None
        trace_cache[(case_key, arm)] = emitted
        if emitted is not None:
            base_comp.update(r.get("emission_source") for r in emitted[3])

    esc_comp, esc_win = Counter(), Counter()
    onset_comp, onset_win = Counter(), Counter()
    loop_comp = Counter()
    # inside-loop rule agreement: (emission_source, strict_would_accept,
    # lossy_only_accepted) over interior tokens
    interior_rule = Counter()
    loops_with_recovered = 0
    onset_lossy_only = 0
    esc_rows_out = []
    token_labels_path = os.path.join(os.path.dirname(args.report), "loop_tokens.jsonl")
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    token_labels = open(token_labels_path, "w")

    # escape token indexes per arm-region, so interior labeling can tag them
    esc_idx_by_loop = {}
    for e in escapes:
        emitted = trace_cache.get(arm_key(e))
        if emitted is None:
            continue
        _, _, spans, rows = emitted
        idx = server.char_to_token_index(spans, e["escape_char"])
        esc_idx_by_loop.setdefault((arm_key(e), e["char_start"]), set()).add(idx)
        tok = rows[idx]
        esc_comp[tok.get("emission_source")] += 1
        for j in range(max(0, idx - 2), min(len(rows), idx + 3)):
            esc_win[rows[j].get("emission_source")] += 1
        esc_rows_out.append({
            "case_key": e["case_key"], "arm": e["arm"],
            "escape_char": e["escape_char"],
            "escape_kind": e.get("escape_kind"),
            "escape_quote": e.get("escape_quote", "")[:60],
            **{k: tok.get(k) for k in TOKEN_FIELDS},
        })

    for r in loops:
        emitted = trace_cache.get(arm_key(r))
        if emitted is None:
            continue
        _, _, spans, rows = emitted
        onset_idx = server.char_to_token_index(spans, r["onset_char"])
        end_idx = server.char_to_token_index(spans, r["char_end"])
        esc_idxs = esc_idx_by_loop.get((arm_key(r), r["char_start"]), set())

        onset_tok = rows[onset_idx]
        onset_comp[onset_tok.get("emission_source")] += 1
        if onset_tok.get("lossy_only_accepted"):
            onset_lossy_only += 1
        for j in range(max(0, onset_idx - 2), min(len(rows), onset_idx + 3)):
            onset_win[rows[j].get("emission_source")] += 1

        saw_recovered = False
        for i in range(onset_idx, end_idx + 1):
            tok = rows[i]
            src = tok.get("emission_source")
            role = ("onset" if i == onset_idx
                    else "escape" if i in esc_idxs
                    else "interior")
            if role == "interior":
                loop_comp[src] += 1
                interior_rule[(src,
                               bool(tok.get("strict_would_accept")),
                               bool(tok.get("lossy_only_accepted")))] += 1
                if src == "recovered":
                    saw_recovered = True
            token_labels.write(json.dumps({
                "case_key": r["case_key"], "arm": r["arm"],
                "loop_char_start": r["char_start"], "role": role,
                **{k: tok.get(k) for k in TOKEN_FIELDS},
            }) + "\n")
        if saw_recovered:
            loops_with_recovered += 1
    token_labels.close()

    n_esc = sum(esc_comp.values())
    n_base = sum(base_comp.values()) or 1
    n_interior = sum(loop_comp.values()) or 1
    n_onset = sum(onset_comp.values()) or 1

    lines = []
    lines.append("# Loop-escape emission-source composition\n")
    lines.append(f"Input: `{src_path}` -- {len(loops)} loop regions, "
                 f"{n_esc} escape events mapped, {len(skipped)} arms skipped "
                 f"(no/unreadable trace).\n")
    lines.append(f"| composition | {' | '.join(SOURCES)} |")
    lines.append("|---|---|---|---|")
    for name, comp in (("escape tokens", esc_comp),
                       ("escape ±2 window", esc_win),
                       ("onset tokens", onset_comp),
                       ("onset ±2 window", onset_win),
                       ("loop interior", loop_comp),
                       ("whole-trace base", base_comp)):
        n = sum(comp.values()) or 1
        lines.append("| " + name + " | "
                     + " | ".join(f"{comp[s]} ({comp[s] / n:.1%})" for s in SOURCES)
                     + " |")
    lines.append("")
    lines.append("## Lift at escape points (share of escapes / base rate)\n")
    for s in SOURCES:
        base_p = base_comp[s] / n_base
        esc_p = esc_comp[s] / n_esc if n_esc else 0.0
        lo, hi = wilson_ci(esc_comp[s], n_esc)
        lift = esc_p / base_p if base_p else float("nan")
        lines.append(f"- **{s}**: escape share {esc_p:.1%} "
                     f"(95% CI {lo:.1%}-{hi:.1%}), base {base_p:.1%}, "
                     f"lift **{lift:.2f}x**")

    lines.append("")
    lines.append("## Loop onset\n")
    lines.append(f"Of {n_onset} onset tokens, **{onset_lossy_only}** were "
                 f"lossy-only acceptances (strict would have rejected the token "
                 f"that started the loop).\n")

    lines.append("## Inside-loop rule agreement\n")
    lines.append("Would falling back to the strict rule *inside* the loop change "
                 "anything? For each interior token: `strict agrees` = strict rule "
                 "would accept the same token (a strict guard changes nothing); "
                 "`lossy-only` = only the lossy rule accepted it (a strict guard "
                 "would have rejected + resampled here); `recovered` tokens already "
                 "went through rejection + residual resampling and stayed in the "
                 "loop.\n")
    lines.append("| interior source | n | strict agrees | lossy-only |")
    lines.append("|---|---|---|---|")
    for s in SOURCES:
        n_s = sum(v for (src, _, _), v in interior_rule.items() if src == s) or 0
        agree = sum(v for (src, sw, _), v in interior_rule.items()
                    if src == s and sw)
        lonly = sum(v for (src, _, lo_), v in interior_rule.items()
                    if src == s and lo_)
        pa = agree / n_s if n_s else 0.0
        pl = lonly / n_s if n_s else 0.0
        lines.append(f"| {s} | {n_s} | {agree} ({pa:.1%}) | {lonly} ({pl:.1%}) |")
    n_rec = loop_comp["recovered"]
    strict_diff = sum(v for (_, _, lo_), v in interior_rule.items() if lo_)
    lines.append("")
    lines.append(f"- {loops_with_recovered}/{len(loops)} loops contain at least one "
                 f"`recovered` (rejection-resampled) token in their interior -- "
                 f"resampling happened inside the loop without breaking it.")
    lines.append(f"- {strict_diff}/{n_interior} interior tokens "
                 f"({strict_diff / n_interior:.1%}) are lossy-only acceptances -- "
                 f"the only places a strict-inside-loop fallback would act "
                 f"differently at all. Everywhere else strict emits the same "
                 f"token or the resample already ran.")

    lines.append("")
    lines.append("## Per-escape detail\n")
    lines.append("| case_key | arm | char | source | kind | quote (viewer search) |")
    lines.append("|---|---|---|---|---|---|")
    for e in sorted(esc_rows_out, key=lambda x: (x["case_key"], x["arm"], x["escape_char"])):
        q = (e["escape_quote"] or "").replace("|", "\\|").replace("\n", "\\n")
        lines.append(f"| {e['case_key']} | {e['arm']} | {e['escape_char']} "
                     f"| {e['emission_source']} | {e['escape_kind']} | `{q}` |")
    if skipped:
        lines.append("\n## Skipped arms (no usable trace)\n")
        for ck, a, err in skipped:
            lines.append(f"- {ck}/{a}: {err.splitlines()[0][:120]}")

    report = "\n".join(lines) + "\n"
    with open(args.report, "w") as f:
        f.write(report)
    with open(os.path.splitext(args.report)[0] + "_escapes.jsonl", "w") as f:
        for e in esc_rows_out:
            f.write(json.dumps(e) + "\n")
    print(report)
    print(f"(report -> {args.report}; per-token labels -> {token_labels_path})")


if __name__ == "__main__":
    main()
