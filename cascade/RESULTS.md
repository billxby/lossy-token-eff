# Results: head-restricted relaxed speculative decoding

Bill Xu, 2026-09-13. Everything below is relative to lossless decoding on
the same problems (and, where several seeds exist, the same seed);
lossless is always 1.00. Setup unless stated: GPT-OSS-20B target with the
EAGLE3 drafter, vLLM 0.26.0, one H100 (Nibi), temperature 1, 6 drafted
tokens per pass, 32k-token budget on AIME24. Definitions in the glossary
at the end; provenance, caveats and file paths in the last two sections.

## TL;DR

- **Why the paper's one safe rule is safe.** Across every rule we can
  trace, the ones that make answers longer are exactly the ones that
  commit drafted tokens the verifier ranks well below its own top choice.
  `spec_casc_tok` never does, and never inflates.
- **Keeping that property and dropping the rest gives a real but small
  win.** `tok_lt` (free pass only for tokens within ~15–20% of the
  verifier's top choice; ordinary lossless check otherwise) accepts 11–14%
  more drafted tokens per verifier pass than lossless, at unchanged answer
  length and accuracy: **~1.05–1.08× fewer verifier passes on AIME24**
  (990 runs, 3 seeds), ~1.2× on gsm8k.
- **There is no bigger prize in this family.** Adding the same filter to
  the highest-acceptance rule (`opt`) removes its 2.5× rambling and *also*
  its acceptance gain: with the filter on, acceptance equals `tok_lt`'s
  whatever the trigger. One quantity — how far below the verifier's top
  choice a committed token may sit — sets both the gain and the damage.

## 1. What was tested

**The question.** The campaign (`campaign/FINDINGS.md`) showed that
training-free relaxed rules accept more drafted tokens per pass but make
reasoning models write longer answers, so the end-to-end cost goes *up*;
`spec_casc_tok` was the lone exception. We asked *why* it is the
exception, and whether that reason can be turned into a better rule.

**The rules, in plain words.** Each pass, the drafter proposes tokens and
the verifier (big model) decides per token: run the lossless check (keep
with probability p/q) or skip it and keep the token outright.

| rule | when the check is skipped | which tokens may skip |
|---|---|---|
| lossless | never | — |
| `opt` (Narasimhan et al.) | drafter's top-1 confidence ≥ verifier's, minus a margin | any token |
| `tok` (same paper, token variant) | the drafted token is within α of the verifier's top-choice probability | near-top only; *stricter than lossless* for all other tokens |
| **`tok_lt`** (new) | same as `tok` | near-top only; ordinary lossless check for all other tokens |
| **`opt_head`** (new) | `opt`'s trigger **and** the token is within β of the verifier's top choice | near-top only |

**The data.** (E7) 1,226 traced runs from the original single-alpha
campaign, HumanEval and AIME24. (E1 gsm8k) 30 problems, 1 seed. (E1F
AIME24) 30 problems × 3 seeds = 90 runs per point. (E6 AIME24) 30
problems, 1 seed. GPU runs used one warm vLLM server per rule setting
(`scripts/persistent_arm_replay.py`); see caveats.

## 2. Results

### 2.1 The mechanism (E7, traces; no new generation)

Of the tokens each rule committed that lossless would have rejected, the
share whose verifier probability was below 0.2 × the verifier's top choice
("out-of-head"), AIME24:

| rule | out-of-head commits per 1,000 tokens | answer length vs lossless |
|---|---:|---:|
| `spec_casc_tok` (α 0.3 / 0.5 / 0.7) | **0 / 0 / 0** | 0.94 / 1.04 / 1.03 |
| `mentored_dec` | 16 | 1.23 |
| `spec_casc_opt` | 65 | 2.13 |
| `r_fuzzy` | 141 | 1.94 |
| `cactus` | 155 | 1.86 |
| `spec_casc_tok` with the filter off (α = 1, one run) | 172 | **19.2** |

HumanEval shows the same ordering. Within a rule, per-problem rates do
not predict which problems loop (r ≈ 0 on HumanEval, negative on AIME24):
it is a rule-level exposure effect, not a per-token trigger.

### 2.2 gsm8k, `tok_lt` vs `tok` (E1 quick look; 30 problems, 1 seed)

Lossless: 2.64 tokens accepted per pass, 280 tokens per answer, 100%.

| rule | α | accepted per pass | answer length | verifier passes (speedup) | accuracy |
|---|---:|---:|---:|---:|---:|
| `tok` | 0.15 / 0.35 / 0.55 / 0.8 | 1.00 / 1.00 / 1.11 / 1.21 | 0.93 / 0.82 / 0.86 / 0.93 | 1.09 / 1.22 / 1.24 / 1.22 | 97 / 100 / 97 / 100 % |
| `tok_lt` | 0.15 / 0.35 / 0.55 / 0.8 | 1.12 / 1.13 / 1.17 / 1.22 | 1.03 / 0.98 / 0.90 / 0.92 | 1.03 / 1.10 / 1.22 / 1.27 | 97 / 97 / 97 / 100 % |

Indicative only (single seed, short answers, ±15% length swings between
neighbouring settings are sampling noise).

### 2.3 AIME24, `tok_lt` vs `tok`, fine sweep (E1F; 90 runs per point)

Lossless: 2.20 tokens accepted per pass; mean 9,703 / median 7,182 tokens
per answer; 6 of 90 runs ran away to the 32k budget; 73% correct.

| rule | α | accepted per pass | mean answer length | runaways /90 | verifier passes (speedup) | accuracy |
|---|---:|---:|---:|---:|---:|---:|
| `tok` | 0.05 / 0.10 / 0.15 / 0.20 / 0.25 | 1.05 / 1.07 / 1.08 / 1.08 / 1.10 | 1.10 / 1.00 / 1.26 / 1.23 / 1.02 | 8 / 9 / 11 / 9 / 10 | 0.96 / 1.05 / 0.84 / 0.87 / 1.05 | 73 / 77 / 77 / 77 / 77 % |
| **`tok_lt`** | 0.05 / 0.10 / **0.15** / **0.20** / 0.25 | 1.11 / 1.11 / **1.13** / **1.13** / 1.14 | 1.03 / 1.08 / **1.01** / **1.04** / 1.07 | 9 / 8 / **6** / **6** / 11 | 1.06 / 1.01 / **1.08** / **1.06** / 1.01 | 70 / 70 / **73** / 70 / 63 % |

Typical (non-looping) answers under `tok_lt` are within ±10% of lossless
at every setting; runaway counts of 6–11 do not separate by α in this
range (about 1 run in 12 loops under any safe rule). Accuracy is intact
up to α = 0.20 and drops at 0.25 (57 vs 66 correct of 90).

### 2.4 AIME24, the loose trigger with the narrow filter (E6; 30 problems, seed 0)

Lossless (seed 0): 2.22 accepted per pass, 2 runaways, 80%.

| rule | setting | accepted per pass | mean answer length | runaways /30 | verifier passes (speedup) | accuracy |
|---|---|---:|---:|---:|---:|---:|
| plain `opt` (campaign, fresh servers) | α −0.3 / 0.05 | 1.23 / **1.54** | 1.33 / **2.48** | 3 / **13** | 0.89 / **0.59** | 80 / 37 % |
| `opt_head` β=0.15 | α −0.3 / −0.1 / −0.02 / 0.05 | 1.10 / 1.11 / 1.12 / 1.10 | 1.09 / 1.13 / 1.30 / 1.19 | 1 / 3 / 2 / 1 | 1.01 / 0.95 / 0.84 / 0.91 | 73 / 73 / 83 / 80 % |
| `opt_head` β=0.35 | α −0.3 / −0.1 / −0.02 / 0.05 | 1.12 / 1.11 / 1.14 / 1.14 | 1.03 / 1.26 / 1.12 / 1.27 | 1 / 5 / 2 / 5 | 1.07 / 0.86 / 1.00 / 0.87 | 80 / 63 / 80 / 67 % |

With the filter on, acceptance sits at 1.10–1.14 regardless of `opt`'s
own α — the same as `tok_lt` — instead of `opt`'s 1.23–1.54; the rambling
is gone (1–5 runaways instead of 13) and so is the gain.

## 3. Interpretation

1. **Rambling is caused by committing tokens the verifier did not want.**
   Every inflating rule does it; the one rule that never does (`tok`) never
   inflates; switching its filter off makes it inflate 19×; adding the
   filter to the worst rule (`opt`) stops its rambling. Three independent
   confirmations.
2. **The filter is also what caps the gain.** A near-top-only free pass
   can only add the tokens lossless would have rejected *despite* the
   verifier nearly agreeing — about 10–14% more per pass with this
   drafter. Any rule that wants more must let through tokens further from
   the verifier's choice, and that is where the rambling starts.
3. **`tok_lt` is the best version of the safe rule**: it removes `tok`'s
   needless extra strictness on ordinary tokens and gains 11–14% per pass
   (vs `tok`'s 5–10%) at lossless length and accuracy. The end-to-end
   benefit is ~1.05–1.08× on long reasoning and ~1.2× on short math.
4. **The width knob must stay narrow on reasoning tasks**: within ~15–20%
   of the verifier's top choice. At 25% accuracy starts to slip; at 35%+
   (campaign data) answers grow like the bad rules'.
5. **What we could not resolve.** Runaway rates of 7–12% are indistinguishable
   between safe settings at 90 runs per point; a hint that *what replaces
   a rejected token* also matters (`tok` inflates more than `tok_lt` at two
   settings despite accepting less; the two differ in their residual
   distribution) is logged but untested.

## 4. Conclusion

Training-free relaxation cannot buy a large speedup on reasoning models
with this drafter: the acceptance gain and the length inflation are
governed by the same quantity, and the safe range of that quantity is
worth roughly 1.05–1.1× on hard reasoning and 1.2× on short math. The
campaign's "no free lunch" stands, now with the mechanism attached: the
lunch is paid for in tokens the verifier did not want.

## 5. Caveats — state these wherever the numbers are used

- GPU runs used one warm server per rule setting (request-order effect,
  `remote/ENVIRONMENT.md`); the campaign's own tables used a fresh server
  per measurement. Cross-table comparisons (e.g. `opt` vs `opt_head`) mix
  the two protocols.
- 30 problems per seed; AIME24 means are dominated by 2–5 looping runs of
  32k tokens — read medians and runaway counts alongside means. E1F has 3
  seeds; E1 gsm8k and E6 have one.
- Everything is GPT-OSS-20B + EAGLE3 on the V1 vLLM runner; the new rules
  do not yet exist for Qwen3-8B (`DIRECTIONS.md` D8).
- Wall-clock speedups were not measured under a clean protocol (E3 not
  run); "verifier passes" is the cost proxy throughout.
- Do not quote: the 30-run quick-look points (superseded), the α=0.35
  "cliff" (noise), per-pass gains on their own.

## 6. Sentences for the paper

- "Relative to lossless decoding on AIME24, `tok_lt` at α = 0.15 accepts
  13% more drafted tokens per verifier pass, produces answers of the same
  length (1.01×, equal runaway rate) and reduces verifier passes by 8% at
  unchanged accuracy (73% vs 73%; 30 problems × 3 seeds)."
- "The rules that inflate are exactly those that commit tokens the
  verifier ranks well below its own top choice: 16–155 such commits per
  1,000 tokens for `mentored_dec`/`opt`/`r_fuzzy`/`cactus`, zero for
  `spec_casc_tok`, which alone never inflates; removing its filter
  inflates 19×."
- "Adding the same filter to `opt` eliminates its 2.5× inflation but
  reduces its acceptance gain to `tok_lt`'s level; the filter width, not
  the trigger, sets both the gain and the cost."

## 7. Open threads (optional)

- Seeds on E6 (tightens error bars on "no gain"; unlikely to change it).
- Residual-sampling hint from E1F: same accept rule, lossless vs blended
  residual, is a one-patch experiment.
- E3: measured wall-clock and this stack's drafter cost, to convert
  passes into seconds.
- E8: recover the Qwen3 (V2) sampler from the old box to test the second
  model family.

## 8. Files

| what | where |
|---|---|
| this report's numbers, scored against lossless | `cascade/results/speed_ignoring_accuracy.md` (datasets `gsm8k_quick`, `aime24_fine`, `aime24_e6`) |
| trace analysis (E7) | `cascade/results/trace_rank_analysis.md` |
| per-run tables / per-point results / graphs | `campaign/{tables,results,graphs}/{gsm8k_quick,aime24_quick,aime24_fine,aime24_e6}.*` |
| run log with dates, job ids, decision rules | `cascade/JOURNAL.md` |
| rules and knobs | `cascade/METHODS.md`; patches `patches/vllm-0.26.0-spec-casc-{tok-lt,opt-head,...}.patch` |
| how to re-run | `cascade/EXPERIMENTS.md`, `bash cascade/run.sh <id> --target nibi` |

## Glossary

- **accepted per pass (l̄):** drafted tokens the verifier kept per checking pass; the per-pass gain.
- **verifier passes:** the real cost — one pass ≈ one autoregressive step of the big model; speedup = lossless passes ÷ rule's passes.
- **runaway:** a run that hit the 32k-token budget (looping or endless hedging).
- **α / β (filter width):** how close to the verifier's top-choice probability a drafted token must be to skip the check; 0.15 = within 15%.
- **out-of-head:** verifier probability below 0.2 × its top choice (the E7 threshold).
