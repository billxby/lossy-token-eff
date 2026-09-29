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
2. **MT-Bench judge API key (step 1.9).** No Anthropic credentials here (no
   `ANTHROPIC_API_KEY`, no `ant` CLI profile). The judge is written and
   dry-run (`scripts/addendum_mtbench_judge.py`: FastChat single-v1 /
   single-math-v1 prompts, turn 1, `[[rating]]`; claude-fable-5-1 on the
   Message Batches API). Ask: put `ANTHROPIC_API_KEY=...` in
   `~/.config/lossy-token-eff/judge.env` (`chmod 600`). Cost estimate from the
   dry run: 2,070 requests for the existing seed-0 runs (224 more runs never
   reached an answer and score 1 without a call), ~2.3M input + ~3.1M output
   tokens -> ~$89 at batch prices; roughly double once the seed-1/2 MT-Bench
   runs are in. Run: `python3 scripts/addendum_mtbench_judge.py submit` then
   `... collect`.
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
