# Loop-escape emission-source analysis

Question: in speculative-decoding traces, which emission source breaks degenerate
loops? Prior greedy-trace analysis found 60-70% of escapes came from **bonus**
tokens, hypothesized to be because the bonus token was the only stochastically
sampled one. All runs in this repo are temperature-1.0 (every source is
stochastic), so if bonus still dominates escapes here, stochasticity was not the
explanation -- something structural about bonus positions (fresh target-model
sample after a fully-accepted round, no draft conditioning) breaks loops.

Three stages:

```
1. find_loop_candidates.py   regex scan for consecutive repetition (loose
                             thresholds; judge filters false positives)
                             -> out/candidates.jsonl
2. judge_escapes.py          LLM judge (claude-sonnet-5, structured output):
                             confirms degenerate vs legitimate repetition,
                             quotes the loop ONSET and each escape point
                             verbatim; quotes located via str.find
                             -> out/judged.jsonl
                             Needs: pip install anthropic + ANTHROPIC_API_KEY
                             (or `ant auth login`). ~54 short calls.
3. escape_composition.py     maps onset/escape chars -> trace tokens via the
                             viewer's span machinery (imports viewer/server.py):
                             - composition at escapes / onsets / loop interior
                               vs whole-trace base rate, lift + Wilson CIs
                             - inside-loop rule agreement: would a strict
                               fallback inside the loop change anything
                               (strict_would_accept vs lossy_only_accepted),
                               and how many recovered tokens sat inside loops
                               without breaking them
                             - per-token role labels (onset|interior|escape)
                               -> out/loop_tokens.jsonl
                             -> out/report.md, out/report_escapes.jsonl
```

Run:

```sh
python3 analysis/loop_escape/find_loop_candidates.py
python3 analysis/loop_escape/judge_escapes.py            # needs API creds
python3 analysis/loop_escape/escape_composition.py       # reads out/judged.jsonl
```

Before the judge has run (or to sanity-check without it), stage 3 can
approximate the escape as the end of each detected region:

```sh
python3 analysis/loop_escape/escape_composition.py \
    --from-candidates analysis/loop_escape/out/candidates.jsonl
```

Notes:

- case_key/arm in all outputs match the viewer's addressing, and the report's
  per-escape table includes the judge's verbatim quote -- paste it into the
  viewer's search box to eyeball any escape.
- The escape-token attribution is +-1-2 tokens ambiguous by nature ("does
  'Wait' break the loop, or the token after?"); the report includes an
  escape+-2-window composition as a robustness check.
- Sample size is small (tens of events). The report pools across arms; treat
  per-arm splits as descriptive only.
- `recovered` rows can be split further by `lossy_only_accepted` (strict
  rejection resample vs lossy-leniency acceptance) -- per-escape fields are in
  report_escapes.jsonl.
