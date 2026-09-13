# Setup: what must be true before `cascade/run.sh` can run

## Where things can run

| | old H100 box (Chiatzen's) | Nibi (Alliance) | this Mac |
|---|---|---|---|
| vLLM 0.26.0 + patches | installed, `.venv-vllm`, pristine-hash verified | build with `cascade/cluster/setup_nibi.sh` | no |
| GPT-OSS-20B + EAGLE3 | in `~/.cache/huggingface` | download in setup script | no |
| Qwen3-8B + speculator | yes, **and the only copy of the V2 consolidated sampler** (E8) | blocked until E8 | no |
| campaign `runs/` + traces | yes (`runs/`, gitignored) | fresh | only `old_runs/` (tracked; 1,226 traced runs) |
| E7 trace analysis | yes | yes | **yes — already run** |
| disk | ~3.8 GB free (binding constraint; traces off for big sweeps) | project space (large) | -- |

## Checklist: old box

1. `git pull` the `spec-casc` branch (this workspace is on it).
2. `bash cascade/run.sh E0` — installs and self-tests each new patch,
   including the GPU kernel test. Expect five "all ... checks passed".
3. Disk: `df -h .`; keep >= 3 GB. Fresh-mode runs write ~25 KB each without
   traces, a few MB each with traces (E1/E2/E5 fresh mode traces by
   default; add `--no-trace-proposals` by editing `run.sh`'s `campaign()`
   if space is tight — but E7-style analysis of the new variants needs the
   traces).
4. Nothing else is running on the GPU (`nvidia-smi`), and no stale server:
   `bash remote/stop_server.sh`.
5. `bash cascade/run.sh E1-gsm8k` (5 h fresh) or `--mode persistent` (25 min).

## Checklist: Nibi

1. Login works: `ssh nibi` (key + Duo push). As of 2026-09-11 the server
   still closes the session after a successful Duo — provisioning lag;
   retry, then support@tech.alliancecan.ca if it persists a day.
2. First-login checklist in `cluster/README.md` (`sshare -U`, `sinfo`,
   `module spider python cuda`, `diskusage_report`). Fix `MODULES` and
   the GPU type in `cluster/setup_nibi.sh` / `cluster/nibi_run.sbatch`
   accordingly (both take env overrides, no edit needed).
3. `git clone` into `~/projects/def-hongyanz/billxby/lossy-token-eff`
   (project space, not home).
4. `bash cascade/cluster/setup_nibi.sh` on the login node (internet):
   venvs, wheels, checkpoints, one patch self-test (CPU parts).
5. `bash cascade/cluster/nibi_interactive.sh`, then on the GPU node:
   `bash cascade/run.sh E0` (kernel tests need the GPU).
6. Submit: `bash cascade/run.sh E1-gsm8k --target nibi` (goes through
   `cluster/nibi_run.sbatch`); `squeue -u $USER`; output in `casc-<jobid>.out`.
7. Results come back with `rsync -avz nibi:projects/def-hongyanz/billxby/lossy-token-eff/campaign/ campaign/`
   (and `cascade/results/`). Never run `*_qwen3` datasets there until E8.

Unverified assumptions, in order of likelihood to bite: module names
(`StdEnv/2023 python/3.12 cuda/12.6`), the GPU gres string (`h100`),
whether the vLLM cu129 wheel imports under Nibi's toolchain (fallback:
Apptainer `vllm/vllm-openai:v0.26.0`), and whether compute nodes have
internet (the scripts assume not: `HF_HUB_OFFLINE=1`, downloads on login).

## What is verified vs not, for the new code

| item | verified how | not yet |
|---|---|---|
| 5 new patches apply to pristine v0.26.0 and reproduce their manifest hashes | offline on the Mac, then **live on Nibi 2026-09-11**: `apply.sh` installed all five against the real vLLM 0.26.0 with matching hashes | -- |
| their tests (plumbing, formula, Triton kernel) | **E0 on an H100 (job 21759794): all five "all ... checks passed"** | -- |
| registry / installer / server script / runner wiring | import + `bash -n` + `run.sh --dry-run` of every id | a live `apply.sh` on a real install |
| `speed_ignoring_accuracy.py`, `trace_rank_analysis.py` | run on real campaign tables / `old_runs` traces | -- |
| `campaign_report.py` extension (any calibrated method in results/graphs by default; uncalibrated two-knob arms with `--include-uncalibrated`; grey fallback styles) | run end-to-end on `old_runs/aime24` (23 result rows incl. `_k8`/`_t28000`-style params, both PNGs rendered) | -- |
| `campaign_run.py` calibration **merge** (a `--methods` subset no longer overwrites other methods' chosen alphas; new methods matched to the existing l̄ targets unless `--retarget`) | refactored selection reproduces every recorded `campaign/calibration/*.json` (8/8 datasets: identical targets and chosen alphas); add-on path unit-tested | a live add-on run |
| `timing_report.py` | run on `old_runs/humaneval` (no baseline arm there, so c_rel untested) | c_rel column on real E3 output |
| cluster scripts | `bash -n` only | any Nibi login |

## Recovering the V2 file (E8) and other one-time chores

- E8 commands: `EXPERIMENTS.md`. 30 minutes with old-box access.
- Pull the campaign traces if E7-style analysis of the *campaign* alphas is
  wanted (old_runs only has the original single-alpha runs):
  `rsync -avz --include='*/' --include='proposals.jsonl' --include='run.json' --exclude='*' box:lossy-token-eff/runs/ runs/`
  (they are large for aime24; gsm8k/humaneval are small).
- MT-Bench has no grader (D9) — an LLM-judge script would be new work.
