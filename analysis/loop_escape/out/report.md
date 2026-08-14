# Loop-escape emission-source composition

Input: `analysis/loop_escape/out/candidates.jsonl` -- 54 loop regions, 54 escape events mapped, 0 arms skipped (no/unreadable trace).

| composition | accepted_draft | recovered | bonus |
|---|---|---|---|
| escape tokens | 32 (59.3%) | 13 (24.1%) | 9 (16.7%) |
| escape ±2 window | 207 (76.7%) | 28 (10.4%) | 35 (13.0%) |
| onset tokens | 47 (87.0%) | 5 (9.3%) | 2 (3.7%) |
| onset ±2 window | 211 (78.1%) | 42 (15.6%) | 17 (6.3%) |
| loop interior | 2937 (81.6%) | 278 (7.7%) | 386 (10.7%) |
| whole-trace base | 578416 (71.4%) | 189444 (23.4%) | 42627 (5.3%) |

## Lift at escape points (share of escapes / base rate)

- **accepted_draft**: escape share 59.3% (95% CI 46.0%-71.3%), base 71.4%, lift **0.83x**
- **recovered**: escape share 24.1% (95% CI 14.6%-36.9%), base 23.4%, lift **1.03x**
- **bonus**: escape share 16.7% (95% CI 9.0%-28.7%), base 5.3%, lift **3.17x**

## Loop onset

Of 54 onset tokens, **5** were lossy-only acceptances (strict would have rejected the token that started the loop).

## Inside-loop rule agreement

Would falling back to the strict rule *inside* the loop change anything? For each interior token: `strict agrees` = strict rule would accept the same token (a strict guard changes nothing); `lossy-only` = only the lossy rule accepted it (a strict guard would have rejected + resampled here); `recovered` tokens already went through rejection + residual resampling and stayed in the loop.

| interior source | n | strict agrees | lossy-only |
|---|---|---|---|
| accepted_draft | 2937 | 2724 (92.7%) | 213 (7.3%) |
| recovered | 278 | 27 (9.7%) | 0 (0.0%) |
| bonus | 386 | 0 (0.0%) | 0 (0.0%) |

- 45/54 loops contain at least one `recovered` (rejection-resampled) token in their interior -- resampling happened inside the loop without breaking it.
- 213/3601 interior tokens (5.9%) are lossy-only acceptances -- the only places a strict-inside-loop fallback would act differently at all. Everywhere else strict emits the same token or the resample already ran.

## Per-escape detail

| case_key | arm | char | source | kind | quote (viewer search) |
|---|---|---|---|---|---|
| aime24_fresh/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | approx_region_end | `` |
| aime24_fresh/case_003/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 105771 | bonus | approx_region_end | `` |
| aime24_fresh/case_003/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 87141 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_004/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 11581 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_004/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 12801 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 8198 | bonus | approx_region_end | `` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 12201 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 8350 | bonus | approx_region_end | `` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 12407 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 12631 | recovered | approx_region_end | `` |
| aime24_fresh/case_006/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 31295 | recovered | approx_region_end | `` |
| aime24_fresh/case_006/seed_0 | specCascTokSemanticGuardFutureGuardAnd0p3k8 | 15233 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_007/seed_0 | specCascOpt0p05 | 51366 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_007/seed_0 | specCascTokSemanticGuardFutureGuard0p5k8 | 12357 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_008/seed_0 | specCascOpt0p05 | 71977 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_011/seed_0 | specCascOpt0p05 | 71760 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_014/seed_0 | specCascTokSemanticGuardFutureGuardAnd0p3k8 | 53390 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_016/seed_0 | specCascOpt0p05 | 8376 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_017/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 4016 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 52856 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 69751 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 69927 | bonus | approx_region_end | `` |
| aime24_fresh/case_018/seed_0 | specCascTok0p7 | 7221 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_019/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 14790 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_021/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 27255 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_026/seed_0 | specCascOpt0p05 | 66451 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_026/seed_0 | specCascTokSemanticGuardFutureGuard0p3k4 | 89305 | recovered | approx_region_end | `` |
| aime24_fresh/case_026/seed_0 | specCascTokSemanticGuardFutureGuard0p5k8 | 88631 | recovered | approx_region_end | `` |
| aime24_fresh/case_028/seed_0 | specCascOpt0p05 | 6867 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_028/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 5787 | recovered | approx_region_end | `` |
| aime24_fresh/case_029/seed_0 | specCascTokSemanticGuardV20p3 | 18736 | accepted_draft | approx_region_end | `` |
| aime24_fresh/case_030/seed_0 | specCascTokSemanticGuardFutureGuardAnd0p3k8 | 18928 | recovered | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 3909 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 4537 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 14071 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 14765 | bonus | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 21293 | bonus | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 23166 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 23675 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24175 | bonus | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24300 | bonus | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24551 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 25333 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 26110 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_036/seed_0 | rFuzzySemanticGuard0p3 | 2566 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_109/seed_0 | specCascOpt0p05 | 11709 | accepted_draft | approx_region_end | `` |
| humaneval_fresh/case_141/seed_0 | specCascOpt0p05 | 13637 | accepted_draft | approx_region_end | `` |
| spec_casc_tok_semantic_guard_and_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | approx_region_end | `` |
| spec_casc_tok_semantic_guard_future_guard_and_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | approx_region_end | `` |
| spec_casc_tok_semantic_guard_future_guard_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | approx_region_end | `` |
| spec_casc_tok_semantic_guard_future_guard_pilot/aime24/case_003/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 105771 | bonus | approx_region_end | `` |
| spec_casc_tok_semantic_guard_future_guard_pilot/aime24/case_028/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 5787 | recovered | approx_region_end | `` |
| spec_casc_tok_semantic_guard_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | approx_region_end | `` |
| spec_casc_tok_semantic_guard_v2_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | approx_region_end | `` |
