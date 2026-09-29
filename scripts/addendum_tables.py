#!/usr/bin/env python3
"""Tables for steps 2-6 of the NAACL-2027 addendum (campaign/addendum/README.md),
built from the local runs/ tree and campaign/addendum/analysis/grades.csv
(the campaign's own graders, run on Nibi by scripts/addendum_grade.py).

  python3 scripts/addendum_tables.py seeds    # step 2.3: seeds/<ds>__seed<k>.csv + seeds/summary.csv
  python3 scripts/addendum_tables.py nspec    # step 3.2: tables/nspec__<ds>.csv
  python3 scripts/addendum_tables.py temp     # step 4.1: tables/temp__<ds>.csv
  python3 scripts/addendum_tables.py qwenT    # step 4.2: tables/qwenT0.6__<ds>.csv
  python3 scripts/addendum_tables.py lmdraft  # step 4.3: tables/lmdraft__<ds>.csv
  python3 scripts/addendum_tables.py best     # step 5.2: best_setting.csv (+ --plan: the seed-1 arms to run)
  python3 scripts/addendum_tables.py aime     # step 6.2: aime24_repeats.csv

Ratios compare an arm with `strict` of the same dataset and seed on the cases
both have (paired): lambda = mean completion tokens ratio, rounds ratio = mean
draft_rounds ratio, time ratio = mean wall_time_seconds ratio. Intervals are
95% percentile bootstraps over cases (10,000 resamples, numpy seed 20261001).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNS = REPO / "runs"
ADD = REPO / "campaign" / "addendum"
BASE = ["gsm8k", "aime24", "humaneval", "livecodebench", "mtbench", "longbench_v2"]
FIVE = ["mentored_dec", "cactus", "spec_casc_opt", "r_fuzzy", "spec_casc_tok"]
N_CASES = {"gsm8k": 150, "humaneval": 150, "longbench_v2": 150, "livecodebench": 90, "mtbench": 80, "aime24": 30}
GRADED = {"gsm8k", "aime24", "humaneval", "livecodebench", "longbench_v2"}
BOOT = 10000
RNG_SEED = 20261001


def params_dir(method: str, alpha: str) -> str:
    if method in ("strict", "baseline"):
        return method
    return f"alpha{float(alpha):g}".replace("-", "neg")


def loosest(ds: str, method: str) -> str:
    with (REPO / "campaign" / "results" / f"{ds}.csv").open(newline="", encoding="utf-8") as handle:
        return f"{max(float(r['alpha']) for r in csv.DictReader(handle) if r['method'] == method):g}"


_grades = None


def grades() -> dict[str, int | None]:
    global _grades
    if _grades is None:
        _grades = {}
        path = ADD / "analysis" / "grades.csv"
        if path.is_file():
            with path.open(newline="", encoding="utf-8") as handle:
                for r in csv.DictReader(handle):
                    _grades[r["relpath"]] = int(r["correct"]) if r["correct"] in ("0", "1") else None
    return _grades


def load_cell(ds: str, method: str, alpha: str, seed: int, run_root: str = "runs") -> dict[str, dict]:
    """case -> run record (ok runs only) with 'correct' attached (None if not graded)."""
    root = REPO / run_root / ds / method / params_dir(method, alpha)
    out = {}
    for run_json in sorted(root.glob(f"case_*/seed_{seed}/run.json")):
        try:
            run = json.loads(run_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if run.get("status") != "ok":
            continue
        rel = str(run_json.parent.relative_to(RUNS))
        run["correct"] = grades().get(rel)
        run["_rel"] = rel
        out[run_json.parent.parent.name] = run
    return out


def boot_mean_ci(x: np.ndarray, rng) -> tuple[float, float]:
    idx = rng.integers(0, len(x), size=(BOOT, len(x)))
    m = x[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def boot_ratio_ci(a: np.ndarray, b: np.ndarray, rng) -> tuple[float, float]:
    idx = rng.integers(0, len(a), size=(BOOT, len(a)))
    r = a[idx].mean(axis=1) / b[idx].mean(axis=1)
    return float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def fmt(x):
    if x is None:
        return ""
    if isinstance(x, float):
        return "" if math.isnan(x) else f"{x:.6g}"
    return x


def write_csv(path: pathlib.Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if not rows:
        print(f"(no rows for {path.name})")
        return
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: fmt(row.get(k)) for k in fields})
    print(f"wrote {path.relative_to(REPO)} ({len(rows)} rows)")


def accuracy(runs: list[dict]) -> float | None:
    vals = [r["correct"] for r in runs]
    if not vals or any(v is None for v in vals):
        return None
    return sum(vals) / len(vals)


def compare(relaxed: dict[str, dict], strict: dict[str, dict], rng=None) -> dict:
    """Paired comparison of two cells (case -> run)."""
    cases = sorted(set(relaxed) & set(strict))
    if not cases:
        return {"n_pairs": 0}
    R = [relaxed[c] for c in cases]
    S = [strict[c] for c in cases]
    arr = lambda runs, k: np.array([float(r[k]) for r in runs])
    Lr, Ls = arr(R, "output_tokens"), arr(S, "output_tokens")
    Rr, Rs = arr(R, "draft_rounds"), arr(S, "draft_rounds")
    Tr, Ts = arr(R, "wall_time_seconds"), arr(S, "wall_time_seconds")
    out = {
        "n_pairs": len(cases),
        "l_bar": float(np.mean([r["l_bar"] for r in R])), "l_bar_strict": float(np.mean([s["l_bar"] for s in S])),
        "mean_tokens": float(Lr.mean()), "mean_tokens_strict": float(Ls.mean()),
        "lambda": float(Lr.mean() / Ls.mean()), "rounds_ratio": float(Rr.mean() / Rs.mean()),
        "time_ratio": float(Tr.mean() / Ts.mean()),
        "accuracy": accuracy(R), "accuracy_strict": accuracy(S),
        "capout_rate": float(np.mean([r.get("finish_reason") == "length" for r in R])),
        "capout_rate_strict": float(np.mean([s.get("finish_reason") == "length" for s in S])),
    }
    if rng is not None:
        out["lambda_ci_lo"], out["lambda_ci_hi"] = boot_ratio_ci(Lr, Ls, rng)
        out["rounds_ratio_ci_lo"], out["rounds_ratio_ci_hi"] = boot_ratio_ci(Rr, Rs, rng)
        out["time_ratio_ci_lo"], out["time_ratio_ci_hi"] = boot_ratio_ci(Tr, Ts, rng)
    return out


# ------------------------------------------------------------------ step 2.3

STEP2_CELLS = {  # dataset -> methods with seeds 1-2 (plus strict), steps 2.1 and 2.2
    **{ds: FIVE for ds in ("gsm8k", "humaneval", "mtbench", "livecodebench",
                           "gsm8k_qwen3", "humaneval_qwen3", "mtbench_qwen3", "livecodebench_qwen3")},
    "aime24": FIVE, "longbench_v2": ["mentored_dec", "spec_casc_opt", "r_fuzzy"],
    "aime24_qwen3": ["spec_casc_opt", "r_fuzzy"],
}


def seeds_present(ds: str) -> list[int]:
    seeds = set()
    for d in (RUNS / ds / "strict" / "strict").glob("case_*/seed_*"):
        seeds.add(int(d.name.removeprefix("seed_")))
    return sorted(seeds)


def cmd_seeds(args) -> int:
    py = sys.executable
    for ds in STEP2_CELLS:
        for seed in seeds_present(ds):
            if seed == 0:
                continue
            out = ADD / "seeds" / f"{ds}__seed{seed}.csv"
            subprocess.run([py, str(REPO / "scripts" / "campaign_report.py"), "--dataset", ds, "--seed", str(seed),
                            "--runs-root", str(RUNS), "--tables-out", str(out),
                            "--calibration-json", str(ADD / "seeds" / ".no-calibration.json")],
                           check=True, capture_output=True)
            print(f"wrote {out.relative_to(REPO)}")
    rows = []
    for ds, methods in STEP2_CELLS.items():
        seeds = seeds_present(ds)
        strict = {s: load_cell(ds, "strict", "strict", s) for s in seeds}
        for method in methods:
            alpha = loosest(ds, method)
            row = {"target": "qwen3-8b" if ds.endswith("_qwen3") else "gpt-oss-20b",
                   "dataset": ds.removesuffix("_qwen3"), "method": method, "alpha": alpha}
            per = {}
            for s in seeds:
                c = compare(load_cell(ds, method, alpha, s), strict[s])
                full = c["n_pairs"] == N_CASES[ds.removesuffix("_qwen3")]
                row[f"n_pairs_s{s}"] = c["n_pairs"]
                for k in ("lambda", "rounds_ratio", "time_ratio", "accuracy", "accuracy_strict"):
                    row[f"{k}_s{s}"] = c.get(k) if full else None
                if full:
                    per[s] = c
            for k in ("lambda", "rounds_ratio", "time_ratio", "accuracy", "accuracy_strict"):
                vals = [per[s][k] for s in sorted(per) if per[s].get(k) is not None]
                row[f"{k}_mean"] = float(np.mean(vals)) if vals else None
                row[f"{k}_sd"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else None
                row[f"{k}_n_seeds"] = len(vals)
            rows.append(row)
    seeds_all = sorted({s for ds in STEP2_CELLS for s in seeds_present(ds)})
    fields = ["target", "dataset", "method", "alpha"]
    for k in ("lambda", "rounds_ratio", "time_ratio", "accuracy", "accuracy_strict"):
        fields += [f"{k}_s{s}" for s in seeds_all] + [f"{k}_mean", f"{k}_sd", f"{k}_n_seeds"]
    fields += [f"n_pairs_s{s}" for s in seeds_all]
    write_csv(ADD / "seeds" / "summary.csv", rows, fields)
    return 0


# ------------------------------------------------------------- steps 3, 4.1

def point_row(label: dict, runs: dict[str, dict], rng) -> dict:
    R = list(runs.values())
    row = dict(label)
    row["n_cases"] = len(R)
    for name, key in (("l_bar", "l_bar"), ("completion_tokens", "output_tokens"),
                      ("verifier_rounds", "draft_rounds"), ("wall_time_s", "wall_time_seconds")):
        x = np.array([float(r[key]) for r in R])
        row[f"mean_{name}"] = float(x.mean()) if len(x) else None
        if len(x):
            row[f"mean_{name}_ci_lo"], row[f"mean_{name}_ci_hi"] = boot_mean_ci(x, rng)
    acc = [r["correct"] for r in R]
    if R and all(a is not None for a in acc):
        x = np.array(acc, float)
        row["accuracy"] = float(x.mean())
        row["accuracy_ci_lo"], row["accuracy_ci_hi"] = boot_mean_ci(x, rng)
    row["capout_rate"] = float(np.mean([r.get("finish_reason") == "length" for r in R])) if R else None
    return row


def sweep_table(kind: str, values: list, condition: callable, extra_label: str) -> None:
    rng = np.random.default_rng(RNG_SEED)
    for base in ("gsm8k", "livecodebench"):
        for ds in (base, f"{base}_qwen3"):
            rows = []
            for v in values:
                runs = load_cell(ds, "strict", "strict", 0, run_root=f"runs/addendum/{condition(v)}")
                if runs:
                    rows.append(point_row({extra_label: v, "source": condition(v) + " (Nibi)"}, runs, rng))
            ref = load_cell(ds, "strict", "strict", 0, run_root="runs/addendum/nibiref")
            default = {"nspec": 6, "temp": 1.0}[kind]
            if ref:
                rows.append(point_row({extra_label: default, "source": "nibiref (Nibi, campaign settings)"}, ref, rng))
            old = load_cell(ds, "strict", "strict", 0)
            if old:
                rows.append(point_row({extra_label: default, "source": "campaign seed 0 (old box, H100 PCIe)"}, old, rng))
            rows.sort(key=lambda r: (float(r[extra_label]), r["source"]))
            write_csv(ADD / "tables" / f"{kind}__{ds}.csv", rows)


def cmd_nspec(args) -> int:
    sweep_table("nspec", [2, 3, 4, 8, 10], lambda k: f"nspec{k}", "n_draft")
    return 0


def cmd_temp(args) -> int:
    sweep_table("temp", [1.2, 1.5], lambda t: f"temp{t:g}", "temperature")
    return 0


def arm_table(condition: str, arms: list[tuple[str, str]], datasets: list[str]) -> None:
    rng = np.random.default_rng(RNG_SEED)
    for ds in datasets:
        strict = load_cell(ds, "strict", "strict", 0, run_root=f"runs/addendum/{condition}")
        rows = []
        for method, alpha in arms:
            if method == "strict":
                continue
            runs = load_cell(ds, method, alpha, 0, run_root=f"runs/addendum/{condition}")
            c = compare(runs, strict, rng)
            rows.append({"condition": condition, "dataset": ds, "method": method, "alpha": alpha, **c})
        write_csv(ADD / "tables" / f"{condition}__{ds}.csv", rows)


def cmd_qwenT(args) -> int:
    arms = [("strict", "strict")] + [(m, loosest("gsm8k_qwen3", m)) for m in FIVE]
    arm_table("qwenT0.6", arms, ["gsm8k_qwen3"])
    arms = [("strict", "strict")] + [(m, loosest("livecodebench_qwen3", m)) for m in FIVE]
    arm_table("qwenT0.6", arms, ["livecodebench_qwen3"])
    return 0


def cmd_lmdraft(args) -> int:
    arms = [("strict", "strict"), ("mentored_dec", "0.75"), ("cactus", "0.35"), ("spec_casc_tok", "0.8")]
    arm_table("lmdraft", arms, ["gsm8k_qwen3", "livecodebench_qwen3"])
    return 0


# ------------------------------------------------------------------ step 5.2

GRID = {"mentored_dec": ["0.15", "0.35", "0.55", "0.75"], "spec_casc_tok": ["0.15", "0.35", "0.55", "0.8"]}


def nibi_cases(cell: dict[str, dict]) -> set[str]:
    """Cases of a seed-0 cell that ran on Nibi (step 5.1 fills): config.json vllm.site_packages under /project."""
    out = set()
    for case, run in cell.items():
        cfg = RUNS / run["_rel"] / "config.json"
        try:
            site = json.loads(cfg.read_text(encoding="utf-8")).get("vllm", {}).get("site_packages", "")
        except (OSError, json.JSONDecodeError):
            site = ""
        if site.startswith("/project/") or "/projects/def-hongyanz/" in site:
            out.add(case)
    return out


def select_best(ds: str, method: str) -> tuple[str | None, list[dict]]:
    base = ds.removesuffix("_qwen3")
    strict = load_cell(ds, "strict", "strict", 0)
    nibiref = load_cell(ds, "strict", "strict", 0, run_root="runs/addendum/nibiref")
    cands = []
    for alpha in GRID[method]:
        cell = load_cell(ds, method, alpha, 0)
        if len(cell) < N_CASES[base]:
            cands.append({"alpha": alpha, "complete": False})
            continue
        c = compare(cell, strict)
        on_nibi = nibi_cases(cell)
        hw = "nibi" if len(on_nibi) > len(cell) / 2 else "old_box"
        if hw == "nibi":  # hardware-matched time ratio: Nibi cases vs the Nibi strict reference
            sub = {k: v for k, v in cell.items() if k in on_nibi}
            t = compare(sub, nibiref)
            c["time_ratio"] = t.get("time_ratio")
            c["time_ratio_basis"] = f"nibiref, {t.get('n_pairs', 0)} Nibi cases"
        else:
            c["time_ratio_basis"] = "campaign strict seed 0 (old box)"
        c.update({"alpha": alpha, "complete": True, "hardware": hw})
        if base in GRADED:
            ok = c["accuracy"] is not None and c["accuracy_strict"] is not None and c["accuracy"] >= c["accuracy_strict"] - 0.02
            c["rule"] = "accuracy >= strict - 2 points"
        else:
            ok = c["rounds_ratio"] < 1
            c["rule"] = "rounds ratio < 1 (no grader)"
        c["eligible"] = ok
        cands.append(c)
    eligible = [c for c in cands if c.get("eligible") and c.get("time_ratio") is not None]
    best = min(eligible, key=lambda c: c["time_ratio"])["alpha"] if eligible else None
    return best, cands


def cmd_best(args) -> int:
    rows, plan = [], []
    for base in BASE:
        for ds in (base, f"{base}_qwen3"):
            for method in GRID:
                best, cands = select_best(ds, method)
                complete = all(c["complete"] for c in cands)
                row = {"target": "qwen3-8b" if ds.endswith("_qwen3") else "gpt-oss-20b", "dataset": base,
                       "method": method, "grid_complete": complete, "chosen_alpha": best or "",
                       "rule": next((c["rule"] for c in cands if c.get("rule")), "")}
                for c in cands:
                    a = c["alpha"]
                    row[f"eligible_{a}"] = c.get("eligible", "")
                    row[f"time_ratio_s0_{a}"] = c.get("time_ratio")
                if best:
                    s0 = next(c for c in cands if c["alpha"] == best)
                    for k in ("lambda", "rounds_ratio", "time_ratio", "accuracy", "accuracy_strict", "n_pairs"):
                        row[f"s0_{k}"] = s0.get(k)
                    row["s0_hardware"], row["s0_time_ratio_basis"] = s0["hardware"], s0["time_ratio_basis"]
                    s1 = compare(load_cell(ds, method, best, 1), load_cell(ds, "strict", "strict", 1))
                    for k in ("lambda", "rounds_ratio", "time_ratio", "accuracy", "accuracy_strict", "n_pairs"):
                        row[f"s1_{k}"] = s1.get(k)
                    if complete:
                        plan.append({"dataset": ds, "method": method, "alpha": best})
                rows.append(row)
    write_csv(ADD / "best_setting.csv", rows)
    if args.plan:
        print(json.dumps(plan))
    return 0


# ------------------------------------------------------------------ step 6.2

def cmd_aime(args) -> int:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for ds in ("aime24", "aime24_qwen3"):
        seeds = [s for s in range(0, 5) if load_cell(ds, "strict", "strict", s)]
        strict = {s: load_cell(ds, "strict", "strict", s) for s in seeds}
        for method in ["strict", *FIVE]:
            alpha = "strict" if method == "strict" else loosest(ds, method)
            cells = {s: load_cell(ds, method, alpha, s) for s in seeds}
            full = [s for s in seeds if len(cells[s]) == 30 and all(r["correct"] is not None for r in cells[s].values())]
            row = {"target": "qwen3-8b" if ds.endswith("_qwen3") else "gpt-oss-20b", "method": method, "alpha": alpha,
                   "seeds_complete": " ".join(map(str, full))}
            for s in seeds:
                cell = cells[s]
                row[f"acc_s{s}"] = accuracy(list(cell.values())) if s in full else None
                if method != "strict" and s in full:
                    c = compare(cell, strict[s])
                    row[f"lambda_s{s}"], row[f"rounds_ratio_s{s}"] = c["lambda"], c["rounds_ratio"]
                row[f"mean_rounds_s{s}"] = float(np.mean([r["draft_rounds"] for r in cell.values()])) if s in full else None
            if full:
                M = np.array([[cells[s][f"case_{i:03d}"]["correct"] for s in full] for i in range(1, 31)], float)
                row["acc_mean_over_seeds"] = float(M.mean())
                row["acc_sd_across_seeds"] = float(M.mean(axis=0).std(ddof=1)) if len(full) > 1 else None
                # two-level bootstrap: problems with replacement, then seeds within each problem
                pi = rng.integers(0, 30, size=(BOOT, 30))
                si = rng.integers(0, len(full), size=(BOOT, 30, len(full)))
                boot = M[pi[..., None], si].mean(axis=(1, 2))
                row["acc_ci_lo"], row["acc_ci_hi"] = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
                row["n_seeds"] = len(full)
            rows.append(row)
    write_csv(ADD / "aime24_repeats.csv", rows)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("seeds", cmd_seeds), ("nspec", cmd_nspec), ("temp", cmd_temp), ("qwenT", cmd_qwenT),
                     ("lmdraft", cmd_lmdraft), ("aime", cmd_aime)):
        sub.add_parser(name).set_defaults(fn=fn)
    p = sub.add_parser("best")
    p.add_argument("--plan", action="store_true")
    p.set_defaults(fn=cmd_best)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
