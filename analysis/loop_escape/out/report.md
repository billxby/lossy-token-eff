# Loop-escape emission-source composition

Input: `/Users/billxu/GitHub/lossy-token-eff/analysis/loop_escape/out/judged.jsonl` -- 54 loop regions, 92 escape events mapped, 0 arms skipped (no/unreadable trace).

| composition | accepted_draft | recovered | bonus |
|---|---|---|---|
| escape tokens | 61 (66.3%) | 24 (26.1%) | 7 (7.6%) |
| escape ±2 window | 346 (75.2%) | 68 (14.8%) | 46 (10.0%) |
| onset tokens | 37 (68.5%) | 12 (22.2%) | 5 (9.3%) |
| onset ±2 window | 196 (72.6%) | 52 (19.3%) | 22 (8.1%) |
| loop interior | 4913 (81.0%) | 505 (8.3%) | 649 (10.7%) |
| whole-trace base | 578416 (71.4%) | 189444 (23.4%) | 42627 (5.3%) |

## Lift at escape points (share of escapes / base rate)

- **accepted_draft**: escape share 66.3% (95% CI 56.2%-75.1%), base 71.4%, lift **0.93x**
- **recovered**: escape share 26.1% (95% CI 18.2%-35.9%), base 23.4%, lift **1.12x**
- **bonus**: escape share 7.6% (95% CI 3.7%-14.9%), base 5.3%, lift **1.45x**

## Loop onset

Of 54 onset tokens, **6** were lossy-only acceptances (strict would have rejected the token that started the loop).

## Inside-loop rule agreement

Would falling back to the strict rule *inside* the loop change anything? For each interior token: `strict agrees` = strict rule would accept the same token (a strict guard changes nothing); `lossy-only` = only the lossy rule accepted it (a strict guard would have rejected + resampled here); `recovered` tokens already went through rejection + residual resampling and stayed in the loop.

| interior source | n | strict agrees | lossy-only |
|---|---|---|---|
| accepted_draft | 4913 | 4429 (90.1%) | 484 (9.9%) |
| recovered | 505 | 38 (7.5%) | 0 (0.0%) |
| bonus | 649 | 0 (0.0%) | 0 (0.0%) |

- 52/54 loops contain at least one `recovered` (rejection-resampled) token in their interior -- resampling happened inside the loop without breaking it.
- 484/6067 interior tokens (8.0%) are lossy-only acceptances -- the only places a strict-inside-loop fallback would act differently at all. Everywhere else strict emits the same token or the resample already ran.

## Per-escape detail

| case_key | arm | char | source | kind | quote (viewer search) |
|---|---|---|---|---|---|
| aime24_fresh/case_002/seed_0 | specCascTok0p3 | 44115 | accepted_draft | completes_computation | `Simplify: divide by 4: 756/(25 sqrt(14)). So Xb - Xc` |
| aime24_fresh/case_003/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 105774 | accepted_draft | self_correction | `Anyway, we can trust.` |
| aime24_fresh/case_003/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 87199 | recovered | completes_computation | `subtract 1: B = B+2. That means shift by 2` |
| aime24_fresh/case_004/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 11583 | accepted_draft | self_correction | `Hold on: Actually we need sorted list: 0,0.0767,0.1111,0.139` |
| aime24_fresh/case_004/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 12271 | accepted_draft | content_shift | `Let's just list all unique values sorted:\n\n0\n0.0767\n0.1111` |
| aime24_fresh/case_004/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 12802 | accepted_draft | self_correction | `0.5894? duplicate.\n\nActually we have 0.5894 only once.` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 8574 | accepted_draft | completes_computation | `121*8 = 120*8 + 1*8 = 960 + 8 = 1218. Yes correct.` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 8626 | accepted_draft | content_shift | `So 1087 - 1218 = 1087 - 1218 = -131.` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 12297 | accepted_draft | re_enters_loop | `Stop over. Let's compute 121*9: 100*9=1210; 20*9=180;` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 12449 | accepted_draft | re_enters_loop | `Ok just compute 121*9 = 9*121 = 121*10 - 121 = 1210 - 121` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 12851 | accepted_draft | re_enters_loop | `Better to compute: 1210 minus 121 = 1210 - 121 = 1210 - 121` |
| aime24_fresh/case_005/seed_0 | specCascOpt0p05 | 12969 | accepted_draft | truncation | `Ok, maybe we should scrap the me` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 8369 | recovered | content_shift | `Factor: a^2? Let's just compute with expansions: s = (a+b+c)` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 8434 | recovered | completes_computation | `Then s-a = (a+b+c)/2 - a = (a+b+c)/2 - a = (a+b+c -2a)/2 = (` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 12408 | accepted_draft | re_enters_loop | `+ 2? Wait hold.\n\nLet's compute:` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 12632 | recovered | completes_computation | `+ 41 = 89 => 121 - 2√41 x = 89` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 12850 | accepted_draft | re_enters_loop | `2√41 x = 121 - 89 = 32 => x = 32/(2√41)` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 12936 | accepted_draft | self_correction | `Wait 32/(2 sqrt41)=32/(2*2.598) =32/5.196` |
| aime24_fresh/case_006/seed_0 | specCascOpt0p05 | 13295 | accepted_draft | completes_computation | `32/(2*√41)=32/(2*6.403)=32/12.806=2.5. Good.` |
| aime24_fresh/case_006/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 31295 | recovered | content_shift | `. Combine: sqrt(21/41)/sqrt(189) = sqrt((21/41)/189)` |
| aime24_fresh/case_006/seed_0 | specCascTokSemanticGuardFutureGuardAnd0p3k8 | 15234 | accepted_draft | completes_computation | `Let's compute: 4.582575695*20=91.6515139` |
| aime24_fresh/case_007/seed_0 | specCascOpt0p05 | 51427 | accepted_draft | completes_computation | `p(27 - p)^2. Good: separate: p^2 / p = p.` |
| aime24_fresh/case_007/seed_0 | specCascTokSemanticGuardFutureGuard0p5k8 | 12358 | accepted_draft | re_enters_loop | `Sorry. Let's compute accurately: 17410.3-24033.8=-663?` |
| aime24_fresh/case_007/seed_0 | specCascTokSemanticGuardFutureGuard0p5k8 | 12547 | accepted_draft | re_enters_loop | `We must compute: 24,033.8-17,410.3=6,623.5.` |
| aime24_fresh/case_007/seed_0 | specCascTokSemanticGuardFutureGuard0p5k8 | 12989 | accepted_draft | content_shift | `Then add 7129.08 => 505.58. Then subtract 529 => -23.42` |
| aime24_fresh/case_008/seed_0 | specCascOpt0p05 | 72439 | accepted_draft | completes_computation | `So compute f = 0.426 - 0.4219 = 0.0041. So f positive.` |
| aime24_fresh/case_011/seed_0 | specCascOpt0p05 | 71760 | accepted_draft | completes_computation | `.25 = 34,410.25. Good.` |
| aime24_fresh/case_014/seed_0 | specCascTokSemanticGuardFutureGuardAnd0p3k8 | 53391 | accepted_draft | completes_computation | `r/s - r_in*(1 - s)/s = r/s - r_in*(1 - s)/s. But r_in*(s-1)/` |
| aime24_fresh/case_016/seed_0 | specCascOpt0p05 | 8377 | accepted_draft | content_shift | `(makes sense). We'll compute.` |
| aime24_fresh/case_017/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 4091 | accepted_draft | content_shift | `sqrt(5070) = sqrt(2*3*5*169) = 13 sqrt(30).` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 52858 | accepted_draft | content_shift | `But we can express 100x + 100y = 100s.` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 69755 | accepted_draft | re_enters_loop | `Let's compute: a+b = 300 - c. So a-100 + b-100 =` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 70006 | bonus | completes_computation | `Wait compute: a+b = 300 - c, thus (a-100)` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 70085 | accepted_draft | re_enters_loop | `Indeed earlier we found s = a - 100 + b - 100` |
| aime24_fresh/case_018/seed_0 | specCascOpt0p05 | 70398 | accepted_draft | completes_computation | `300-200=100. So 300 - c - 200 = 300 - 200 - c?` |
| aime24_fresh/case_018/seed_0 | specCascTok0p7 | 7233 | recovered | self_correction | `Wait 5,990,101 + 9,899 = 5,? 5,990,101 + 9,899 = 6,000,000.` |
| aime24_fresh/case_019/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 14793 | recovered | content_shift | `Compute combine: (7/4)(1 - 2s + s^2) = (7/4)(1 - 2s + s^2).` |
| aime24_fresh/case_021/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 27257 | accepted_draft | re_enters_loop | `Actually formula: n = a*k + s = 209*210 + 210` |
| aime24_fresh/case_021/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 27321 | bonus | completes_computation | `210*(209+1)=210*210=44100. n=44100.` |
| aime24_fresh/case_021/seed_0 | specCascTokSemanticGuardFutureGuard0p7k8 | 27509 | recovered | completes_computation | `Let's compute: 209*211=209*200+209*11=41800+2299=44099` |
| aime24_fresh/case_026/seed_0 | specCascOpt0p05 | 66452 | accepted_draft | completes_computation | `= (s,0) + b + c - (s,0) = b + c.` |
| aime24_fresh/case_026/seed_0 | specCascTokSemanticGuardFutureGuard0p3k4 | 89438 | recovered | re_enters_loop | `Let's multiply: 62900*9100 = 62900*9100 = (62900*9100).` |
| aime24_fresh/case_026/seed_0 | specCascTokSemanticGuardFutureGuard0p3k4 | 89494 | accepted_draft | re_enters_loop | `Use 629*9100*100? Actually 62900*9100 = 62900*9100` |
| aime24_fresh/case_026/seed_0 | specCascTokSemanticGuardFutureGuard0p3k4 | 89559 | recovered | re_enters_loop | `Let's compute 62900*9100 = 62900*9100 = 62900*9100.` |
| aime24_fresh/case_026/seed_0 | specCascTokSemanticGuardFutureGuard0p3k4 | 89611 | recovered | completes_computation | `Let's do step: 62900*9100 = 62900*(9000 + 100)` |
| aime24_fresh/case_026/seed_0 | specCascTokSemanticGuardFutureGuard0p5k8 | 88633 | accepted_draft | content_shift | `Simplify denominator: 1 + (1 + v)/u = (u + 1 + v)/u` |
| aime24_fresh/case_028/seed_0 | specCascOpt0p05 | 6868 | accepted_draft | completes_computation | `= 1000*(1 - a). But we can compute mod 7.` |
| aime24_fresh/case_028/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 5789 | accepted_draft | self_correction | `7*269=188... Let's compute precisely: 1888 / 7` |
| aime24_fresh/case_029/seed_0 | specCascTokSemanticGuardV20p3 | 18737 | accepted_draft | self_correction | `= 1/9? Actually 1089 = 33^2. 121 = 11^2.` |
| aime24_fresh/case_030/seed_0 | specCascTokSemanticGuardFutureGuardAnd0p3k8 | 18930 | accepted_draft | content_shift | `Expand: (5 - r)(5 - c) = 25 - 5r - 5c + rc.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 3910 | accepted_draft | self_correction | `'cata' ??? Let's just compute truth:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 4018 | accepted_draft | self_correction | `Actually I recall string concatenation:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 4555 | accepted_draft | self_correction | `'cata' + 'c' = 'cata c'? Wait no.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 4596 | accepted_draft | truncation | `step back: Suppose s='cata' + 'c': string 'cata' 4 chars.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 5012 | bonus | completes_computation | `characters 'c','a','t','a','c' => 'catac'.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 14072 | accepted_draft | re_enters_loop | `'catac' maybe? Let's compute: 'cata': 'cata' + 'tac'` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 14143 | accepted_draft | content_shift | `Wait there are 4 letters: 'c','a','t','a'. Append` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 14994 | accepted_draft | completes_computation | `'cata' + 'tac' = 'catatac', yes.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 15027 | accepted_draft | re_enters_loop | `So 'cata' + 'tac' = 'cata' + 'tac' = 'c a t a t a c'` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 15183 | accepted_draft | content_shift | `What's the string length? 'cata' length 4.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 15330 | accepted_draft | re_enters_loop | `So it's 'cata' + 'tac' = 'cata' 'tac' -> 'cata t a c'?` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 15394 | accepted_draft | content_shift | `Thus algorithm: find longest suffix palindrome` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 21294 | bonus | content_shift | `'cata''tac' = 'cata' + 'tac' = 'cattac'?` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 23803 | recovered | self_correction | `I'm lost. Let's implement in python mentally:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 23813 | accepted_draft | content_shift | `Let's implement in python mentally:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 23850 | recovered | re_enters_loop | `string 'cata' length 4. Append 'tac' length 3` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24318 | recovered | content_shift | `Ok I'll just compute algorithmically:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24318 | recovered | re_enters_loop | `Ok I'll just compute algorithmically: 'cata' + 'tac'` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24318 | recovered | re_enters_loop | `Ok I'll just compute algorithmically:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24640 | recovered | self_correction | `Apologies, I'm stuck. Let's quickly count:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24640 | recovered | self_correction | `Apologies, I'm stuck. Let's quickly count:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24640 | recovered | re_enters_loop | `Apologies, I'm stuck. Let's quickly count:` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24903 | accepted_draft | re_enters_loop | `Let's compute using Python mentally: 'cata' is 4 letters.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24903 | accepted_draft | content_shift | `Let's compute using Python mentally: 'cata' is 4 letters.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 24903 | accepted_draft | re_enters_loop | `Let's compute using Python mentally: 'cata' is 4 letters.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 25352 | accepted_draft | self_correction | `Stop. The result will be key string 'cata' 'tac' =>` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 25404 | bonus | re_enters_loop | `'cata' + 'tac' -> 'cata' + 'tac' -> 'catatac' ->` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 25469 | bonus | self_correction | `Wait we need each letter: 'c','a','t','a','t','a','c'` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 25626 | accepted_draft | re_enters_loop | `Not 'cata t a c' -> 'cata t a c'? The correct string is` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 25718 | accepted_draft | self_correction | `But I'm being meaningless.` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 25746 | accepted_draft | re_enters_loop | `Let's just convert to string: 'cata' + 'tac' = 'cata'` |
| humaneval_fresh/case_011/seed_0 | specCascOpt0p05 | 26233 | accepted_draft | re_enters_loop | `Let's just produce string: 'c@a'.` |
| humaneval_fresh/case_036/seed_0 | rFuzzySemanticGuard0p3 | 2579 | bonus | completes_computation | `maximum = val   # OK` |
| humaneval_fresh/case_109/seed_0 | specCascOpt0p05 | 11748 | recovered | self_correction | `No, we have 3 numbers: [-1, 11, -11], sumAbs for 11:` |
| humaneval_fresh/case_141/seed_0 | specCascOpt0p05 | 13698 | accepted_draft | content_shift | `The following implementation satisfies the specification:` |
| spec_casc_tok_semantic_guard_and_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44115 | accepted_draft | completes_computation | `Simplify: divide by 4: 756/(25 sqrt(14)).` |
| spec_casc_tok_semantic_guard_future_guard_and_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | completes_computation | `/(100 sqrt(14)). Simplify: divide by 4: 756/(25 sqrt(14)).` |
| spec_casc_tok_semantic_guard_future_guard_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44115 | accepted_draft | content_shift | `Simplify: divide by 4: 756/(25 sqrt(14)).` |
| spec_casc_tok_semantic_guard_future_guard_pilot/aime24/case_003/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 105774 | accepted_draft | self_correction | `Anyway, we can trust.` |
| spec_casc_tok_semantic_guard_future_guard_pilot/aime24/case_028/seed_0 | specCascTokSemanticGuardFutureGuard0p3k8 | 5802 | recovered | self_correction | `Let's compute precisely: 1888 / 7 = 269.714` |
| spec_casc_tok_semantic_guard_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44098 | recovered | completes_computation | `/(100 sqrt(14)). Simplify: divide by 4: 756/(25 sqrt(14)).` |
| spec_casc_tok_semantic_guard_v2_pilot/aime24/case_002/seed_0 | specCascTok0p3 | 44112 | recovered | completes_computation | `). Simplify: divide by 4: 756/(25 sqrt(14)).` |
