# viewer

Local webapp for the qualitative-review job: pick a case, put up to three
arms side by side, and see exactly where and how their outputs diverge.

Zero dependencies (Python stdlib only):

```
python3 viewer/server.py            # http://127.0.0.1:8377
python3 viewer/server.py --port 9000 --runs-root runs
```

## What it does

- **Case picker** — every dir under `runs/` whose children contain
  `output.txt` (handles `aime24_fresh/case_NNN/seed_0/...` and the pilot
  layouts alike), grouped by benchmark root, filterable. Arm dropdowns show
  the verdict from that root's `summary.json` when one exists.
- **3-pane diff** — the byte-identical shared prefix across the selected
  arms is dimmed, and a red `◆` marks the first divergence ("jump to
  divergence" scrolls all panes there). Pairwise first-diff offsets are in
  the bar up top. Same-seed runs are identical until the first accept
  decision that differs, so `◆` is the first behavioral difference.
- **find** — phrase search with per-pane match counts (e.g. count
  `Not bad` to size a repetition loop), Enter / Shift-Enter to cycle.
- **trace@◆** — per pane, the `proposals.jsonl` rows around the divergence
  position (±10 tokens): draft vs emitted text, `strict_would_accept`,
  `lossy_would_accept`, `emission_source`, marker/guard flags.
- **flags** — per-run counts of `lossy_only_accepted` tokens and guard
  interventions (`lossy_would_accept: true` but rejected — i.e. the guard
  flipped a decision), with the first intervention positions listed.

## Trace-reading gotchas (mirrors what the fields actually mean)

- `lossy_would_accept` records what the *unguarded* relaxed rule would have
  done; a guard intervention is `lossy_would_accept && !actually_accepted`.
- `token_marker_guard_active` flags marker tokens themselves (informational);
  in the future-guard arms the forced-strict window is the K positions
  *after* a marker and has no explicit per-row flag.
- `accepted_draft`, `recovered` and `bonus` rows are all emitted tokens;
  rejected drafts share an `output_position` with the `recovered` row that
  replaced them. The char→token mapping reconstructs the emitted stream from
  the trace and can drift a few tokens from `output.txt` (discarded post-EOS
  round, channel-token rendering).
