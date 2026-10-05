# Step 9 Block 0 report (2026-10-05)

Checks for the three new datasets (AIME24, LongBench-v2, HumanEval) on each of the five dedicated step-8 pairs, before
any step-9 block runs: prompt format, grader path, head config, and one 2-case lossless smoke run per (pair,
dataset) on the block's own cluster (`runs/addendum/step9_block0/<cluster>/<pair>/`, outside the run tree, never in a
table). Clusters: README deviation 42 (GPT-OSS-20B and Llama-3.1-8B-Instruct blocks on Nibi H100s, Qwen3-8B + DSpark
and R1-Distill on Killarney H100s; every block whole on one cluster).

## Prompt format

| pair | AIME24 | LongBench-v2 | HumanEval |
|---|---|---|---|
| GPT-OSS-20B + RH EAGLE-3 | `prompts/aime24` (the paper's Harmony set) | `prompts/longbench_v2` | `prompts/humaneval` |
| Qwen3-8B + DSpark | `prompts/aime24_qwen3` (the paper's Qwen3 set) | `prompts/longbench_v2_qwen3` | `prompts/humaneval_qwen3` |
| Llama-3.1-8B-Instruct + EAGLE-3 / EAGLE-1 | `prompts/aime24_llama31` (step 8) | `prompts/longbench_v2_llama31` (new) | `prompts/humaneval_llama31` (new) |
| R1-Distill-Llama-8B + EAGLE-3 | (step 8, not rerun) | `prompts/longbench_v2_r1llama` (new) | `prompts/humaneval_r1llama` (new) |

The four new sets are the Harmony sets re-rendered through each model's own chat template with
`scripts/build_prompts_qwen3.py --chat-format {llama31,r1llama} --count 150`, run on Killarney in the lane venv
(transformers 5.18, offline HF cache; R1 through the corrected tokenizer copy of README deviation 33, which has the
same chat template). The same command reproduces step 8's committed `aime24_llama31` and `aime24_r1llama` byte for
byte (30 of 30 rendered prompts and token counts each). Llama-3.1 renders Meta's current template ("Cutting Knowledge
Date: December 2023 / Today Date: 26 Jul 2024" system header); R1 ends the generation prompt with an opened `<think>`.
Token counts: HumanEval 123-476 (Llama-3.1) / 93-446 (R1); LongBench-v2 10,097-45,438 / 10,067-45,408. Every lane repo
holds byte-identical copies (sha256 digest per set; README deviation 41).

## Longest sequences and head configs

| pair | longest LongBench-v2 prompt + budget | drafter position limit |
|---|---|---|
| GPT-OSS-20B + RH EAGLE-3 | 44,855 + 8,192 = 53,047 | 131,072 (its own config; no copy needed) |
| Qwen3-8B + DSpark | 51,234 + 8,192 = 59,426 | 40,960 in the published config: a 65,536 copy for LongBench-v2 only (README deviation 40) |
| Llama-3.1-8B-Instruct + EAGLE-3 / EAGLE-1 | 45,438 + 8,192 = 53,630 | 65,536 (step 8's copies, deviation 31; identical on Nibi) |
| R1-Distill-Llama-8B + EAGLE-3 | 45,408 + 8,192 = 53,600 | 65,536 (step 8's copy) |

Every server runs at MAX_MODEL_LEN 65,536 (Qwen3: YaRN 1.6, as the paper). AIME24 (32,768 + at most 424 prompt
tokens) and HumanEval (9,000 + at most 476) stay inside every drafter's native limit.

## Grader paths

The campaign's own graders (`scripts/addendum_grade.py` GRADERS, run in a Nibi CPU job): HumanEval =
`grade_humaneval.py` (last fenced code block of the answer segment, executed against the case's tests, 10 s, 1 GB);
LongBench-v2 = `grade_longbench.py` (`\boxed{A-D}`, else the last bare capital A-D of the answer segment); AIME24 =
`grade_aime.py` unchanged (1-3 digit `\boxed{}`, else the last 1-3 digit integer; every step-9 run whose last boxed
answer is longer than 3 digits is listed in `aime_boxed_long.csv` for a later re-grade). Answer segment
(`answer_extraction.final_segment`): after the last Harmony final-channel marker (GPT-OSS), after `</think>` (Qwen3,
R1-Distill), the whole text (Llama-3.1, which does not reason in tags).

## Smoke runs

(filled in from the smoke runs)
