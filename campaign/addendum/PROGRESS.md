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
2. ~~MT-Bench judge API key (step 1.9)~~ -- resolved 2026-09-29 13:29Z (`~/.config/lossy-token-eff/judge.env`, now mode 600).
3. **Duo.** The Nibi link is one ControlMaster session opened 2026-09-29
   05:25Z with a keepalive channel. If it drops, queued jobs keep running on
   Nibi (lanes are chained up to ~48 h ahead) but nothing is pulled back or
   resubmitted until one more Duo push is approved.
4. **SPEED-Bench HLE prompts (step 7) -- 208 of 880 cases.** Humanities
   (72/80), Math (62/80) and STEM (74/80) come from `cais/hle`, a gated
   Hugging Face dataset (auto-approved on request). Ask: accept the terms at
   https://huggingface.co/datasets/cais/hle with your HF account, create a
   read token at https://huggingface.co/settings/tokens, and save it on the
   Mac as `~/.cache/huggingface/token` (mode 600; do not paste it in chat).
   Then `scripts/build_speedbench_prompts.py` adds the 208 prompts, the Math
   budget pilot runs, and those cases join every arm. Everything else in
   step 7 runs without it.
5. **MT-Bench judge (step 1.9) -- decision.** Batch
   `msgbatch_01MWf6AJLXcXd9ep5uFx5a7v` (2070 requests, claude-fable-5-1,
   ~$89 at batch price) was submitted 13:31Z and still showed 0 processed at
   18:27Z. Option: cancel it and judge the same requests directly (~$178,
   about an hour). Not done without your say-so; the collector keeps waiting.

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
- 2026-09-29T06:19:30Z grading: uploaded 18265 run dir(s) to the Nibi mirror, submitted CPU grading job 22892393
- 2026-09-29T05:56Z Launched: lane A jobs 22880871 -> 22880999 (afterany), lane B jobs 22881159 -> 22881281 (afterany); 70 + 48 work items. Both started ~06:00Z (g3, g18).
- 2026-09-29T06:19Z Grading mirror: 18,265 campaign run dirs (run.json + config.json + output.txt, 483 MB) uploaded to /scratch/billxby/lossy-addendum/mirror; CPU job 22892393 graded all of them in 5 min (06:19-06:24Z).
- 2026-09-29T06:23Z FAILURE lane A, job 22880871: `main|gsm8k|mentored_dec|0.75|1` attempt 1 exited 1 after 96 s -- patches/test_mentored_dec.py's V2 plumbing check fails on Nibi (V2 file pristine); V1 patch installed and V1 kernel checks passed. Attempt 2 ran (patch already installed -> self-test skipped). Fix: MENTORED_DEC_TEST_V1_ONLY for GPT-OSS items (README deviation 5), verified on the login node (plumbing checks pass, V1 only).
- 2026-09-29T06:25Z Step 1 first pass: 60-cell Eq. 4 / rounds / time counts reproduce the paper exactly (33/38/27; 6 and 11 time losses); 20 cells are time losses beyond the 95% paired bootstrap interval.
- 2026-09-29T06:32:22Z grading: pulled 18265 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T06:33:05Z lane A: pulled 450 new run dir(s) into runs/
- 2026-09-29T06:33:22Z lane B: pulled 217 new run dir(s) into runs/
- 2026-09-29T06:33:24Z step 0.5 nibiref livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.27 GPU-h)
- 2026-09-29T06:33:24Z step 2.1 main gsm8k spec_casc_opt alpha=0.05 seed=1: done, 150/150 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T06:33:24Z step 2.1 main gsm8k spec_casc_opt alpha=0.05 seed=2: done, 150/150 cases (jobs 22880871, 0.09 GPU-h)
- 2026-09-29T06:33:25Z step 2.1 main gsm8k mentored_dec alpha=0.75 seed=1: done, 150/150 cases (jobs 22880871, 0.12 GPU-h)
- 2026-09-29T06:33:25Z step 3 nspec2 gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.12 GPU-h)
- 2026-09-29T06:41Z Step 1.9 prepared, not run: FastChat judge data in prompts/mtbench_judge/ (judge_prompts.jsonl sha256 fd283293..., question.jsonl 119565ad..., reference_answer_gpt-4.jsonl f957a5bc...); every campaign MT-Bench case maps to a FastChat question (case_007's HF copy says 'reprompt top-5 words' for q121's 'returns' -- matched by similarity, judged on the text the model saw). Blocked on credentials (Needs Bill 2).
- 2026-09-29T06:49:51Z lane A: pulled 450 new run dir(s) into runs/
- 2026-09-29T06:50:00Z lane B: pulled 90 new run dir(s) into runs/
- 2026-09-29T06:50:02Z step 2.1 main gsm8k mentored_dec alpha=0.75 seed=2: done, 150/150 cases (jobs 22880871, 0.11 GPU-h)
- 2026-09-29T06:50:03Z step 2.1 main gsm8k cactus alpha=0.35 seed=1: done, 150/150 cases (jobs 22880871, 0.13 GPU-h)
- 2026-09-29T06:50:03Z step 2.1 main gsm8k cactus alpha=0.35 seed=2: done, 150/150 cases (jobs 22880871, 0.09 GPU-h)
- 2026-09-29T06:50:03Z step 3 nspec2 livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.26 GPU-h)
- 2026-09-29T06:52:03Z grading: uploaded 1680 run dir(s) to the Nibi mirror, submitted CPU grading job 22898857
- 2026-09-29T06:52:05Z grading: pulled 18265 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T07:09:00Z lane A: pulled 450 new run dir(s) into runs/
- 2026-09-29T07:09:15Z lane B: pulled 240 new run dir(s) into runs/
- 2026-09-29T07:09:17Z step 2.1 main gsm8k r_fuzzy alpha=0.25 seed=1: done, 150/150 cases (jobs 22880871, 0.12 GPU-h)
- 2026-09-29T07:09:18Z step 2.1 main gsm8k r_fuzzy alpha=0.25 seed=2: done, 150/150 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T07:09:19Z step 2.1 main gsm8k spec_casc_tok alpha=0.8 seed=1: done, 150/150 cases (jobs 22880871, 0.09 GPU-h)
- 2026-09-29T07:09:19Z step 3 nspec3 gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.10 GPU-h)
- 2026-09-29T07:09:20Z step 3 nspec3 livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.25 GPU-h)
- 2026-09-29T07:10:05Z grading: uploaded 690 run dir(s) to the Nibi mirror, submitted CPU grading job 22899474
- 2026-09-29T07:10:07Z grading: pulled 19945 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T07:27:14Z lane A: pulled 376 new run dir(s) into runs/
- 2026-09-29T07:27:28Z lane B: pulled 217 new run dir(s) into runs/
- 2026-09-29T07:27:31Z step 2.1 main gsm8k spec_casc_tok alpha=0.8 seed=2: done, 150/150 cases (jobs 22880871, 0.08 GPU-h)
- 2026-09-29T07:27:31Z step 2.1 main humaneval strict alpha=strict seed=1: done, 150/150 cases (jobs 22880871, 0.15 GPU-h)
- 2026-09-29T07:27:31Z step 3 nspec4 gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.09 GPU-h)
- 2026-09-29T07:28:40Z grading: uploaded 593 run dir(s) to the Nibi mirror, submitted CPU grading job 22900432
- 2026-09-29T07:28:42Z grading: pulled 20635 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T07:45:08Z lane A: pulled 225 new run dir(s) into runs/
- 2026-09-29T07:45:25Z lane B: pulled 209 new run dir(s) into runs/
- 2026-09-29T07:45:27Z step 2.1 main humaneval strict alpha=strict seed=2: done, 150/150 cases (jobs 22880871, 0.14 GPU-h)
- 2026-09-29T07:45:28Z step 2.1 main humaneval spec_casc_opt alpha=0.05 seed=1: done, 150/150 cases (jobs 22880871, 0.18 GPU-h)
- 2026-09-29T07:45:28Z step 3 nspec4 livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.26 GPU-h)
- 2026-09-29T07:45:29Z step 3 nspec8 gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.10 GPU-h)
- 2026-09-29T07:46:13Z grading: uploaded 434 run dir(s) to the Nibi mirror, submitted CPU grading job 22902033
- 2026-09-29T07:46:14Z grading: pulled 21228 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T08:03:02Z lane A: pulled 299 new run dir(s) into runs/
- 2026-09-29T08:03:17Z lane B: pulled 213 new run dir(s) into runs/
- 2026-09-29T08:03:20Z step 2.1 main humaneval spec_casc_opt alpha=0.05 seed=2: done, 150/150 cases (jobs 22880871, 0.16 GPU-h)
- 2026-09-29T08:03:20Z step 2.1 main humaneval mentored_dec alpha=0.75 seed=1: done, 150/150 cases (jobs 22880871, 0.14 GPU-h)
- 2026-09-29T08:03:20Z step 3 nspec8 livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.29 GPU-h)
- 2026-09-29T08:03:21Z step 3 nspec10 gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.09 GPU-h)
- 2026-09-29T08:04:12Z grading: uploaded 512 run dir(s) to the Nibi mirror, submitted CPU grading job 22902756
- 2026-09-29T08:04:14Z grading: pulled 21662 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T08:21:15Z lane A: pulled 300 new run dir(s) into runs/
- 2026-09-29T08:21:31Z lane B: pulled 122 new run dir(s) into runs/
- 2026-09-29T08:21:34Z step 2.1 main humaneval mentored_dec alpha=0.75 seed=2: done, 150/150 cases (jobs 22880871, 0.14 GPU-h)
- 2026-09-29T08:21:34Z step 2.1 main humaneval cactus alpha=0.35 seed=1: done, 150/150 cases (jobs 22880871, 0.15 GPU-h)
- 2026-09-29T08:21:35Z step 3 nspec10 livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.30 GPU-h)
- 2026-09-29T08:22:24Z grading: uploaded 422 run dir(s) to the Nibi mirror, submitted CPU grading job 22903558
- 2026-09-29T08:22:26Z grading: pulled 22174 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T08:38:43Z lane A: pulled 300 new run dir(s) into runs/
- 2026-09-29T08:39:00Z lane B: pulled 183 new run dir(s) into runs/
- 2026-09-29T08:39:02Z step 2.1 main humaneval cactus alpha=0.35 seed=2: done, 150/150 cases (jobs 22880871, 0.17 GPU-h)
- 2026-09-29T08:39:03Z step 2.1 main humaneval r_fuzzy alpha=0.25 seed=1: done, 150/150 cases (jobs 22880871, 0.18 GPU-h)
- 2026-09-29T08:39:03Z step 4.1 temp1.2 gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.11 GPU-h)
- 2026-09-29T08:39:44Z grading: uploaded 483 run dir(s) to the Nibi mirror, submitted CPU grading job 22904152
- 2026-09-29T08:39:46Z grading: pulled 22596 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T08:55:51Z lane A: pulled 279 new run dir(s) into runs/
- 2026-09-29T08:56:08Z lane B: pulled 166 new run dir(s) into runs/
- 2026-09-29T08:56:10Z step 2.1 main humaneval r_fuzzy alpha=0.25 seed=2: done, 150/150 cases (jobs 22880871, 0.14 GPU-h)
- 2026-09-29T08:56:11Z step 4.1 temp1.2 livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.30 GPU-h)
- 2026-09-29T08:56:11Z step 4.1 temp1.5 gsm8k strict alpha=strict seed=0: done, 150/150 cases (jobs 22881159, 0.20 GPU-h)
- 2026-09-29T08:57:04Z grading: uploaded 445 run dir(s) to the Nibi mirror, submitted CPU grading job 22904566
- 2026-09-29T08:57:06Z grading: pulled 23079 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T09:12:51Z lane A: pulled 251 new run dir(s) into runs/
- 2026-09-29T09:13:03Z lane B: pulled 48 new run dir(s) into runs/
- 2026-09-29T09:13:06Z step 2.1 main humaneval spec_casc_tok alpha=0.8 seed=1: done, 150/150 cases (jobs 22880871, 0.17 GPU-h)
- 2026-09-29T09:13:07Z step 2.1 main humaneval spec_casc_tok alpha=0.8 seed=2: done, 150/150 cases (jobs 22880871, 0.14 GPU-h)
- 2026-09-29T09:13:07Z step 2.1 main mtbench strict alpha=strict seed=1: done, 80/80 cases (jobs 22880871, 0.12 GPU-h)
- 2026-09-29T09:14:40Z grading: uploaded 299 run dir(s) to the Nibi mirror, submitted CPU grading job 22904796
- 2026-09-29T09:14:42Z grading: pulled 23524 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T09:30:28Z lane A: pulled 240 new run dir(s) into runs/
- 2026-09-29T09:30:42Z lane B: pulled 42 new run dir(s) into runs/
- 2026-09-29T09:30:44Z step 2.1 main mtbench strict alpha=strict seed=2: done, 80/80 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T09:30:45Z step 2.1 main mtbench spec_casc_opt alpha=0.05 seed=1: done, 80/80 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T09:30:45Z step 2.1 main mtbench spec_casc_opt alpha=0.05 seed=2: done, 80/80 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T09:30:46Z step 4.1 temp1.5 livecodebench strict alpha=strict seed=0: done, 90/90 cases (jobs 22881159, 0.58 GPU-h)
- 2026-09-29T09:31:49Z grading: uploaded 282 run dir(s) to the Nibi mirror, submitted CPU grading job 22905093
- 2026-09-29T09:31:51Z grading: pulled 23823 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T09:47:34Z lane A: pulled 182 new run dir(s) into runs/
- 2026-09-29T09:47:44Z lane B: pulled 30 new run dir(s) into runs/
- 2026-09-29T09:47:47Z step 2.1 main mtbench mentored_dec alpha=0.75 seed=1: done, 80/80 cases (jobs 22880871, 0.13 GPU-h)
- 2026-09-29T09:47:48Z step 2.1 main mtbench mentored_dec alpha=0.75 seed=2: done, 80/80 cases (jobs 22880871, 0.09 GPU-h)
- 2026-09-29T09:47:48Z step 2.2 main aime24 strict alpha=strict seed=1: done, 30/30 cases (jobs 22881159, 0.28 GPU-h)
- 2026-09-29T09:48:13Z grading: uploaded 212 run dir(s) to the Nibi mirror, submitted CPU grading job 22905291
- 2026-09-29T09:48:16Z grading: pulled 24105 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T10:04:10Z lane A: pulled 218 new run dir(s) into runs/
- 2026-09-29T10:04:23Z lane B: pulled 24 new run dir(s) into runs/
- 2026-09-29T10:04:25Z step 2.1 main mtbench cactus alpha=0.35 seed=1: done, 80/80 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T10:04:26Z step 2.1 main mtbench cactus alpha=0.35 seed=2: done, 80/80 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T10:04:26Z step 2.1 main mtbench r_fuzzy alpha=0.25 seed=1: done, 80/80 cases (jobs 22880871, 0.11 GPU-h)
- 2026-09-29T10:04:51Z grading: uploaded 242 run dir(s) to the Nibi mirror, submitted CPU grading job 22905529
- 2026-09-29T10:04:55Z grading: pulled 24317 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T10:20:39Z lane A: pulled 215 new run dir(s) into runs/
- 2026-09-29T10:20:52Z lane B: pulled 24 new run dir(s) into runs/
- 2026-09-29T10:20:54Z step 2.1 main mtbench r_fuzzy alpha=0.25 seed=2: done, 80/80 cases (jobs 22880871, 0.10 GPU-h)
- 2026-09-29T10:20:55Z step 2.1 main mtbench spec_casc_tok alpha=0.8 seed=1: done, 80/80 cases (jobs 22880871, 0.11 GPU-h)
- 2026-09-29T10:20:55Z step 2.2 main aime24 spec_casc_opt alpha=0.05 seed=1: done, 30/30 cases (jobs 22881159, 0.39 GPU-h)
- 2026-09-29T10:21:26Z grading: uploaded 239 run dir(s) to the Nibi mirror, submitted CPU grading job 22905739
- 2026-09-29T10:21:29Z grading: pulled 24559 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T10:37:34Z lane A: pulled 115 new run dir(s) into runs/
- 2026-09-29T10:37:46Z lane B: pulled 28 new run dir(s) into runs/
- 2026-09-29T10:37:49Z step 2.1 main mtbench spec_casc_tok alpha=0.8 seed=2: done, 80/80 cases (jobs 22880871, 0.12 GPU-h)
- 2026-09-29T10:37:49Z step 2.1 main livecodebench strict alpha=strict seed=1: done, 90/90 cases (jobs 22880871, 0.26 GPU-h)
- 2026-09-29T10:37:50Z step 2.2 main aime24 mentored_dec alpha=0.75 seed=1: done, 30/30 cases (jobs 22881159, 0.30 GPU-h)
- 2026-09-29T10:38:26Z grading: uploaded 143 run dir(s) to the Nibi mirror, submitted CPU grading job 22905902
- 2026-09-29T10:38:28Z grading: pulled 24798 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T10:54:09Z lane A: pulled 90 new run dir(s) into runs/
- 2026-09-29T10:54:17Z lane B: pulled 19 new run dir(s) into runs/
- 2026-09-29T10:54:20Z step 2.1 main livecodebench strict alpha=strict seed=2: done, 90/90 cases (jobs 22880871, 0.25 GPU-h)
- 2026-09-29T10:54:21Z step 2.2 main aime24 cactus alpha=0.18 seed=1: done, 30/30 cases (jobs 22881159, 0.30 GPU-h)
- 2026-09-29T10:54:42Z grading: uploaded 109 run dir(s) to the Nibi mirror, submitted CPU grading job 22906204
- 2026-09-29T10:54:46Z grading: pulled 24941 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T11:10:28Z lane A: pulled 90 new run dir(s) into runs/
- 2026-09-29T11:10:40Z lane B: pulled 25 new run dir(s) into runs/
- 2026-09-29T11:10:43Z step 2.1 main livecodebench spec_casc_opt alpha=0.05 seed=1: done, 90/90 cases (jobs 22880871, 0.30 GPU-h)
- 2026-09-29T11:10:43Z step 2.2 main aime24 r_fuzzy alpha=0.25 seed=1: done, 30/30 cases (jobs 22881159, 0.35 GPU-h)
- 2026-09-29T11:11:04Z grading: uploaded 115 run dir(s) to the Nibi mirror, submitted CPU grading job 22906465
- 2026-09-29T11:11:06Z grading: pulled 25050 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T11:26:47Z lane A: pulled 81 new run dir(s) into runs/
- 2026-09-29T11:26:58Z lane B: pulled 31 new run dir(s) into runs/
- 2026-09-29T11:27:01Z step 2.2 main aime24 spec_casc_tok alpha=0.8 seed=1: done, 30/30 cases (jobs 22881159, 0.27 GPU-h)
- 2026-09-29T11:28:06Z grading: uploaded 112 run dir(s) to the Nibi mirror, submitted CPU grading job 22907663
- 2026-09-29T11:28:10Z grading: pulled 25165 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T11:44:12Z lane A: pulled 96 new run dir(s) into runs/
- 2026-09-29T11:44:25Z lane B: pulled 32 new run dir(s) into runs/
- 2026-09-29T11:44:28Z step 2.1 main livecodebench spec_casc_opt alpha=0.05 seed=2: done, 90/90 cases (jobs 22880871, 0.30 GPU-h)
- 2026-09-29T11:44:28Z step 2.2 main aime24 strict alpha=strict seed=2: done, 30/30 cases (jobs 22881159, 0.28 GPU-h)
- 2026-09-29T11:45:15Z grading: uploaded 128 run dir(s) to the Nibi mirror, submitted CPU grading job 22908002
- 2026-09-29T11:45:19Z grading: pulled 25277 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T12:01:00Z lane A: pulled 93 new run dir(s) into runs/
- 2026-09-29T12:01:11Z lane B: pulled 25 new run dir(s) into runs/
- 2026-09-29T12:01:14Z step 2.1 main livecodebench mentored_dec alpha=0.75 seed=1: done, 90/90 cases (jobs 22880871, 0.27 GPU-h)
- 2026-09-29T12:01:15Z step 2.1 main livecodebench mentored_dec alpha=0.75 seed=2: done, 90/90 cases (jobs 22880871, 0.25 GPU-h)
- 2026-09-29T12:01:42Z grading: uploaded 118 run dir(s) to the Nibi mirror, submitted CPU grading job 22909077
- 2026-09-29T12:01:46Z grading: pulled 25405 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T12:17:37Z lane A: pulled 90 new run dir(s) into runs/
- 2026-09-29T12:17:52Z lane B: pulled 30 new run dir(s) into runs/
- 2026-09-29T12:17:55Z step 2.1 main livecodebench cactus alpha=0.18 seed=1: done, 90/90 cases (jobs 22880871, 0.28 GPU-h)
- 2026-09-29T12:17:56Z step 2.2 main aime24 spec_casc_opt alpha=0.05 seed=2: done, 30/30 cases (jobs 22881159, 0.39 GPU-h)
- 2026-09-29T12:18:16Z grading: uploaded 120 run dir(s) to the Nibi mirror, submitted CPU grading job 22909383
- 2026-09-29T12:18:18Z grading: pulled 25523 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T12:33:56Z lane A: pulled 90 new run dir(s) into runs/
- 2026-09-29T12:34:05Z lane B: pulled 27 new run dir(s) into runs/
- 2026-09-29T12:34:08Z step 2.1 main livecodebench cactus alpha=0.18 seed=2: done, 90/90 cases (jobs 22880871, 0.27 GPU-h)
- 2026-09-29T12:34:08Z step 2.2 main aime24 mentored_dec alpha=0.75 seed=2: done, 30/30 cases (jobs 22881159, 0.28 GPU-h)
- 2026-09-29T12:34:28Z grading: uploaded 117 run dir(s) to the Nibi mirror, submitted CPU grading job 22910433
- 2026-09-29T12:34:29Z grading: pulled 25643 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T12:50:51Z lane A: pulled 90 new run dir(s) into runs/
- 2026-09-29T12:51:01Z lane B: pulled 25 new run dir(s) into runs/
- 2026-09-29T12:51:04Z step 2.1 main livecodebench r_fuzzy alpha=0.25 seed=1: done, 90/90 cases (jobs 22880871, 0.30 GPU-h)
- 2026-09-29T12:51:04Z step 2.2 main aime24 cactus alpha=0.18 seed=2: done, 30/30 cases (jobs 22881159, 0.29 GPU-h)
- 2026-09-29T12:52:23Z grading: uploaded 115 run dir(s) to the Nibi mirror, submitted CPU grading job 22911605
- 2026-09-29T12:52:25Z grading: pulled 25760 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T13:07:57Z lane A: pulled 90 new run dir(s) into runs/
- 2026-09-29T13:08:07Z lane B: pulled 28 new run dir(s) into runs/
- 2026-09-29T13:08:10Z step 2.1 main livecodebench r_fuzzy alpha=0.25 seed=2: done, 90/90 cases (jobs 22880871, 0.28 GPU-h)
- 2026-09-29T13:08:11Z step 2.2 main aime24 r_fuzzy alpha=0.25 seed=2: done, 30/30 cases (jobs 22881159, 0.35 GPU-h)
- 2026-09-29T13:09:55Z grading: uploaded 118 run dir(s) to the Nibi mirror, submitted CPU grading job 22912733
- 2026-09-29T13:10:00Z grading: pulled 25875 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T13:26:18Z lane A: pulled 90 new run dir(s) into runs/
- 2026-09-29T13:26:33Z lane B: pulled 42 new run dir(s) into runs/
- 2026-09-29T13:26:36Z step 2.1 main livecodebench spec_casc_tok alpha=0.8 seed=1: done, 90/90 cases (jobs 22880871, 0.28 GPU-h)
- 2026-09-29T13:26:37Z step 2.2 main aime24 spec_casc_tok alpha=0.8 seed=2: done, 30/30 cases (jobs 22881159, 0.25 GPU-h)
- 2026-09-29T13:26:38Z step 6 main aime24 strict alpha=strict seed=3: done, 30/30 cases (jobs 22881159, 0.23 GPU-h)
- 2026-09-29T13:27:15Z grading: uploaded 132 run dir(s) to the Nibi mirror, submitted CPU grading job 22913325
- 2026-09-29T13:27:17Z grading: pulled 25993 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T13:31Z Step 1.9: key file present; one validation request ok (claude-fable-5-1, end_turn, req_011CfXp6D2QSEa5qi65k1saW, 6,569 in / 886 out tokens, rating parsed). Submitted Message Batch msgbatch_01MWf6AJLXcXd9ep5uFx5a7v: 2,070 judge requests = every seed-0 MT-Bench run of both targets with an answer (224 runs without one score 1, no call), effort medium, est. ~$89. Seeds 1-2 are not in this batch (`--seeds 1 2` later, roughly +$40 for GPT-OSS).
- 2026-09-29T14:30:28Z lane A: pulled 647 new run dir(s) into runs/
- 2026-09-29T14:30:52Z lane B: pulled 95 new run dir(s) into runs/
- 2026-09-29T14:30:56Z step 2.1 main livecodebench spec_casc_tok alpha=0.8 seed=2: done, 90/90 cases (jobs 22880871, 0.26 GPU-h)
- 2026-09-29T14:30:56Z step 0.5 nibiref humaneval strict alpha=strict seed=0: done, 150/150 cases (jobs 22880871, 0.14 GPU-h)
- 2026-09-29T14:30:57Z step 0.5 nibiref mtbench strict alpha=strict seed=0: done, 80/80 cases (jobs 22880871, 0.11 GPU-h)
- 2026-09-29T14:30:57Z step 0.5 nibiref longbench_v2 strict alpha=strict seed=0: done, 150/150 cases (jobs 22880871, 0.24 GPU-h)
- 2026-09-29T14:30:57Z step 0.5 nibiref aime24 strict alpha=strict seed=0: done, 30/30 cases (jobs 22880871, 0.22 GPU-h)
- 2026-09-29T14:30:58Z step 5.1 main gsm8k mentored_dec alpha=0.55 seed=0: done, 150/150 cases (jobs 22880871, 0.12 GPU-h)
- 2026-09-29T14:30:58Z step 6 main aime24 spec_casc_opt alpha=0.05 seed=3: done, 30/30 cases (jobs 22881159, 0.35 GPU-h)
- 2026-09-29T14:30:59Z step 6 main aime24 mentored_dec alpha=0.75 seed=3: done, 30/30 cases (jobs 22881159, 0.29 GPU-h)
- 2026-09-29T14:30:59Z step 6 main aime24 cactus alpha=0.18 seed=3: done, 30/30 cases (jobs 22881159, 0.26 GPU-h)
- 2026-09-29T14:32:04Z grading: uploaded 742 run dir(s) to the Nibi mirror, submitted CPU grading job 22918280
- 2026-09-29T14:32:07Z grading: pulled 26125 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T15:31:14Z lane A: pulled 941 new run dir(s) into runs/
- 2026-09-29T15:31:44Z lane B: pulled 103 new run dir(s) into runs/
- 2026-09-29T15:31:47Z step 5.1 main gsm8k spec_casc_tok alpha=0.35 seed=0: done, 150/150 cases (jobs 22880871, 0.08 GPU-h)
- 2026-09-29T15:31:48Z step 5.1 main gsm8k spec_casc_tok alpha=0.55 seed=0: done, 150/150 cases (jobs 22880871, 0.06 GPU-h)
- 2026-09-29T15:31:49Z step 5.1 main humaneval mentored_dec alpha=0.55 seed=0: done, 150/150 cases (jobs 22880871, 0.13 GPU-h)
- 2026-09-29T15:31:49Z step 5.1 main humaneval spec_casc_tok alpha=0.35 seed=0: done, 150/150 cases (jobs 22880871, 0.17 GPU-h)
- 2026-09-29T15:31:50Z step 5.1 main humaneval spec_casc_tok alpha=0.55 seed=0: done, 150/150 cases (jobs 22880871, 0.13 GPU-h)
- 2026-09-29T15:31:50Z step 5.1 main longbench_v2 mentored_dec alpha=0.35 seed=0: done, 150/150 cases (jobs 22880871, 0.28 GPU-h)
- 2026-09-29T15:31:50Z step 6 main aime24 r_fuzzy alpha=0.25 seed=3: done, 30/30 cases (jobs 22881159, 0.38 GPU-h)
- 2026-09-29T15:31:51Z step 6 main aime24 spec_casc_tok alpha=0.8 seed=3: done, 30/30 cases (jobs 22881159, 0.30 GPU-h)
- 2026-09-29T15:31:51Z step 6 main aime24 strict alpha=strict seed=4: done, 30/30 cases (jobs 22881159, 0.26 GPU-h)
- 2026-09-29T15:34:07Z grading: uploaded 1044 run dir(s) to the Nibi mirror, submitted CPU grading job 22921601
- 2026-09-29T15:34:10Z grading: pulled 26867 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T13:37Z-14:28Z Nibi link down (this Mac's connection dropped; last keepalive 13:37:46Z). Lanes kept running; one Duo push reconnected at 14:28Z and the next poll collected 742 runs / 9 arms.
- 2026-09-29T14:20Z Step 0.2 re-check (Bill asked "is that sampler nowhere in the box"): not in any readable path on Nibi (/project/6071935 other members' dirs are not readable; only the two pristine lane copies), not in git on any branch incl. upstream (chiatzenw-cur) and the 2026-09-24 stash (only HASHES.txt/JOURNAL.md mention its code), not found on this Mac after a 2-hour full-home scan (cascade/SETUP.md: vLLM was never installed on this Mac). Only the old box has it.
- 2026-09-29T14:30Z Judge collector crashed on a transient API 503 ("credential validation failed") while polling; now retries 5xx/connection errors for up to 6 h. Batch msgbatch_01MWf6AJLXcXd9ep5uFx5a7v still in_progress at 15:35Z (0/2,070 done).
- 2026-09-29T15:49:53Z lane A: pulled 162 new run dir(s) into runs/
- 2026-09-29T15:50:26Z lane B: pulled 25 new run dir(s) into runs/
- 2026-09-29T15:50:30Z step 5.1 main longbench_v2 spec_casc_tok alpha=0.35 seed=0: done, 150/150 cases (jobs 22880871, 0.26 GPU-h)
- 2026-09-29T15:50:31Z step 6 main aime24 spec_casc_opt alpha=0.05 seed=4: done, 30/30 cases (jobs 22881159, 0.34 GPU-h)
- 2026-09-29T15:52:07Z grading: uploaded 187 run dir(s) to the Nibi mirror, submitted CPU grading job 22922054
- 2026-09-29T15:52:08Z grading: pulled 27911 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T16:10:29Z lane A: pulled 160 new run dir(s) into runs/
- 2026-09-29T16:11:19Z lane B: pulled 36 new run dir(s) into runs/
- 2026-09-29T16:11:22Z step 5.1 main longbench_v2 spec_casc_tok alpha=0.55 seed=0: done, 150/150 cases (jobs 22880871, 0.24 GPU-h)
- 2026-09-29T16:11:23Z step 5.1 main livecodebench mentored_dec alpha=0.55 seed=0: done, 90/90 cases (jobs 22880871, 0.29 GPU-h)
- 2026-09-29T16:11:24Z step 6 main aime24 mentored_dec alpha=0.75 seed=4: done, 30/30 cases (jobs 22881159, 0.36 GPU-h)
- 2026-09-29T16:14:10Z grading: uploaded 196 run dir(s) to the Nibi mirror, submitted CPU grading job 22923108
- 2026-09-29T16:14:11Z grading: pulled 28098 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T16:30:42Z lane A: pulled 87 new run dir(s) into runs/
- 2026-09-29T16:31:05Z lane B: pulled 28 new run dir(s) into runs/
- 2026-09-29T16:31:08Z step 5.1 main livecodebench spec_casc_tok alpha=0.35 seed=0: done, 90/90 cases (jobs 22880871, 0.32 GPU-h)
- 2026-09-29T16:31:08Z step 6 main aime24 cactus alpha=0.18 seed=4: done, 30/30 cases (jobs 22881159, 0.29 GPU-h)
- 2026-09-29T16:32:41Z grading: uploaded 115 run dir(s) to the Nibi mirror, submitted CPU grading job 22923643
- 2026-09-29T16:32:42Z grading: pulled 28294 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T16:49:02Z lane A: pulled 87 new run dir(s) into runs/
- 2026-09-29T16:49:22Z lane B: pulled 26 new run dir(s) into runs/
- 2026-09-29T16:49:26Z step 5.1 main livecodebench spec_casc_tok alpha=0.55 seed=0: done, 90/90 cases (jobs 22880871, 0.28 GPU-h)
- 2026-09-29T16:49:26Z step 6 main aime24 r_fuzzy alpha=0.25 seed=4: done, 30/30 cases (jobs 22881159, 0.39 GPU-h)
- 2026-09-29T16:50:09Z grading: uploaded 113 run dir(s) to the Nibi mirror, submitted CPU grading job 22924170
- 2026-09-29T16:50:10Z grading: pulled 28409 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T17:06:28Z lane A: pulled 179 new run dir(s) into runs/
- 2026-09-29T17:06:54Z lane B: pulled 69 new run dir(s) into runs/
- 2026-09-29T17:06:57Z step 5.1 main mtbench mentored_dec alpha=0.35 seed=0: done, 80/80 cases (jobs 22880871, 0.15 GPU-h)
- 2026-09-29T17:06:58Z step 5.1 main mtbench spec_casc_tok alpha=0.35 seed=0: done, 80/80 cases (jobs 22880871, 0.13 GPU-h)
- 2026-09-29T17:06:58Z step 6 main aime24 spec_casc_tok alpha=0.8 seed=4: done, 30/30 cases (jobs 22881159, 0.31 GPU-h)
- 2026-09-29T17:08:31Z grading: uploaded 248 run dir(s) to the Nibi mirror, submitted CPU grading job 22926385
- 2026-09-29T17:08:32Z grading: pulled 28522 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T17:25:11Z lane A: pulled 79 new run dir(s) into runs/
- 2026-09-29T17:25:45Z lane B: pulled 197 new run dir(s) into runs/
- 2026-09-29T17:25:48Z step 5.1 main mtbench spec_casc_tok alpha=0.55 seed=0: done, 80/80 cases (jobs 22880871, 0.12 GPU-h)
- 2026-09-29T17:25:49Z step 5.1 main aime24 mentored_dec alpha=0.55 seed=0: done, 30/30 cases (jobs 22880871, 0.21 GPU-h)
- 2026-09-29T17:25:50Z step 2.2 main longbench_v2 strict alpha=strict seed=1: done, 150/150 cases (jobs 22881159, 0.28 GPU-h)
- 2026-09-29T17:27:44Z grading: uploaded 276 run dir(s) to the Nibi mirror, submitted CPU grading job 22927505
- 2026-09-29T17:27:45Z grading: pulled 28770 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T17:44:16Z lane A: pulled 32 new run dir(s) into runs/
- 2026-09-29T17:44:48Z lane B: pulled 158 new run dir(s) into runs/
- 2026-09-29T17:44:55Z step 5.1 main aime24 spec_casc_tok alpha=0.35 seed=0: done, 30/30 cases (jobs 22880871, 0.26 GPU-h)
- 2026-09-29T17:44:56Z step 2.2 main longbench_v2 strict alpha=strict seed=2: done, 150/150 cases (jobs 22881159, 0.25 GPU-h)
- 2026-09-29T17:47:16Z grading: uploaded 190 run dir(s) to the Nibi mirror, submitted CPU grading job 22930026
- 2026-09-29T17:47:18Z grading: pulled 29046 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T17:58:00Z lane A: pulled 22 new run dir(s) into runs/
- 2026-09-29T17:59:10Z lane B: pulled 98 new run dir(s) into runs/
- 2026-09-29T17:59:13Z step 5.1 main aime24 spec_casc_tok alpha=0.55 seed=0: done, 30/30 cases (jobs 22880871, 0.23 GPU-h)
- 2026-09-29T17:59:14Z step 2.2 main longbench_v2 spec_casc_opt alpha=0.05 seed=1: done, 150/150 cases (jobs 22881159, 0.32 GPU-h)
- 2026-09-29T18:00:16Z grading: uploaded 120 run dir(s) to the Nibi mirror, submitted CPU grading job 22930898
- 2026-09-29T18:00:18Z grading: pulled 29236 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T18:06:50Z grading: pulled 29356 verdicts into campaign/addendum/analysis/grades.csv
- 2026-09-29T18:06:54Z step 5.2: 12 cells have an eligible best setting; added 11 seed-1 row(s): gsm8k/mentored_dec/0.55, gsm8k/spec_casc_tok/0.55, aime24/mentored_dec/0.55, aime24/spec_casc_tok/0.15, humaneval/mentored_dec/0.55, humaneval/spec_casc_tok/0.35, livecodebench/mentored_dec/0.55, livecodebench/spec_casc_tok/0.35, mtbench/spec_casc_tok/0.55, longbench_v2/mentored_dec/0.55, longbench_v2/spec_casc_tok/0.55
- 2026-09-29T18:11:27Z lane B: pulled 70 new run dir(s) into runs/
- 2026-09-29T18:11:49Z lane A: submitted job 22931500; lane has 11 work items, est. 1.7 GPU-h
