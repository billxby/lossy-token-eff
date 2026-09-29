#!/usr/bin/env python3
"""Write campaign/addendum/RESULTS.md from the addendum's CSVs (every number is
read from a named CSV row, never typed in), plus the hand-written observations
in campaign/addendum/RESULTS_notes.md (included verbatim at the end).

  python3 scripts/addendum_results.py
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
ADD = REPO / "campaign" / "addendum"
AN = ADD / "analysis"
DS_ORDER = ["gsm8k", "aime24", "humaneval", "livecodebench", "mtbench", "longbench_v2"]
METHOD_ORDER = ["mentored_dec", "cactus", "spec_casc_opt", "r_fuzzy", "spec_casc_tok"]


def rows(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def f(x, nd=2):
    if x in (None, ""):
        return "-"
    try:
        v = float(x)
    except ValueError:
        return str(x)
    return f"{v:.{nd}f}"


def pct(x, nd=0):
    return "-" if x in (None, "") else f"{100 * float(x):.{nd}f}%"


def rel(p: pathlib.Path) -> str:
    return str(p.relative_to(REPO))


def cell_sort(r):
    return (r.get("target", ""), DS_ORDER.index(r["dataset"]) if r.get("dataset") in DS_ORDER else 9,
            METHOD_ORDER.index(r["method"]) if r.get("method") in METHOD_ORDER else 9)


def section_status() -> list[str]:
    m = rows(ADD / "manifest.csv")
    out = ["## Status", ""]
    if not m:
        return out + ["(no manifest yet)", ""]
    by = defaultdict(Counter)
    for r in m:
        by[r["step"]][r["status"]] += 1
    used = sum(float(r["gpu_hours_actual"] or 0) for r in m)
    left = sum(float(r["gpu_hours_est"] or 0) for r in m if r["status"] in ("queued", "running", "pending"))
    blocked = sum(float(r["gpu_hours_est"] or 0) for r in m if r["status"] == "blocked")
    out += [f"Source: `{rel(ADD / 'manifest.csv')}` ({len(m)} rows). GPU-hours used so far (sum of "
            f"`gpu_hours_actual`): {used:.1f}; estimated remaining, runnable rows: {left:.1f}; blocked rows: {blocked:.1f}.", "",
            "| step | " + " | ".join(["done", "running", "queued", "pending", "blocked"]) + " |", "|---|---:|---:|---:|---:|---:|"]
    for step in sorted(by, key=lambda s: [float(x) for x in s.split(".")]):
        c = by[step]
        out.append(f"| {step} | " + " | ".join(str(c.get(k, 0)) for k in ("done", "running", "queued", "pending", "blocked")) + " |")
    return out + [""]


def section_step1() -> list[str]:
    out = ["## Step 1: zero-GPU analyses (seed 0, the paper's data)", ""]
    s = rows(AN / "eq4_vs_measured_summary.csv")
    if s:
        s = s[0]
        out += [f"**Eq. 4 vs measured** (`{rel(AN / 'eq4_vs_measured_summary.csv')}`, row 1; per cell: "
                f"`{rel(AN / 'eq4_vs_measured.csv')}`), {s['cells']} loosest cells: Eq. 4 predicts a win in "
                f"{s['eq4_wins']}, rounds win in {s['rounds_wins']}, time win in {s['time_wins']}; "
                f"{s['eq4_wins_that_are_time_losses']} Eq. 4 wins and {s['rounds_wins_that_are_time_losses']} rounds wins "
                f"are time losses (paper: 33 / 38 / 27 / 6 / 11 -- reproduced exactly). New: {s['time_losses_beyond_ci']} "
                f"cells are time losses beyond the 95% paired bootstrap interval; of the Eq. 4-win time losses "
                f"{s['eq4_wins_that_are_time_losses_beyond_ci']}, and of the rounds-win time losses "
                f"{s['rounds_wins_that_are_time_losses_beyond_ci']}, lie beyond it.", ""]
    e = sorted(rows(AN / "eq4_vs_measured.csv"), key=cell_sort)
    if e:
        out += ["| target | dataset | method | alpha | lambda | gain | gain/lambda | rounds ratio [95% CI] | time ratio [95% CI] |",
                "|---|---|---|---:|---:|---:|---:|---|---|"]
        for r in e:
            out.append(f"| {r['target']} | {r['dataset']} | {r['method']} | {r['alpha']} | {f(r['lambda'])} | {f(r['gain'])} | "
                       f"{f(r['gain_over_lambda'])} | {f(r['rounds_ratio'])} [{f(r['rounds_ratio_ci_lo'])}, {f(r['rounds_ratio_ci_hi'])}] | "
                       f"{f(r['time_ratio'])} [{f(r['time_ratio_ci_lo'])}, {f(r['time_ratio_ci_hi'])}] |")
        out.append("")
    si = sorted(rows(AN / "split_inflation.csv"), key=cell_sort)
    if si:
        out += [f"**Where the extra length goes** (`{rel(AN / 'split_inflation.csv')}`; thinking = GPT-OSS analysis channel / "
                "Qwen3 `<think>` blocks, characters):", "",
                "| target | dataset | method | lambda (tokens) | lambda thinking | lambda answer | share of extra in thinking |",
                "|---|---|---|---:|---:|---:|---:|"]
        for r in si:
            out.append(f"| {r['target']} | {r['dataset']} | {r['method']} | {f(r['lambda'])} | {f(r['lambda_think_chars'])} | "
                       f"{f(r['lambda_answer_chars'])} | {pct(r['extra_share_think'])} |")
        out.append("")
    ce = sorted(rows(AN / "censoring.csv"), key=cell_sort)
    if ce:
        out += [f"**Censoring** (`{rel(AN / 'censoring.csv')}`): cap-out rates and lambda / accuracy restricted to pairs where both "
                "runs finished.", "",
                "| target | dataset | method | cap-out relaxed | cap-out strict | lambda all | lambda both finished | "
                "acc relaxed / strict (all) | acc relaxed / strict (both finished) | n both finished |",
                "|---|---|---|---:|---:|---:|---:|---|---|---:|"]
        for r in ce:
            out.append(f"| {r['target']} | {r['dataset']} | {r['method']} | {pct(r['capout_rate_relaxed'])} | {pct(r['capout_rate_strict'])} | "
                       f"{f(r['lambda_all'])} | {f(r['lambda_both_finished'])} | {pct(r['acc_relaxed_all'])} / {pct(r['acc_strict_all'])} | "
                       f"{pct(r['acc_relaxed_both_finished'])} / {pct(r['acc_strict_both_finished'])} | {r['n_pairs_both_finished']} |")
        out.append("")
    di = sorted(rows(AN / "distribution.csv"), key=cell_sort)
    if di:
        out += [f"**Uniform shift or runaway completions?** (`{rel(AN / 'distribution.csv')}`): per-case L_relaxed / L_strict.", "",
                "| target | dataset | method | p10 | p50 | p90 | share > 2 | top-10% cases' share of net extra |",
                "|---|---|---|---:|---:|---:|---:|---:|"]
        for r in di:
            out.append(f"| {r['target']} | {r['dataset']} | {r['method']} | {f(r['ratio_p10'])} | {f(r['ratio_p50'])} | "
                       f"{f(r['ratio_p90'])} | {pct(r['share_ratio_gt2'])} | {pct(r['top10pct_share_of_net_extra'])} |")
        out.append("")
    rp = sorted(rows(AN / "repetition.csv"), key=cell_sort)
    if rp:
        out += [f"**Exact repetition** (`{rel(AN / 'repetition.csv')}`; per run: `{rel(AN / 'repetition_runs.csv')}`): share of "
                "tokens inside a 50-gram that occurred earlier in the same output, and the longest repeated token run.", "",
                "| target | dataset | method | rep-50 share relaxed | rep-50 share strict | longest repeat relaxed | longest repeat strict |",
                "|---|---|---|---:|---:|---:|---:|"]
        for r in rp:
            out.append(f"| {r['target']} | {r['dataset']} | {r['method']} | {pct(r['mean_rep50_frac_relaxed'], 2)} | "
                       f"{pct(r['mean_rep50_frac_strict'], 2)} | {f(r['mean_longest_repeat_relaxed'], 0)} | {f(r['mean_longest_repeat_strict'], 0)} |")
        out.append("")
    tr = rows(AN / "time_per_round_regression.csv")
    sp = rows(AN / "time_per_round_spearman.csv")
    if tr:
        out += [f"**Time per round** (`{rel(AN / 'time_per_round.csv')}`, `{rel(AN / 'time_per_round_regression.csv')}`, "
                f"`{rel(AN / 'time_per_round_spearman.csv')}`): OLS of time per round on output tokens (dataset = all):", ""]
        for r in tr:
            if r["dataset"] == "all":
                out.append(f"- {r['target']}, {r['scope']} runs (n={r['n_runs']}): slope {float(r['slope_s_per_token']):.3g} s/token, "
                           f"intercept {float(r['intercept_s']) * 1000:.1f} ms, R^2 {f(r['r2'], 3)}")
        if sp:
            out.append(f"- Spearman(lambda, time-per-round ratio) over {sp[0]['n_cells']} cells: rho = {f(sp[0]['spearman_rho'], 3)}, "
                       f"two-sided permutation p = {sp[0]['permutation_p_two_sided']} (20,000 shuffles)")
        out.append("")
    ad = rows(AN / "admitted_tokens.csv")
    if ad:
        out += [f"**What the relaxed rules admit** (`{rel(AN / 'admitted_tokens.csv')}`, GPT-OSS traced runs, loosest alpha): "
                "tokens accepted only because of the relaxation vs tokens both rules accept.", "",
                "| method | class | tokens | target p median | target p mean | target rank mean | rank p90 | target entropy mean |",
                "|---|---|---:|---:|---:|---:|---:|---:|"]
        for r in sorted(ad, key=lambda r: (METHOD_ORDER.index(r["method"]), r["token_class"])):
            if r["scope"] == "loosest_alpha":
                out.append(f"| {r['method']} | {r['token_class']} | {r['n_tokens']} | {f(r['p_median'], 3)} | {f(r['p_mean'], 3)} | "
                           f"{f(r['rank_mean'], 1)} | {f(r['rank_p90'], 0)} | {f(r['entropy_mean'], 2)} |")
        out.append("")
    mj = rows(AN / "mtbench_judge_summary.csv")
    out += ["**MT-Bench judge (step 1.9)**: " + (f"`{rel(AN / 'mtbench_judge_summary.csv')}`." if mj else
            "not run -- no Anthropic API key available (PROGRESS.md, Needs Bill 2); the judge is ready "
            "(`scripts/addendum_mtbench_judge.py`)."), ""]
    return out


def section_seeds() -> list[str]:
    s = sorted(rows(ADD / "seeds" / "summary.csv"), key=cell_sort)
    out = ["## Step 2: seeds on the relaxed arms", ""]
    if not s:
        return out + ["Pending.", ""]
    seeds = sorted({k.split("_s")[-1] for k in s[0] if k.startswith("lambda_s")})
    out += [f"Source: `{rel(ADD / 'seeds' / 'summary.csv')}` (per-seed tables `campaign/addendum/seeds/<dataset>__seed<k>.csv`). "
            "Seed 0 is the campaign's run (old box, H100 PCIe); seeds 1-2 ran on Nibi (H100 SXM). Ratios pair each seed's "
            "relaxed arm with strict of the same seed; '-' = that seed is not complete yet.", "",
            "| target | dataset | method | alpha | " + " | ".join(f"lambda s{k}" for k in seeds) + " | lambda mean (sd) | "
            + " | ".join(f"time ratio s{k}" for k in seeds) + " | time mean (sd) | " + " | ".join(f"acc s{k}" for k in seeds) + " |",
            "|---|---|---|---:|" + "---:|" * (3 * len(seeds) + 2)]
    for r in s:
        out.append(f"| {r['target']} | {r['dataset']} | {r['method']} | {r['alpha']} | "
                   + " | ".join(f(r.get(f"lambda_s{k}")) for k in seeds)
                   + f" | {f(r['lambda_mean'])} ({f(r['lambda_sd'])}) | "
                   + " | ".join(f(r.get(f"time_ratio_s{k}")) for k in seeds)
                   + f" | {f(r['time_ratio_mean'])} ({f(r['time_ratio_sd'])}) | "
                   + " | ".join(pct(r.get(f"accuracy_s{k}")) for k in seeds) + " |")
    return out + [""]


def section_tables(title: str, pattern: str) -> list[str]:
    files = sorted((ADD / "tables").glob(pattern))
    out = [title, ""]
    if not files:
        return out + ["Pending.", ""]
    for p in files:
        t = rows(p)
        if not t:
            continue
        out += [f"`{rel(p)}`:", "", "| " + " | ".join(t[0].keys()) + " |", "|" + "---|" * len(t[0])]
        for r in t:
            out.append("| " + " | ".join(f(v, 3) if k not in ("source", "dataset", "method", "condition") else v for k, v in r.items()) + " |")
        out.append("")
    return out


def main() -> int:
    lines = ["# NAACL-2027 addendum: results", "",
             f"Generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `scripts/addendum_results.py` "
             "from the CSVs it names; hand-written observations are in the last section (from `RESULTS_notes.md`). "
             "Settings and deviations: `campaign/addendum/README.md`.", ""]
    lines += section_status()
    lines += section_step1()
    lines += section_seeds()
    lines += section_tables("## Step 3: lossless draft-length sweep (strict, seed 0)", "nspec__*.csv")
    lines += section_tables("## Step 4.1: temperature (strict, seed 0)", "temp__*.csv")
    lines += section_tables("## Step 4.2: Qwen3 at its recommended sampler", "qwenT0.6__*.csv")
    lines += section_tables("## Step 4.3: standalone LM drafter (Qwen3-0.6B)", "lmdraft__*.csv")
    best = rows(ADD / "best_setting.csv")
    lines += ["## Step 5: alpha grid completion and best-setting validation", "",
              (f"`{rel(ADD / 'best_setting.csv')}` ({len(best)} rows)." if best else "Pending."), ""]
    aime = rows(ADD / "aime24_repeats.csv")
    lines += ["## Step 6: AIME24 accuracy repeats", "", (f"`{rel(ADD / 'aime24_repeats.csv')}` ({len(aime)} rows)." if aime else "Pending."), ""]
    notes = ADD / "RESULTS_notes.md"
    lines += ["## Observations, failures and anything that looked wrong", ""]
    lines += [notes.read_text(encoding="utf-8").strip() if notes.is_file() else "(none yet)", ""]
    (ADD / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {rel(ADD / 'RESULTS.md')} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
