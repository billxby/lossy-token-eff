# NAACL-2027 addendum campaign

Started 2026-09-29 on branch `addendum-oct2026`. Everything the paper needs
from this campaign lives here; the paper's own tables (`campaign/tables/*.csv`,
`campaign/results/*.csv`) are never touched.

| file | what |
|---|---|
| `manifest.csv` | single source of truth: one row per (step, condition, dataset, method, alpha, seed) arm; `n_done` is recounted from `runs/` every cycle |
| `PROGRESS.md` | append-only action log (UTC); "Needs Bill" at the top |
| `lanes/<lane>.json` | the ordered work list each Nibi lane runs (regenerated every cycle) |
| `lanes/<lane>_status.jsonl` | copy of the lane's own journal on Nibi (item start/end, job, elapsed) |
| `lanes/state.json` | Slurm job chain per lane |
| `analysis/` | step 1 (zero-GPU) CSVs, each with a sibling line in `analysis/README.md` |
| `seeds/`, `tables/`, `best_setting.csv`, `aime24_repeats.csv` | steps 2-6 outputs |
| `RESULTS.md` | every number the paper will quote, with its CSV path and row |

## How it runs

- `scripts/addendum_campaign.py cycle` (Mac): pull finished runs back ->
  recount -> rewrite `manifest.csv` and the lane work lists -> push code and
  work lists to Nibi -> keep every lane's Slurm chain supplied -> commit
  (one commit per completed arm) and push the branch.
- `cascade/cluster/addendum_lane.sbatch` -> `scripts/addendum_lane.py`
  (Nibi, one H100 per job, `--time` 12 h, chained `afterany`): runs the
  lane's work list through `scripts/persistent_arm_replay.py` (one server
  per arm+seed, `--no-trace-proposals`), skip-if-done per case.
- Two lanes (user request 2026-09-29: "like 2 GPUs"), each with its own repo
  + `.venv-vllm` copy and a disjoint node set (`remote/stop_server.sh` kills
  every vLLM process of the user on a node; knob files are node-local):
  lane A = `~/projects/def-hongyanz/billxby/lossy-token-eff`, nodes g1-g14;
  lane B = `.../lossy-token-eff-lane2`, nodes g15-g28.

## Run roots and provenance

Each lane writes only to its own run root, `/scratch/billxby/lossy-addendum/lane<L>/runs`,
laid out exactly like the repo's `runs/`. Finished run dirs (run.json with
`status: ok`) are pulled into the repo's `runs/` tree only where the target
directory does not exist yet (staged, then moved; never merged, never
overwritten). Failed or interrupted run dirs on Nibi are moved to
`<lane root>/quarantine/`, not deleted.

Why not the repo copies' own `runs/` on Nibi: they already hold September
cascade-workspace runs (E1/E1F/E1P, `cascade/RESULTS.md`) at the same paths
as the campaign tree -- e.g. `gsm8k/strict/strict/case_*/seed_{0,1,2}` -- that
are different runs from the Mac's (old-box) seed-0 data. Running there would
make skip-if-done silently reuse them. The addendum therefore produces all of
its own runs; the E1P runs stay untouched on Nibi.

- `runs/<dataset>/<method>/<params>/case_NNN/seed_<k>/`: new seeds (steps 2, 5.2, 6) and the
  missing step-5.1 alphas (seed 0), exactly where the campaign's tree puts them.
- `runs/addendum/<condition>/<dataset>/...`: server-setting changes --
  `nspec<k>` (step 3), `temp<T>` (step 4.1), `qwenT0.6` (step 4.2), `lmdraft` (step 4.3),
  `nibiref` (step 0.5, below).

## Settings (unchanged from the campaign)

EAGLE-3 drafters, N_draft 6, temperature 1.0, top-p 1.0, server seed 0 (the
request seed is the `seed_<k>` value), vLLM 0.26.0 with the repo patches,
Qwen3 YaRN 65,536 via `MODEL_FAMILIES`, the campaign token budgets and case
counts. Loosest alpha per rule = the maximum alpha in
`campaign/results/<dataset>.csv` for that method (every rule loosens as its
alpha grows).

## Additions and deviations (each also logged in PROGRESS.md)

1. **Step 0.5, Nibi hardware reference (added).** All existing seed-0 data
   ran on the old box's H100 PCIe; Nibi's H100 SXM is ~3x faster per token
   (measured: 7.1 vs 2.2-2.4 ms/token on the same strict cases). Wall-time
   ratios of cells produced on Nibi need a Nibi strict baseline: `nibiref` =
   strict, seed 0, campaign settings, all cases. It is the N_draft = 6 row of
   step 3, the T = 1.0 row of step 4.1, and the time denominator for the step
   5.1 cells in step 5.2. Step-2 and step-6 ratios compare arms of the same
   seed, all produced on Nibi, so they need no reference.
2. **`patches/apply.sh`: `APPLY_SKIP_TEST_IF_APPLIED`.** Opt-in (set only by
   `addendum_lane.sbatch`): when the requested patch is already installed
   with a matching sha256, its self-test is skipped (~2.5 min of GPU per
   arm). Any fresh apply or switch still runs the test. Default behaviour
   unchanged.
3. **Lane C (Qwen3) not created while Qwen3 is blocked.** /project has a
   500K-file quota (288K used); a third repo + venv copy is ~100K files. Qwen3
   work goes to lanes A/B once the V2 sampler is available.
4. **Step 2.2 aime24 seeds 1-2 are the same runs as step 6 seeds 1-2** (one
   manifest row each, step `2.2`, noted "shared by step 6").
