#!/usr/bin/env python3
"""Run viewer: side-by-side diff of output.txt across arms, with trace lookup.

Zero dependencies -- stdlib only. Launch:

    python3 viewer/server.py [--port 8377] [--runs-root runs]

then open http://127.0.0.1:8377

Endpoints (all GET, JSON unless noted):
    /                    -> static/index.html
    /api/tree            -> {"cases": {case_key: [arm, ...]}}
    /api/case?case=      -> per-arm metadata (run.json fields + summary.json verdict)
    /api/output?case=&arm=            -> {"text": ..., "meta": {...}}
    /api/divergence?case=&arms=a|b|c  -> pairwise + global first-diff char offsets
    /api/trace_at?case=&arm=&char=    -> proposals.jsonl rows around that char offset
    /api/flags?case=&arm=             -> lossy_only / guard-intervention counts

A "case_key" is the directory path relative to the runs root whose children
are arm dirs (each arm dir contains output.txt), e.g.
"aime24_fresh/case_003/seed_0".
"""
import argparse
import json
import os
import re
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

VIEWER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(VIEWER_DIR)
RUNS_ROOT = os.path.join(REPO_ROOT, "runs")

RUN_META_FIELDS = (
    "output_tokens", "finish_reason", "wall_time_seconds", "l_bar",
    "draft_rounds", "eos_reached", "reached_max_new_tokens",
)
SUMMARY_FIELDS = ("verdict", "answer", "reference", "hit_cap", "trace_rounds")
TRACE_ROW_FIELDS = (
    "round", "output_position", "draft_token_text", "emitted_token_text",
    "emission_source", "strict_would_accept", "lossy_would_accept",
    "actually_accepted", "lossy_only_accepted", "token_marker_guard_active",
    "window_guard_active", "window_remaining", "guard_evidence", "p", "q",
)

_tree_cache = None
_summary_cache = {}
_emitted_cache = OrderedDict()  # arm_dir -> (positions, texts, spans, rows)
_EMITTED_CACHE_MAX = 8
_harmony_enc = None
_harmony_err = None


def get_harmony_encoding():
    """GPT-OSS harmony tokenizer, for first-generation traces that recorded
    token ids but not token text. Lazy: only needed for those runs."""
    global _harmony_enc, _harmony_err
    if _harmony_enc is None and _harmony_err is None:
        try:
            from openai_harmony import load_harmony_encoding, HarmonyEncodingName
            _harmony_enc = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        except Exception as e:
            _harmony_err = (f"this run's trace has token ids but no token text, "
                            f"and openai-harmony is unavailable ({e}) -- "
                            f"pip install -r requirements-tokenizer.txt")
    return _harmony_enc, _harmony_err


def decode_token_texts(ids, enc):
    """Per-token text from ids. A multi-token UTF-8 sequence decodes clean
    only as a group: the group's text goes on its first token, '' on the
    rest, keeping concatenation (and therefore char spans) exact."""
    texts = [None] * len(ids)
    i = 0
    while i < len(ids):
        piece = enc.decode([ids[i]])
        if "�" not in piece:
            texts[i] = piece
            i += 1
            continue
        for w in range(2, 9):
            piece = enc.decode(ids[i:i + w])
            if "�" not in piece:
                texts[i] = piece
                for k in range(i + 1, i + w):
                    texts[k] = ""
                i += w
                break
        else:
            texts[i] = piece  # unresolvable; align_spans will zero-width it
            i += 1
    return texts


def scan_tree():
    """Find every dir under RUNS_ROOT containing output.txt; group by parent."""
    cases = {}
    for dirpath, dirnames, filenames in os.walk(RUNS_ROOT):
        if "output.txt" in filenames:
            rel = os.path.relpath(dirpath, RUNS_ROOT)
            case_key, arm = os.path.split(rel)
            cases.setdefault(case_key, []).append(arm)
            dirnames[:] = []  # arm dirs have no nested runs
    return {c: sorted(a) for c, a in sorted(cases.items())}


def get_tree(refresh=False):
    global _tree_cache
    if _tree_cache is None or refresh:
        _tree_cache = scan_tree()
    return _tree_cache


def resolve_arm_dir(case_key, arm):
    """Validate (case, arm) against the scanned tree -- no path tricks."""
    tree = get_tree()
    if case_key not in tree or arm not in tree[case_key]:
        return None
    return os.path.join(RUNS_ROOT, case_key, arm)


def load_summary_rows(top_root):
    """summary.json rows for a benchmark root, keyed by (case_dir, tag)."""
    if top_root in _summary_cache:
        return _summary_cache[top_root]
    rows = {}
    path = os.path.join(RUNS_ROOT, top_root, "summary.json")
    if os.path.isfile(path):
        try:
            with open(path) as f:
                data = json.load(f)
            for r in data.get("rows", []):
                rows[(r.get("case"), r.get("tag"))] = r
        except (json.JSONDecodeError, OSError):
            pass
    _summary_cache[top_root] = rows
    return rows


def arm_meta(case_key, arm):
    arm_dir = resolve_arm_dir(case_key, arm)
    meta = {"arm": arm}
    run_json = os.path.join(arm_dir, "run.json")
    if os.path.isfile(run_json):
        try:
            with open(run_json) as f:
                run = json.load(f)
            for k in RUN_META_FIELDS:
                if k in run:
                    meta[k] = run[k]
        except (json.JSONDecodeError, OSError):
            pass
    parts = case_key.split(os.sep)
    case_dir = next((p for p in parts if p.startswith("case_")), None)
    if case_dir:
        row = load_summary_rows(parts[0]).get((case_dir, arm))
        if row:
            for k in SUMMARY_FIELDS:
                if k in row:
                    meta[k] = row[k]
    meta["has_trace"] = os.path.isfile(os.path.join(arm_dir, "proposals.jsonl"))
    return meta


def read_output(case_key, arm):
    arm_dir = resolve_arm_dir(case_key, arm)
    if arm_dir is None:
        return None
    with open(os.path.join(arm_dir, "output.txt"), errors="replace") as f:
        return f.read()


def first_diff(a, b):
    n = min(len(a), len(b))
    lo, hi = 0, n
    # binary search on the common-prefix length (strings compare fast in C)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if a[:mid] == b[:mid]:
            lo = mid
        else:
            hi = mid - 1
    return lo if (lo < len(a) or lo < len(b)) else -1  # -1: identical


def detect_future_guard_k(arm_dir):
    """K for a future-guard arm: the patch announces 'k=N' in the server log
    lines archived into config.json; fall back to the tag's trailing kN."""
    try:
        with open(os.path.join(arm_dir, "config.json")) as f:
            cfg = json.load(f)
        m = re.search(r"\bk=(\d+)\b", json.dumps(cfg))
        if m:
            return int(m.group(1))
        m = re.search(r"[kK](\d+)$", cfg.get("tag", ""))
        if m:
            return int(m.group(1))
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return 8


def reconstruct_future_guard_windows(raw_rows, k):
    """Replay the future guard's stateful strict window over the trace.

    The tracer records no per-row window flag for the future-guard arms, but
    the mechanics are deterministic (patch module comment): an ACCEPTED draft
    token that is a marker arms a window; the next k verified positions use
    the strict rule; bonus tokens neither consume nor arm; positions after
    the first rejection in a round were never verified. Returns
    {(round, pos_in_round): window_remaining_at_that_position}.
    """
    win = 0
    state = {}
    cur_round = None
    dead = False  # rest of the round was discarded after a rejection
    for r in raw_rows:
        rnd = r.get("round")
        if rnd != cur_round:
            cur_round = rnd
            dead = False
        key = (rnd, r.get("pos_in_round"))
        if r.get("emission_source") == "bonus":
            state[key] = win
            continue
        if dead:
            continue
        state[key] = win
        if win > 0:
            win -= 1
        if not r.get("actually_accepted", False):
            dead = True
            continue
        if r.get("token_marker_guard_active"):
            win = k
    return state


def load_emitted(case_key, arm):
    """Emitted token stream from proposals.jsonl, deduped by output_position.

    accepted_draft, recovered and bonus rows are all emitted tokens; rejected
    drafts share an output_position with the recovered row that replaced them,
    so keep the row that actually landed (last one wins per position).
    """
    arm_dir = resolve_arm_dir(case_key, arm)
    if arm_dir is None:
        return None
    trace_path = os.path.join(arm_dir, "proposals.jsonl")
    if not os.path.isfile(trace_path):
        return None
    cached = _emitted_cache.get(arm_dir)
    if cached is not None:
        _emitted_cache.move_to_end(arm_dir)
        return cached
    raw = []
    with open(trace_path) as f:
        for line in f:
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    by_pos = {}
    for r in raw:
        pos = r.get("output_position")
        if pos is None or (r.get("emitted_token_text") is None
                           and r.get("emitted_token_id") is None):
            continue
        if r.get("actually_accepted", True) or pos not in by_pos:
            by_pos[pos] = r
    # per-row PROVEN rule evidence: only observable where the two rules
    # disagree. 'strict' = the relaxed rule would have accepted but the token
    # was rejected (a guard override); 'relaxed' = strict would have rejected
    # but the token was accepted. Rows where both rules agree are
    # indistinguishable from the trace.
    for r in by_pos.values():
        if r.get("lossy_would_accept") and not r.get("actually_accepted", True):
            r["guard_evidence"] = "strict"
        elif r.get("lossy_only_accepted"):
            r["guard_evidence"] = "relaxed"
    # future-guard arms: replay the intended strict-window mechanics.
    # APPROXIMATE by construction -- validation against the evidence above
    # shows the kernel's actual cross-round carry (and occasionally even
    # in-round arming) does not match the patch's documented mechanics, so
    # this is a visual aid, not ground truth; the evidence field wins.
    if raw and "lookahead" in (raw[0].get("relaxation_method") or ""):
        k = detect_future_guard_k(arm_dir)
        state = reconstruct_future_guard_windows(raw, k)
        for r in by_pos.values():
            rem = state.get((r.get("round"), r.get("pos_in_round")))
            r["window_remaining"] = rem
            r["window_guard_active"] = bool(rem)
    positions = sorted(by_pos)
    rows = [by_pos[p] for p in positions]
    texts = [r.get("emitted_token_text") for r in rows]
    if any(t is None or "�" in t for t in texts):
        # ids are authoritative: first-generation traces recorded no token
        # text at all, and newer traces decoded each token independently,
        # which mangles multi-byte UTF-8 (math symbols like ∈ ∩ ∅ span two
        # tokens) into replacement chars that can never align to output.txt
        enc, err = get_harmony_encoding()
        if enc is None:
            raise RuntimeError(err)
        ids = [r.get("emitted_token_id") for r in rows]
        if all(i is not None for i in ids):
            texts = decode_token_texts(ids, enc)
            for r, t in zip(rows, texts):
                r["emitted_token_text"] = t
                did = r.get("draft_token_id")
                dt = r.get("draft_token_text")
                if did is not None and (dt is None or "�" in dt):
                    r["draft_token_text"] = enc.decode([did])
        else:
            texts = [t or "" for t in texts]
    out_text = read_output(case_key, arm) or ""
    spans = align_spans(texts, out_text)
    result = (positions, texts, spans, rows)
    _emitted_cache[arm_dir] = result
    while len(_emitted_cache) > _EMITTED_CACHE_MAX:
        _emitted_cache.popitem(last=False)
    return result


def align_spans(texts, out_text):
    """Char span of each trace token in output.txt space.

    The trace's emitted stream is not byte-identical to output.txt (channel
    tokens render differently, a discarded post-EOS round trails the cap), so
    walk output.txt and match each token where it actually lands. Tokens with
    no rendering in output.txt get a zero-width span at the current offset.
    """
    spans = []
    o = 0
    n = len(texts)

    def upcoming_match(idx, at, need=20, max_tok=8):
        """Do the next tokens (>= need chars of them) line up at out_text[at:]?
        Long confirmation window so repetitive loop text can't false-match."""
        s = ""
        j = idx
        while j < n and (len(s) < need and j - idx < max_tok):
            s += texts[j]
            j += 1
        return out_text.startswith(s, at)

    i = 0
    while i < n:
        t = texts[i]
        if not t:  # continuation of a multi-byte group; owner has the span
            spans.append((o, o))
            i += 1
            continue
        if out_text.startswith(t, o):
            spans.append((o, o + len(t)))
            o += len(t)
            i += 1
            continue
        # phantom token: the trace recorded it but output.txt never got it
        # (e.g. a bonus token vLLM discarded when the next round's first
        # draft was rejected, or the post-EOS/post-cap round)
        if upcoming_match(i + 1, o):
            spans.append((o, o))
            i += 1
            continue
        # extra chars in output.txt (e.g. the '<|channel|>' head): find where
        # this token resumes, confirmed by the tokens that follow it
        idx = out_text.find(t, o, o + 400)
        while idx != -1 and not upcoming_match(i + 1, idx + len(t)):
            idx = out_text.find(t, idx + 1, o + 400)
        if idx != -1:
            spans.append((idx, idx + len(t)))
            o = idx + len(t)
        else:
            spans.append((o, o))
        i += 1
    return spans


def char_to_token_index(spans, char_offset):
    """Rightmost token whose span starts at or before char_offset."""
    lo, hi = 0, len(spans) - 1
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if spans[mid][0] <= char_offset:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def trace_row_public(r):
    return {k: r.get(k) for k in TRACE_ROW_FIELDS}


def find_loops(text, k=6, min_count=3, max_phrases=12, max_extend=60):
    """Repeated-phrase (loop) detector.

    Word k-grams occurring >= min_count times, each greedily extended to the
    right while >=80% of its occurrences continue with the same word, then
    deduped by word-position overlap (highest count wins). Cheap heuristic,
    good enough to surface degenerate re-derivation loops like the
    'Set {...}? Not bad.' spiral.
    """
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    n = len(words)
    if n < k:
        return []
    grams = {}
    for i in range(n - k + 1):
        key = " ".join(text[a:b] for a, b in words[i:i + k])
        grams.setdefault(key, []).append(i)
    cands = [occ for occ in grams.values() if len(occ) >= min_count]
    extended = []
    for occ in cands:
        L = k
        while L < max_extend:
            nxt = {}
            for i in occ:
                j = i + L
                if j < n:
                    a, b = words[j]
                    nxt.setdefault(text[a:b], []).append(i)
            if not nxt:
                break
            best_occ = max(nxt.values(), key=len)
            if len(best_occ) < max(min_count, len(occ) * 0.8):
                break
            occ, L = best_occ, L + 1
        extended.append((occ, L))
    extended.sort(key=lambda t: (-len(t[0]), -t[1]))
    covered = set()
    out = []
    for occ, L in extended:
        total = len(occ) * L
        overlap = sum(1 for i in occ for d in range(L) if (i + d) in covered)
        if total and overlap / total > 0.5:
            continue
        for i in occ:
            covered.update(range(i, i + L))
        first, last = min(occ), max(occ)
        out.append({
            "phrase": text[words[first][0]:words[first + L - 1][1]],
            "count": len(occ),
            "first_char": words[first][0],
            "last_char": words[last][0],
            "first_frac": words[first][0] / max(1, len(text)),
            "last_frac": words[last][0] / max(1, len(text)),
        })
        if len(out) >= max_phrases:
            break
    return out


# ---------------------------------------------------------------- handlers

def api_tree(q):
    return {"cases": get_tree(refresh="refresh" in q)}


def api_case(q):
    case_key = q.get("case", [""])[0]
    tree = get_tree()
    if case_key not in tree:
        return {"error": f"unknown case {case_key!r}"}
    return {"case": case_key,
            "arms": [arm_meta(case_key, a) for a in tree[case_key]]}


def api_output(q):
    case_key = q.get("case", [""])[0]
    arm = q.get("arm", [""])[0]
    text = read_output(case_key, arm)
    if text is None:
        return {"error": f"unknown run {case_key!r}/{arm!r}"}
    return {"text": text, "meta": arm_meta(case_key, arm)}


def api_divergence(q):
    case_key = q.get("case", [""])[0]
    arms = [a for a in q.get("arms", [""])[0].split("|") if a]
    if len(arms) < 2:
        return {"error": "need at least 2 arms"}
    texts = {}
    for a in arms:
        t = read_output(case_key, a)
        if t is None:
            return {"error": f"unknown run {case_key!r}/{a!r}"}
        texts[a] = t
    pairs = []
    offsets = []
    for i in range(len(arms)):
        for j in range(i + 1, len(arms)):
            d = first_diff(texts[arms[i]], texts[arms[j]])
            pairs.append({"a": arms[i], "b": arms[j], "char": d})
            if d >= 0:
                offsets.append(d)
    global_div = min(offsets) if offsets else -1
    context = None
    if global_div >= 0:
        start = max(0, global_div - 200)
        context = {
            "shared_tail": texts[arms[0]][start:global_div],
            "continuations": {a: texts[a][global_div:global_div + 160]
                              for a in arms},
        }
    return {"pairs": pairs, "global_char": global_div, "context": context}


def api_trace_at(q):
    case_key = q.get("case", [""])[0]
    arm = q.get("arm", [""])[0]
    try:
        char_offset = int(q.get("char", [""])[0])
    except ValueError:
        return {"error": "char must be an integer"}
    try:
        span = min(400, max(5, int(q.get("span", ["10"])[0])))
    except ValueError:
        span = 10
    emitted = load_emitted(case_key, arm)
    if emitted is None:
        return {"error": "no proposals.jsonl for this run"}
    positions, texts, spans, rows = emitted
    if not rows:
        return {"error": "empty trace"}
    idx = char_to_token_index(spans, char_offset)
    lo = max(0, idx - span)
    hi = min(len(rows), idx + span + 1)
    out_rows = []
    for i in range(lo, hi):
        r = trace_row_public(rows[i])
        r["char_start"], r["char_end"] = spans[i]
        r["_at_cursor"] = (i == idx)
        out_rows.append(r)
    return {
        "char": char_offset,
        "output_position": positions[idx],
        "anchor_index": idx - lo,
        "total_tokens": len(rows),
        "note": ("token char spans are aligned to output.txt; tokens with no "
                 "rendering there (channel tokens, post-EOS round) get "
                 "zero-width spans"),
        "rows": out_rows,
    }


def api_loops(q):
    case_key = q.get("case", [""])[0]
    arm = q.get("arm", [""])[0]
    text = read_output(case_key, arm)
    if text is None:
        return {"error": f"unknown run {case_key!r}/{arm!r}"}
    return {"loops": find_loops(text)}


def api_flags(q):
    case_key = q.get("case", [""])[0]
    arm = q.get("arm", [""])[0]
    arm_dir = resolve_arm_dir(case_key, arm)
    if arm_dir is None:
        return {"error": f"unknown run {case_key!r}/{arm!r}"}
    trace_path = os.path.join(arm_dir, "proposals.jsonl")
    if not os.path.isfile(trace_path):
        return {"error": "no proposals.jsonl for this run"}
    n_rows = n_emitted = lossy_only = interventions = markers = 0
    interv_positions = []
    with open(trace_path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_rows += 1
            accepted = r.get("actually_accepted", True)
            if r.get("emitted_token_text") is not None and accepted:
                n_emitted += 1
            if r.get("lossy_only_accepted"):
                lossy_only += 1
            if r.get("token_marker_guard_active"):
                markers += 1
            if (r.get("lossy_would_accept") and not accepted
                    and r.get("emission_source") != "bonus"):
                interventions += 1
                if len(interv_positions) < 200:
                    interv_positions.append(r.get("output_position"))
    return {
        "trace_rows": n_rows,
        "emitted_accepted_or_bonus": n_emitted,
        "lossy_only_accepted": lossy_only,
        "guard_interventions": interventions,
        "guard_intervention_positions": interv_positions,
        "marker_tokens": markers,
    }


ROUTES = {
    "/api/tree": api_tree,
    "/api/case": api_case,
    "/api/output": api_output,
    "/api/divergence": api_divergence,
    "/api/trace_at": api_trace_at,
    "/api/flags": api_flags,
    "/api/loops": api_loops,
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            return self._send_file(os.path.join(VIEWER_DIR, "static", "index.html"),
                                   "text/html; charset=utf-8")
        route = ROUTES.get(parsed.path)
        if route is None:
            return self._send_json({"error": "not found"}, status=404)
        try:
            payload = route(parse_qs(parsed.query))
        except Exception as e:  # surface errors to the UI instead of a blank 500
            payload = {"error": f"{type(e).__name__}: {e}"}
        status = 400 if "error" in payload else 200
        self._send_json(payload, status=status)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            return self._send_json({"error": "missing static file"}, status=500)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet


def main():
    global RUNS_ROOT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8377)
    ap.add_argument("--runs-root", default=RUNS_ROOT)
    args = ap.parse_args()
    RUNS_ROOT = os.path.abspath(args.runs_root)
    tree = get_tree()
    n_runs = sum(len(a) for a in tree.values())
    print(f"scanned {len(tree)} cases / {n_runs} runs under {RUNS_ROOT}")
    print(f"viewer at http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
