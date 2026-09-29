# Addendum campaign progress

Append-only log (UTC). The manifest (`manifest.csv`) is the source of truth
for what is done; this file records every action and failure.

## Needs Bill

1. **Qwen3 V2 sampler (step 0.2) -- blocks every Qwen3 row (135 of 253).**
   The consolidated `rejection_sampler_utils.py` exists only on Chiatzen's
   old H100 box (`cascade/DIRECTIONS.md` D8); neither Nibi venv nor this Mac
   has it (both Nibi copies are pristine, sha256 `bfaec14e...`). Ask: copy
   `lossy-token-eff/.venv-vllm/lib/python3.12/site-packages/vllm/v1/worker/gpu/spec_decode/rejection_sampler_utils.py`
   from that box to `~/Downloads/rejection_sampler_utils.py` on the Mac. Its
   sha256 should be `68d0a904230a82d7aa90916e9ed60297e3c725eeb0188b633893e03fb5b9f938`
   (`patches/HASHES.txt`, label `mentored-dec`, the final 2026-08-23 state).
   Then: diff vs pristine -> `patches/vllm-0.26.0-v2-consolidated.patch`,
   install in both lane venvs, Qwen3 smoke tests, and the Qwen3 rows start.
   Option if waiting is costly: the strict-only Qwen3 rows (steps 0.5, 3,
   4.1) do not exercise any relaxed rule and could run on pristine V2 now --
   but the existing Qwen3 strict data ran on the consolidated file at neutral
   alphas, so comparability would rest on that file being a no-op at neutral
   alphas. Not done without your say-so.
2. **MT-Bench judge API key (step 1.9).** No `ANTHROPIC_API_KEY` /
   `OPENAI_API_KEY` in this environment. Ask: put one in
   `~/.config/lossy-token-eff/judge.env` (`ANTHROPIC_API_KEY=...` or
   `OPENAI_API_KEY=...`, `chmod 600`). Step 1.9 is skipped until then.
3. **Duo.** The Nibi link is one ControlMaster session opened 2026-09-29
   05:25Z with a keepalive channel. If it drops, queued jobs keep running on
   Nibi (lanes are chained up to ~48 h ahead) but nothing is pulled back or
   resubmitted until one more Duo push is approved.

## Log

- 2026-09-29T05:25Z Step 0.1: Nibi login OK (one Duo push; ControlMaster + keepalive channel). `sshare`: def-hongyanz_gpu fair-share 0.33; /project 120/931 GiB, 288K/500K files; scratch 152 MiB/1 TiB.
- 2026-09-29T05:33Z Found: lane 1's `runs/` on Nibi holds the September E1/E1F/E1P runs at campaign paths (e.g. gsm8k/strict/strict seeds 0-2, aime24/spec_casc_tok/alpha0.8 seed 0) -- different runs from the Mac's seed-0 data. Decision: every lane writes to its own clean run root under /scratch (README "Run roots and provenance").
- 2026-09-29T05:33Z Found: `cascade/cluster/sync_to_nibi.sh` uses `--delete-excluded` with `/runs/`, `/logs/` and `.venv*` excluded, which deletes exactly those directories on the receiving side. Not used; code is pushed with tar (no deletes).
- 2026-09-29T05:37Z Step 0.2: consolidated V2 file not obtainable (not on Nibi -- both venvs pristine `bfaec14e...` -- not on this Mac, old box unreachable from here). Every Qwen3 row marked `blocked`; ask under Needs Bill.
- 2026-09-29T05:40Z Step 0.3: pre-downloaded into `~/projects/def-hongyanz/billxby/hf` on the login node: Qwen/Qwen3-8B, RedHatAI/Qwen3-8B-speculator.eagle3, Qwen/Qwen3-0.6B; confirmed openai/gpt-oss-20b (39G incl. all formats) + nebius/EAGLE3-gpt-oss-20b present.
- 2026-09-29T05:50Z Step 0.1 smoke test PASSED: job 22873241 on g1 (H100 80GB HBM3, driver 580.82.07), GPT-OSS gsm8k case_001, `persistent_arm_replay.py` strict, request seed 7, scratch run root (deleted afterwards). Startup (patch switch to spec-casc-opt carrier + self-test + server start) 522.9 s; generation 1.04 s (68 tokens, l_bar 2.24, finish=stop, final channel reached, ordinal 1); job total 9 min 05 s.
- 2026-09-29T05:52Z Step 0.4: lanes = the two existing repo+venv copies (A: lossy-token-eff, nodes g1-g14; B: lossy-token-eff-lane2, nodes g15-g28). No lane C while Qwen3 is blocked (file quota; README deviation 3).
- 2026-09-29T05:52Z Measured speed: strict seed-0 request time per output token, old box 7.06-7.51 ms vs Nibi (E1P runs) 2.20-2.45 ms (gsm8k, humaneval, livecodebench, aime24, mtbench); longbench_v2 72.6 s/case vs 4.7 s/case (prefill-bound on the old box). Added step 0.5 `nibiref` (README deviation 1).
- 2026-09-29T05:52Z Per-arm overhead: Sept-16 Nibi server log shows ~3 min of `apply.sh` (two `import vllm` + the method self-test) before the server even starts, then ~2.7 min to healthy. Added opt-in `APPLY_SKIP_TEST_IF_APPLIED` (README deviation 2).
- 2026-09-29T05:53Z Plan: 253 manifest rows (118 GPT-OSS pending, 135 Qwen3 blocked); step 5.1 missing cells = 41 (18 GPT-OSS + 23 Qwen3) as expected. Estimated GPU time: lane A 14.7 h, lane B 14.4 h (step 2.2 longbench_v2 moved from lane A to lane B to balance).
- 2026-09-29T05:56:07Z lane A: submitted job 22880871; lane has 70 work items, est. 14.7 GPU-h
- 2026-09-29T05:56:15Z lane A: submitted job 22880999 (afterany:22880871); lane has 70 work items, est. 14.7 GPU-h
- 2026-09-29T05:56:23Z lane B: submitted job 22881159; lane has 48 work items, est. 14.4 GPU-h
- 2026-09-29T05:56:30Z lane B: submitted job 22881281 (afterany:22881159); lane has 48 work items, est. 14.4 GPU-h
- 2026-09-29T06:14:41Z lane A: pulled 300 new run dir(s) into runs/
- 2026-09-29T06:14:50Z lane B: pulled 173 new run dir(s) into runs/
- 2026-09-29T06:14:52Z step 0.5 nibiref gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.14 GPU-h)
- 2026-09-29T06:14:53Z step 2.1 main gsm8k strict alpha=strict seed=1: done, 150/150 cases (jobs 22880871, 0.11 GPU-h)
- 2026-09-29T06:14:53Z step 2.1 main gsm8k strict alpha=strict seed=2: done, 150/150 cases (jobs 22880871, 0.09 GPU-h)
