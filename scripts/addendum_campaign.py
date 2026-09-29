#!/usr/bin/env python3
"""Mac-side orchestrator for the NAACL-2027 addendum campaign
(campaign/addendum/README.md). Nibi runs the GPU work through
scripts/addendum_lane.py; this script owns everything else:

  plan     build campaign/addendum/manifest.csv (the single source of truth)
           from the local runs/ tree + campaign/results/*.csv, and write each
           lane's ordered work list (campaign/addendum/lanes/<lane>.json)
  push     copy code + work lists to the lanes' repo copies / run roots
  submit   keep every lane with work supplied with a chain of 12 h jobs
           (--dependency=afterany:<previous>)
  collect  pull finished run dirs back into runs/ (never overwriting),
           recount n_done, commit once per completed arm, push the branch
  cycle    collect -> plan -> push -> submit, then print the manifest summary
  summary  print the manifest summary only

Nothing here ever deletes or overwrites a run directory: pulled runs are
staged and moved into place only where the target does not exist yet.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from campaign_run import MODEL_FAMILIES, TOKEN_BUDGETS, model_flags  # noqa: E402

RUNS = REPO / "runs"
ADD = REPO / "campaign" / "addendum"
MANIFEST = ADD / "manifest.csv"
PROGRESS = ADD / "PROGRESS.md"
LANES_DIR = ADD / "lanes"
STATE = LANES_DIR / "state.json"
JOB_TMP = pathlib.Path(os.environ.get("CLAUDE_JOB_DIR", tempfile.gettempdir())) / "tmp"

HOST = "nibi"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ControlMaster=no", HOST]
REMOTE_HOME = "/home/billxby"
LANES = {
    "A": {"repo": f"{REMOTE_HOME}/projects/def-hongyanz/billxby/lossy-token-eff",
          "root": "/scratch/billxby/lossy-addendum/laneA", "exclude": "g[15-28]"},
    "B": {"repo": f"{REMOTE_HOME}/projects/def-hongyanz/billxby/lossy-token-eff-lane2",
          "root": "/scratch/billxby/lossy-addendum/laneB", "exclude": "g[1-14]"},
}
MAX_CHAIN = 4          # jobs per lane queued at once (running + pending); covers ~48 h if this Mac loses the link
# Nibi H100 SXM request time / old-box H100 PCIe request time, measured 2026-09-29 from strict seed-0
# runs of the same cases (old box 7.1 ms/token, Nibi 2.2-2.4 ms/token; longbench_v2 is prefill-bound
# on the old box: 72.6 s/case vs 4.7 s/case)
HW_FACTOR = {"longbench_v2": 0.12}
HW_DEFAULT = 0.33
STARTUP_S = 270.0      # per arm: stop + patch check/switch + server start (smoke test: 523 s cold, Sept logs ~5.7 min with the self-test)

BASE = ["gsm8k", "humaneval", "longbench_v2", "livecodebench", "mtbench", "aime24"]
N_CASES = {"gsm8k": 150, "humaneval": 150, "longbench_v2": 150, "livecodebench": 90, "mtbench": 80, "aime24": 30}
FIVE = ["mentored_dec", "cactus", "spec_casc_opt", "r_fuzzy", "spec_casc_tok"]
# strict runs on spec_casc_opt's carrier patch (scripts/lossy_methods.py), so the two
# adjacent cost one patch switch fewer per dataset
ARMS6 = ["strict", "spec_casc_opt", "mentored_dec", "cactus", "r_fuzzy", "spec_casc_tok"]
GRID_51 = {"mentored_dec": [0.15, 0.35, 0.55, 0.75], "spec_casc_tok": [0.15, 0.35, 0.55, 0.8]}

FIELDS = ["step", "condition", "target", "dataset", "method", "alpha", "seeds", "run_root", "n_cases_target",
          "n_done", "status", "slurm_job_ids", "gpu_hours_est", "gpu_hours_actual", "notes"]
QWEN3_BLOCK = "blocked: Qwen3 needs the consolidated V2 sampler (cascade/DIRECTIONS.md D8), not obtainable yet -- see PROGRESS.md Needs Bill"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_qwen(ds: str) -> bool:
    return ds.endswith("_qwen3")


def base_of(ds: str) -> str:
    return ds.removesuffix("_qwen3")


def target_of(ds: str) -> str:
    return "qwen3-8b" if is_qwen(ds) else "gpt-oss-20b"


def params_dir(method: str, alpha: str) -> str:
    if method in ("strict", "baseline"):
        return method
    return f"alpha{float(alpha):g}".replace("-", "neg")


def fmt_alpha(a) -> str:
    return "strict" if a == "strict" else f"{float(a):g}"


def cases_for(ds: str) -> list[str]:
    return [f"case_{i:03d}" for i in range(1, N_CASES[base_of(ds)] + 1)]


def row_key(row: dict) -> str:
    return "|".join([row["condition"], row["dataset"], row["method"], row["alpha"], str(row["seeds"])])


# ---------------------------------------------------------------- selections

def loosest_alphas() -> dict[str, dict[str, str]]:
    """dataset -> method -> loosest chosen alpha (the max; every rule loosens as alpha grows)."""
    out: dict[str, dict[str, str]] = {}
    for base in BASE:
        for ds in (base, f"{base}_qwen3"):
            with (REPO / "campaign" / "results" / f"{ds}.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            out[ds] = {}
            for method in FIVE:
                alphas = [float(r["alpha"]) for r in rows if r["method"] == method]
                out[ds][method] = fmt_alpha(max(alphas))
    return out


# ------------------------------------------------------------ local run tree

_state_cache: dict[pathlib.Path, str] = {}


def local_state(run_dir: pathlib.Path) -> str:
    """ok | missing | other; 'ok' results are cached (runs are never rewritten)."""
    cached = _state_cache.get(run_dir)
    if cached == "ok":
        return cached
    run_json = run_dir / "run.json"
    if not run_json.is_file():
        state = "missing"
    else:
        try:
            state = "ok" if json.loads(run_json.read_text(encoding="utf-8")).get("status") == "ok" else "other"
        except (OSError, json.JSONDecodeError):
            state = "other"
    _state_cache[run_dir] = state
    return state


def row_run_dir(row: dict, case: str) -> pathlib.Path:
    return (REPO / row["run_root"] / row["dataset"] / row["method"] / params_dir(row["method"], row["alpha"])
            / case / f"seed_{row['seeds']}")


def missing_local(row: dict) -> list[str]:
    return [c for c in cases_for(row["dataset"]) if local_state(row_run_dir(row, c)) != "ok"]


_case_time_cache: dict[tuple, float | None] = {}


def mean_case_seconds(ds: str, method: str, alpha: str) -> float | None:
    key = (ds, method, alpha)
    if key not in _case_time_cache:
        root = RUNS / ds / method / params_dir(method, alpha)
        times = []
        for run_json in root.glob("case_*/seed_0/run.json"):
            try:
                data = json.loads(run_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("status") == "ok" and data.get("wall_time_seconds") is not None:
                times.append(float(data["wall_time_seconds"]))
        _case_time_cache[key] = sum(times) / len(times) if times else None
    return _case_time_cache[key]


def estimate_hours(row: dict, n_missing: int) -> float:
    if n_missing == 0:
        return 0.0
    ds, method, alpha = row["dataset"], row["method"], row["alpha"]
    per_case = mean_case_seconds(ds, method, alpha) if row["condition"] in ("main", "qwenT0.6") else None
    if per_case is None:
        per_case = mean_case_seconds(ds, "strict", "strict") or 60.0
    if row["condition"] == "lmdraft":
        per_case *= 1.3
    factor = HW_FACTOR.get(base_of(ds), HW_DEFAULT)
    return round((n_missing * per_case * factor + STARTUP_S) / 3600.0, 2)


# ------------------------------------------------------------------ the plan

def server_settings(condition: str) -> dict:
    s = {"num_spec": 6, "temperature": 1.0, "top_p": 1.0}
    if condition.startswith("nspec"):
        s["num_spec"] = int(condition.removeprefix("nspec"))
    elif condition.startswith("temp"):
        s["temperature"] = float(condition.removeprefix("temp"))
    elif condition == "qwenT0.6":
        s.update(temperature=0.6, top_p=0.95)
    return s


def make_row(step: str, condition: str, ds: str, method: str, alpha: str, seed: int, notes: str = "") -> dict:
    return {
        "step": step, "condition": condition, "target": target_of(ds), "dataset": ds, "method": method,
        "alpha": alpha, "seeds": str(seed),
        "run_root": "runs" if condition == "main" else f"runs/addendum/{condition}",
        "n_cases_target": str(N_CASES[base_of(ds)]), "n_done": "0", "status": "pending",
        "slurm_job_ids": "", "gpu_hours_est": "", "gpu_hours_actual": "", "notes": notes,
    }


def all_rows() -> tuple[list[dict], dict[str, list[str]]]:
    """Every addendum row in lane order, plus lane -> [row keys] (Qwen3 rows get no lane while blocked)."""
    loose = loosest_alphas()
    rows: list[dict] = []
    lanes: dict[str, list[str]] = {"A": [], "B": []}

    def add(row: dict, lane: str | None) -> None:
        rows.append(row)
        if lane and not is_qwen(row["dataset"]):
            lanes[lane].append(row_key(row))

    def arm_alpha(ds: str, arm: str) -> str:
        return "strict" if arm == "strict" else loose[ds][arm]

    # step 0.5 (added, see README): strict seed 0 at the campaign settings on Nibi -- the
    # hardware-matched reference for wall-time ratios of Nibi-produced cells (N_draft=6 row of
    # step 3, T=1.0 row of step 4.1, time ratios of the step 5.1 cells in step 5.2).
    for ds in ("gsm8k", "livecodebench"):
        add(make_row("0.5", "nibiref", ds, "strict", "strict", 0), "B")
    # step 2.1 -- lane A
    for fam in ("", "_qwen3"):
        for base in ("gsm8k", "humaneval", "mtbench", "livecodebench"):
            ds = base + fam
            for arm in ARMS6:
                for seed in (1, 2):
                    add(make_row("2.1", "main", ds, arm, arm_alpha(ds, arm), seed), "A")
    for ds in ("humaneval", "mtbench", "longbench_v2", "aime24"):
        add(make_row("0.5", "nibiref", ds, "strict", "strict", 0), "A")
    for ds in (f"{b}_qwen3" for b in BASE):
        add(make_row("0.5", "nibiref", ds, "strict", "strict", 0), None)
    # step 3 -- lane B
    for fam in ("", "_qwen3"):
        for k in (2, 3, 4, 8, 10):
            for base in ("gsm8k", "livecodebench"):
                add(make_row("3", f"nspec{k}", base + fam, "strict", "strict", 0), "B")
    # step 4.1 -- lane B
    for fam in ("", "_qwen3"):
        for temp in ("1.2", "1.5"):
            for base in ("gsm8k", "livecodebench"):
                add(make_row("4.1", f"temp{temp}", base + fam, "strict", "strict", 0), "B")
    # step 4.2 (Qwen3 only)
    for base in ("gsm8k", "livecodebench"):
        ds = base + "_qwen3"
        for arm in ARMS6:
            add(make_row("4.2", "qwenT0.6", ds, arm, arm_alpha(ds, arm), 0), None)
    # step 4.3 (Qwen3 only)
    for base in ("gsm8k", "livecodebench"):
        for arm, alpha in (("strict", "strict"), ("mentored_dec", "0.75"), ("cactus", "0.35"), ("spec_casc_tok", "0.8")):
            add(make_row("4.3", "lmdraft", base + "_qwen3", arm, alpha, 0), None)
    # step 5.1 -- lane A: every grid alpha of the two rules whose cell is not complete yet
    for fam in ("", "_qwen3"):
        for base in BASE:
            ds = base + fam
            for method, grid in GRID_51.items():
                for a in grid:
                    row = make_row("5.1", "main", ds, method, fmt_alpha(a), 0)
                    if missing_local(row):
                        add(row, "A")
    # step 6 (+ step 2.2 for aime24 seeds 1-2) -- lane B, seed-major
    for fam in ("", "_qwen3"):
        ds = "aime24" + fam
        for seed in (1, 2, 3, 4):
            for arm in ARMS6:
                if seed <= 2 and (not fam or arm in ("strict", "spec_casc_opt", "r_fuzzy")):
                    step, note = "2.2", "seeds 1-2 shared by step 6"
                else:
                    step, note = "6", ""
                add(make_row(step, "main", ds, arm, arm_alpha(ds, arm), seed, note), "B")
    # step 2.2 longbench_v2 (GPT-OSS) -- lane B (moved from A at launch: A 18.3 h vs B 10.8 h estimated)
    for arm in ("strict", "spec_casc_opt", "mentored_dec", "r_fuzzy"):
        for seed in (1, 2):
            add(make_row("2.2", "main", "longbench_v2", arm, arm_alpha("longbench_v2", arm), seed), "B")
    return rows, lanes


def load_manifest() -> list[dict]:
    if not MANIFEST.is_file():
        return []
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_manifest(rows: list[dict]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})
    tmp.replace(MANIFEST)


def load_state() -> dict:
    if STATE.is_file():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"lanes": {name: {"jobs": [], "rows": []} for name in LANES}, "blocked_qwen3": True}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def lane_status_events(lane: str) -> list[dict]:
    path = LANES_DIR / f"{lane}_status.jsonl"
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def progress(line: str) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(f"- {utc_now()} {line}\n")


def work_item(row: dict, cases: list[str]) -> dict:
    ds = row["dataset"]
    family = MODEL_FAMILIES["qwen3" if is_qwen(ds) else "gpt_oss_20b"]
    flags = model_flags(*family)
    if row["condition"] == "lmdraft":
        flags = model_flags(family[0], "Qwen/Qwen3-0.6B", family[2], family[3])
    item = {
        "id": row_key(row), "step": row["step"], "condition": row["condition"], "dataset": ds,
        "method": row["method"], "alpha": row["alpha"], "seed": int(row["seeds"]), "cases": cases,
        "prompt_root": f"prompts/{ds}", "runs_subroot": row["run_root"],
        "max_new_tokens": TOKEN_BUDGETS[ds], "model_flags": flags, **server_settings(row["condition"]),
    }
    if row["condition"] == "lmdraft":
        item["env"] = {"SPEC_METHOD": "draft_model"}
    if row["condition"] == "qwenT0.6":
        item["extra_flags"] = ["--top-k", "20"]  # Qwen3's recommended sampler: T 0.6, top-p 0.95, top-k 20
    return item


def cmd_plan(args: argparse.Namespace) -> int:
    old = {row_key(r): r for r in load_manifest()}
    rows, lanes = all_rows()
    state = load_state()
    blocked_qwen = state.get("blocked_qwen3", True)
    # A row keeps the lane it first got (a row with progress in one lane's run root must never
    # move to another lane: skip-if-done only sees the lane's own root).
    lane_of = {}
    for lane, keys in lanes.items():
        for key in keys:
            lane_of[key] = lane
    for lane, info in state["lanes"].items():
        for key in info.get("rows", []):
            lane_of[key] = lane
    job_state = {j["id"]: j.get("state", "") for info in state["lanes"].values() for j in info.get("jobs", [])}
    active_item = {}
    for lane in LANES:
        started = {}
        for ev in lane_status_events(lane):
            if ev.get("event") == "item_start":
                started[ev["job"]] = ev["item"]
            elif ev.get("event") in ("item_end", "job_end"):
                started.pop(ev["job"], None)
        for job, item in started.items():
            if job_state.get(job) == "RUNNING":
                active_item[lane] = item

    out_rows = []
    work: dict[str, list[dict]] = {lane: [] for lane in LANES}
    order = {lane: [] for lane in LANES}
    for row in rows:
        key = row_key(row)
        prev = old.get(key, {})
        for keep in ("slurm_job_ids", "gpu_hours_actual", "notes"):
            if prev.get(keep):
                row[keep] = prev[keep]
        missing = missing_local(row)
        row["n_done"] = str(int(row["n_cases_target"]) - len(missing))
        row["gpu_hours_est"] = f"{estimate_hours(row, len(missing)):.2f}"
        lane = lane_of.get(key)
        if not missing:
            row["status"] = "done"
        elif is_qwen(row["dataset"]) and blocked_qwen:
            row["status"] = "blocked"
            if QWEN3_BLOCK not in row["notes"]:
                row["notes"] = "; ".join(x for x in (row["notes"], QWEN3_BLOCK) if x)
        elif lane is None:
            row["status"] = "pending"
        else:
            lane_jobs = [j for j in state["lanes"][lane]["jobs"] if j.get("state") in ("RUNNING", "PENDING")]
            if active_item.get(lane) == key:
                row["status"] = "running"
            elif lane_jobs:
                row["status"] = "queued"
            else:
                row["status"] = "pending"
            work[lane].append(work_item(row, missing))
            order[lane].append(key)
            tag = f"lane={lane}"
            if tag not in row["notes"]:
                row["notes"] = "; ".join(x for x in (tag, row["notes"]) if x)
        # job ids and measured hours from the lane journals
        if lane:
            jobs, secs = [], 0.0
            for ev in lane_status_events(lane):
                if ev.get("item") != key:
                    continue
                if ev.get("event") == "item_start" and ev["job"] not in jobs:
                    jobs.append(ev["job"])
                if ev.get("event") == "item_end":
                    secs += float(ev.get("elapsed_s") or 0.0)
            if jobs:
                row["slurm_job_ids"] = " ".join(jobs)
            if secs:
                row["gpu_hours_actual"] = f"{secs / 3600:.2f}"
        out_rows.append(row)

    write_manifest(out_rows)
    for lane in LANES:
        state["lanes"][lane]["rows"] = list(dict.fromkeys(state["lanes"][lane].get("rows", []) + order[lane]))
        path = LANES_DIR / f"{lane}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"lane": lane, "written": utc_now(), "items": work[lane]}, indent=1) + "\n",
                        encoding="utf-8")
    save_state(state)
    if not args.quiet:
        print_summary(out_rows)
    return 0


def print_summary(rows: list[dict]) -> None:
    from collections import Counter, defaultdict
    by_status = Counter(r["status"] for r in rows)
    hours = defaultdict(float)
    for r in rows:
        if r["status"] in ("running", "queued", "pending"):
            hours[r["notes"].split(";")[0] if r["notes"].startswith("lane=") else "unassigned"] += float(r["gpu_hours_est"] or 0)
    print(f"manifest: {len(rows)} rows; " + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
    print("est. GPU-hours remaining by lane: " + ", ".join(f"{k}: {v:.1f}" for k, v in sorted(hours.items())))
    steps = defaultdict(Counter)
    for r in rows:
        steps[r["step"]][r["status"]] += 1
    for step in sorted(steps, key=lambda s: [float(x) for x in s.split("/")[0].split(".")]):
        print(f"  step {step}: " + ", ".join(f"{k}={v}" for k, v in sorted(steps[step].items())))


def cmd_summary(args: argparse.Namespace) -> int:
    print_summary(load_manifest())
    return 0


# ------------------------------------------------------------------- remote

def ssh(command: str, *, input_bytes: bytes | None = None, check: bool = True, timeout: float = 600) -> subprocess.CompletedProcess:
    return subprocess.run([*SSH, command], input=input_bytes, capture_output=True, check=check, timeout=timeout)


PUSH_FILES = [
    "scripts/addendum_lane.py", "cascade/cluster/addendum_lane.sbatch", "cascade/cluster/addendum_smoke.sbatch",
    "cascade/cluster/addendum_grade.sbatch", "scripts/addendum_grade.py",
    "scripts/persistent_arm_replay.py", "scripts/fresh_server_replay.py", "scripts/run_experiment_vllm.py",
    "scripts/lossy_methods.py", "scripts/campaign_run.py", "remote/run_server_vllm.sh", "remote/stop_server.sh",
    "patches/apply.sh", "patches/HASHES.txt",
]


def cmd_push(args: argparse.Namespace) -> int:
    files = [f for f in PUSH_FILES if (REPO / f).is_file()]
    tar = subprocess.run(["tar", "-cf", "-", *files], cwd=REPO, capture_output=True, check=True).stdout
    for lane, info in LANES.items():
        ssh(f"cd {shlex.quote(info['repo'])} && tar -xf -", input_bytes=tar)
        work = (LANES_DIR / f"{lane}.json").read_bytes()
        root = shlex.quote(info["root"])
        ssh(f"mkdir -p {root}/slurm && cat > {root}/work.json.tmp && mv {root}/work.json.tmp {root}/work.json",
            input_bytes=work)
        n = len(json.loads(work)["items"])
        print(f"pushed {len(files)} code files + work list ({n} items) to lane {lane}")
    return 0


def squeue_states() -> dict[str, str]:
    out = ssh("squeue -u billxby -h -o '%i|%T'", check=False).stdout.decode()
    states = {}
    for line in out.splitlines():
        if "|" in line:
            job, st = line.strip().split("|", 1)
            states[job] = st
    return states


def refresh_job_states(state: dict) -> dict[str, str]:
    live = squeue_states()
    for info in state["lanes"].values():
        for job in info.get("jobs", []):
            if job["id"] in live:
                job["state"] = live[job["id"]]
            elif job.get("state") in ("PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "", None):
                job["state"] = "ENDED"
    return live


def cmd_submit(args: argparse.Namespace) -> int:
    state = load_state()
    refresh_job_states(state)
    manifest = {row_key(r): r for r in load_manifest()}
    for lane, info in LANES.items():
        items = json.loads((LANES_DIR / f"{lane}.json").read_text(encoding="utf-8"))["items"]
        if not items:
            continue
        remaining_h = sum(float(manifest.get(i["id"], {}).get("gpu_hours_est") or 0) for i in items)
        want = max(1, min(MAX_CHAIN, int(remaining_h / 11.0) + 1))
        jobs = state["lanes"][lane]["jobs"]
        active = [j for j in jobs if j.get("state") in ("PENDING", "RUNNING", "CONFIGURING", "COMPLETING")]
        while len(active) < want:
            dep = f"--dependency=afterany:{active[-1]['id']} " if active else ""
            cmd = (
                f"cd {shlex.quote(info['repo'])} && mkdir -p {info['root']}/slurm && "
                f"LANE={lane} REPO_DIR={shlex.quote(info['repo'])} LANE_ROOT={info['root']} "
                f"sbatch --parsable --job-name=add-{lane} --exclude={info['exclude']} "
                f"--output={info['root']}/slurm/%x-%j.out {dep}cascade/cluster/addendum_lane.sbatch"
            )
            out = ssh(cmd).stdout.decode().strip().splitlines()[-1]
            job_id = out.split(";")[0].strip()
            job = {"id": job_id, "state": "PENDING", "submitted": utc_now(), "dependency": active[-1]["id"] if active else ""}
            jobs.append(job)
            active.append(job)
            progress(f"lane {lane}: submitted job {job_id}" + (f" (afterany:{job['dependency']})" if job["dependency"] else "")
                     + f"; lane has {len(items)} work items, est. {remaining_h:.1f} GPU-h")
            print(f"lane {lane}: submitted {job_id} {('after ' + job['dependency']) if job['dependency'] else ''}")
    save_state(state)
    return 0


# ------------------------------------------------------------------ collect

def pull_lane_runs(lane: str, info: dict) -> list[str]:
    """Pull every ok run dir from the lane's run root that does not exist locally. Returns rel paths."""
    root = info["root"]
    script = (
        f"cd {root} 2>/dev/null || exit 0; T=$(date +%s); "
        f"if [ -f .collect_marker ]; then F='-newer .collect_marker'; else F=''; fi; "
        f"find runs -name run.json $F 2>/dev/null | xargs -r grep -l '\"status\": \"ok\"' ; echo \"__T=$T\""
    )
    out = ssh(script, timeout=900).stdout.decode().splitlines()
    stamp = next((l.split("=", 1)[1] for l in out if l.startswith("__T=")), None)
    rels = [l.strip()[: -len("/run.json")] for l in out if l.strip().endswith("/run.json")]
    new = [r for r in rels if not (REPO / r).exists()]
    pulled = []
    if new:
        JOB_TMP.mkdir(parents=True, exist_ok=True)
        stage = pathlib.Path(tempfile.mkdtemp(prefix=f"pull_{lane}_", dir=JOB_TMP))
        listing = ("\n".join(new) + "\n").encode()
        proc = subprocess.run([*SSH, f"cd {root} && tar -cf - -T -"], input=listing, capture_output=True, timeout=1800)
        if proc.returncode != 0:
            raise RuntimeError(f"remote tar failed for lane {lane}: {proc.stderr.decode()[-500:]}")
        subprocess.run(["tar", "-xf", "-", "-C", str(stage)], input=proc.stdout, check=True)
        for rel in new:
            src, dst = stage / rel, REPO / rel
            if not (src / "run.json").is_file():
                continue
            if dst.exists():  # appeared meanwhile; never merge two runs' files
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dst)
            pulled.append(rel)
        shutil.rmtree(stage, ignore_errors=True)
    if stamp:
        ssh(f"cd {root} && touch -d @{stamp} .collect_marker", check=False)
    # journals and batch manifests (small; our own copies, refreshed every collect)
    status = ssh(f"cat {root}/status.jsonl 2>/dev/null", check=False).stdout
    if status:
        (LANES_DIR / f"{lane}_status.jsonl").write_bytes(status)
    return pulled


def git(*argv: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *argv], cwd=REPO, capture_output=True, text=True, check=check)


COAUTHOR = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"


def commit(message: str, paths: list[str]) -> bool:
    git("add", "--", *paths)
    if not git("diff", "--cached", "--quiet", check=False).returncode:
        return False
    git("commit", "-q", "-m", message + COAUTHOR)
    return True


def cmd_collect(args: argparse.Namespace) -> int:
    state = load_state()
    refresh_job_states(state)
    save_state(state)
    before = {row_key(r): r for r in load_manifest()}
    total = 0
    for lane, info in LANES.items():
        try:
            pulled = pull_lane_runs(lane, info)
        except (RuntimeError, subprocess.SubprocessError) as exc:
            progress(f"lane {lane}: collect FAILED ({exc}); will retry next cycle")
            print(f"lane {lane}: collect failed: {exc}", file=sys.stderr)
            continue
        total += len(pulled)
        if pulled:
            progress(f"lane {lane}: pulled {len(pulled)} new run dir(s) into runs/")
    # recount (plan writes the manifest) and commit once per newly completed arm
    cmd_plan(argparse.Namespace(quiet=True))
    after = load_manifest()
    done_now = [r for r in after if r["status"] == "done" and before.get(row_key(r), {}).get("status") not in ("done", None)]
    # rows that were never in the old manifest but are done already (first plan) are not "completed arms" of this run
    staged = ["campaign/addendum/manifest.csv", "campaign/addendum/PROGRESS.md", "campaign/addendum/lanes"]
    for row in done_now:
        progress(f"step {row['step']} {row['condition']} {row['dataset']} {row['method']} alpha={row['alpha']} "
                 f"seed={row['seeds']}: done, {row['n_done']}/{row['n_cases_target']} cases "
                 f"(jobs {row['slurm_job_ids'] or '-'}, {row['gpu_hours_actual'] or '?'} GPU-h)")
        msg = (f"addendum: step{row['step']} {row['condition']} {row['dataset']} {row['method']} "
               f"alpha={row['alpha']} seed={row['seeds']}: {row['n_done']}/{row['n_cases_target']} cases")
        commit(msg, staged)
    if total and not done_now:
        commit(f"addendum: progress {utc_now()} ({total} runs pulled, no arm completed)", staged)
    if not args.no_push:
        pushed = git("push", "-q", "origin", "addendum-oct2026", check=False)
        if pushed.returncode != 0:
            print(f"git push failed: {pushed.stderr[-300:]}", file=sys.stderr)
    print(f"collect: {total} run dir(s) pulled, {len(done_now)} arm(s) completed")
    return 0


# ------------------------------------------------------------------ grading

MIRROR = "/scratch/billxby/lossy-addendum/mirror"
GRADES_LOCAL = ADD / "analysis" / "grades.csv"
UPLOADED = JOB_TMP / "mirror_uploaded.txt"


def local_run_rels() -> list[str]:
    """Every run dir under runs/ (campaign datasets + runs/addendum/<condition>/), relative to runs/."""
    rels = []
    for base in BASE:
        for ds in (base, f"{base}_qwen3"):
            rels += [str(p.parent.relative_to(RUNS)) for p in (RUNS / ds).glob("*/*/case_*/seed_*/run.json")]
    addendum = RUNS / "addendum"
    if addendum.is_dir():
        rels += [str(p.parent.relative_to(RUNS)) for p in addendum.glob("*/*/*/*/case_*/seed_*/run.json")]
    return sorted(rels)


def cmd_grade(args: argparse.Namespace) -> int:
    """Upload not-yet-graded runs to the Nibi mirror and submit one CPU grading job."""
    import io
    import tarfile

    graded = set()
    if GRADES_LOCAL.is_file():
        with GRADES_LOCAL.open(newline="", encoding="utf-8") as handle:
            graded = {r["relpath"] for r in csv.DictReader(handle) if r.get("verdict")}
    uploaded = set(UPLOADED.read_text().split()) if UPLOADED.is_file() else set()
    new = [r for r in local_run_rels() if r not in graded and r not in uploaded]
    if new:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for rel in new:
                for name in ("run.json", "config.json", "output.txt"):
                    path = RUNS / rel / name
                    if path.is_file():
                        tar.add(path, arcname=f"{rel}/{name}")
        ssh(f"mkdir -p {MIRROR}/runs && cd {MIRROR}/runs && tar -xf -", input_bytes=buf.getvalue(), timeout=1800)
        UPLOADED.parent.mkdir(parents=True, exist_ok=True)
        with UPLOADED.open("a") as handle:
            handle.write("\n".join(new) + "\n")
        print(f"uploaded {len(new)} run dir(s) ({len(buf.getvalue()) / 1e6:.0f} MB) to {MIRROR}/runs")
    live = squeue_states()
    queued = ssh("squeue -u billxby -h -n add-grade -o %i", check=False).stdout.decode().split()
    if queued:
        print(f"grading job already queued/running: {' '.join(queued)}")
        return 0
    repo = LANES["A"]["repo"]
    out = ssh(f"cd {repo} && mkdir -p {MIRROR}/slurm && MIRROR={MIRROR} REPO_DIR={repo} "
              f"sbatch --parsable --output={MIRROR}/slurm/%x-%j.out cascade/cluster/addendum_grade.sbatch").stdout.decode().strip()
    progress(f"grading: uploaded {len(new)} run dir(s) to the Nibi mirror, submitted CPU grading job {out}")
    print(f"submitted grading job {out}")
    return 0


def cmd_grade_pull(args: argparse.Namespace) -> int:
    data = ssh(f"cat {MIRROR}/grades.csv", check=False).stdout
    if not data:
        print("no grades.csv on the mirror yet")
        return 1
    GRADES_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    GRADES_LOCAL.write_bytes(data)
    n = data.count(b"\n") - 1
    progress(f"grading: pulled {n} verdicts into campaign/addendum/analysis/grades.csv")
    print(f"pulled {n} verdicts -> {GRADES_LOCAL}")
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    cmd_collect(argparse.Namespace(no_push=True))
    cmd_plan(argparse.Namespace(quiet=True))
    cmd_push(args)
    cmd_submit(args)
    cmd_plan(argparse.Namespace(quiet=True))  # statuses reflect the jobs just submitted
    commit(f"addendum: cycle {utc_now()}", ["campaign/addendum/manifest.csv", "campaign/addendum/PROGRESS.md",
                                             "campaign/addendum/lanes"])
    git("push", "-q", "origin", "addendum-oct2026", check=False)
    print_summary(load_manifest())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--quiet", action="store_true"); p.set_defaults(fn=cmd_plan)
    sub.add_parser("push").set_defaults(fn=cmd_push)
    sub.add_parser("submit").set_defaults(fn=cmd_submit)
    p = sub.add_parser("collect"); p.add_argument("--no-push", action="store_true"); p.set_defaults(fn=cmd_collect)
    sub.add_parser("cycle").set_defaults(fn=cmd_cycle)
    sub.add_parser("summary").set_defaults(fn=cmd_summary)
    sub.add_parser("grade").set_defaults(fn=cmd_grade)
    sub.add_parser("grade-pull").set_defaults(fn=cmd_grade_pull)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
