#!/usr/bin/env python3
"""Addendum step 1.9 (campaign/addendum/README.md): MT-Bench single-answer
grading of the campaign's MT-Bench completions, turn 1 only, with the
FastChat llm_judge prompts (prompts/mtbench_judge/, fetched 2026-09-29 from
lm-sys/FastChat main: judge_prompts.jsonl, mt_bench/question.jsonl,
mt_bench/reference_answer/gpt-4.jsonl). Categories math/reasoning/coding use
`single-math-v1` with the GPT-4 reference answer (FastChat's NEED_REF_CATS),
every other category `single-v1`; the rating is parsed from `[[rating]]`.

Judge: the strongest Claude model (claude-fable-5-1) through the Message
Batches API (50% price, asynchronous). Differences from FastChat's GPT-4
judge, recorded in every output row: no temperature (Claude Fable 5.1 rejects
sampling parameters; thinking is always on, depth set by --effort), and no
server-side refusal fallback (the Batches API rejects it): a refused request
is recorded as verdict=refusal, not re-routed to another model.

  python3 scripts/addendum_mtbench_judge.py plan      # runs to judge, question mapping check, cost estimate; no API call
  python3 scripts/addendum_mtbench_judge.py submit    # create the batch (needs ANTHROPIC_API_KEY)
  python3 scripts/addendum_mtbench_judge.py collect   # wait for it, parse ratings, write the CSVs
  python3 scripts/addendum_mtbench_judge.py direct [--cancel-batch]  # same requests through the Messages API
                                                      # (standard price), then the CSVs; resumable

"Every arm" = strict and the five campaign rules at every alpha that has
runs (single-knob parameter directories), both targets, every seed present.
A run whose output never reaches an answer (GPT-OSS: no final channel;
Qwen3: no text outside <think> blocks) is not sent to the judge: it gets
score 1 and verdict=no_answer (the reader saw nothing); summaries report the
mean with and without those runs.

--suite speedbench (branch speedbench-oct, README deviation 25): the same judge, effort, Batches API and
no-answer rule on the SPEED-Bench qualitative runs (672 prompts per arm, both targets): step 7's lossless
strict and five rules at their loosest alpha, and step 7.1's five rules at their gentlest alpha
(--settings picks which). SPEED-Bench has no reference answers, so every category uses FastChat's
`single-v1` prompt (MT-Bench used `single-math-v1` with GPT-4 references for math/reasoning/coding).
State, cache and outputs are separate files: analysis/speedbench_judge{_batches.json,_direct.jsonl,.csv,
_summary.csv}; the summary is per (target, arm, category) and per (target, arm, all), with the paired
per-prompt score difference to lossless.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNS = REPO / "runs"
JUDGE_DIR = REPO / "prompts" / "mtbench_judge"
OUT = REPO / "campaign" / "addendum" / "analysis"
STATE = OUT / "mtbench_judge_batches.json"
FIVE = ["mentored_dec", "cactus", "spec_casc_opt", "r_fuzzy", "spec_casc_tok"]
NEED_REF_CATS = {"math", "reasoning", "coding"}
SPECIAL = re.compile(r"<\|[^|>]*\|>")
# Claude Fable 5.1 on the Batches API: $10/$50 per MTok standard, half in a batch.
PRICE_IN, PRICE_OUT = 5.0, 25.0


def answer_text(text: str, target: str) -> str:
    """The part of the completion a user would read (same split as scripts/addendum_analysis.py)."""
    if target == "gpt-oss-20b":
        i = text.find("<|channel|>final")
        if i < 0:
            return ""
        tail = text[i:]
        tail = tail.split("<|message|>", 1)[1] if "<|message|>" in tail else ""
        return SPECIAL.sub("", tail).strip()
    if "</think>" not in text:
        return ""
    parts, inside, pos = [], False, 0
    first_open, first_close = text.find("<think>"), text.find("</think>")
    inside = first_close >= 0 and (first_open < 0 or first_close < first_open)
    for m in re.finditer(r"</?think>", text):
        if not inside:
            parts.append(text[pos:m.start()])
        inside = m.group(0) == "<think>"
        pos = m.end()
    if not inside:
        parts.append(text[pos:])
    return SPECIAL.sub("", "".join(parts)).strip()


def load_judge_data():
    prompts = {d["name"]: d for d in map(json.loads, (JUDGE_DIR / "judge_prompts.jsonl").open())}
    questions = [json.loads(l) for l in (JUDGE_DIR / "question.jsonl").open()]
    refs = {d["question_id"]: d["choices"][0]["turns"][0]
            for d in map(json.loads, (JUDGE_DIR / "reference_answer_gpt-4.jsonl").open())}
    by_text = {q["turns"][0].strip(): q for q in questions}
    return prompts, by_text, refs


def collect_runs(seeds: list[str] | None = None) -> list[dict]:
    prompts, by_text, refs = load_judge_data()
    runs = []
    for ds, target in (("mtbench", "gpt-oss-20b"), ("mtbench_qwen3", "qwen3-8b")):
        for run_json in sorted((RUNS / ds).glob("*/*/case_*/seed_*/run.json")):
            run_dir = run_json.parent
            case, params, method = run_dir.parent.name, run_dir.parent.parent.name, run_dir.parent.parent.parent.name
            if method != "strict" and (method not in FIVE or "_" in params):
                continue
            run = json.loads(run_json.read_text(encoding="utf-8"))
            if run.get("status") != "ok":
                continue
            if seeds is not None and run_dir.name.removeprefix("seed_") not in seeds:
                continue
            case_dir = REPO / "prompts" / ds / case
            question = json.loads((case_dir / "source.json").read_text(encoding="utf-8"))["problem"]
            category = json.loads((case_dir / "metadata.json").read_text(encoding="utf-8"))["category"]
            q = by_text.get(question.strip())
            if q is None:
                # HuggingFaceH4/mt_bench_prompts carries a typo in case_007 ("reprompt top-5 words" for
                # FastChat q121's "returns top-5 words"): match by similarity for the id/reference only;
                # the judge still sees the question text the model was asked.
                import difflib
                best = max(by_text, key=lambda t: difflib.SequenceMatcher(None, t, question.strip()).ratio())
                if difflib.SequenceMatcher(None, best, question.strip()).ratio() < 0.95:
                    raise SystemExit(f"no FastChat question matches {ds}/{case}")
                q = by_text[best]
            alpha = "strict" if method == "strict" else f"{float(params.removeprefix('alpha').replace('neg', '-')):g}"
            answer = answer_text((run_dir / "output.txt").read_text(encoding="utf-8", errors="replace"), target)
            version = "single-math-v1" if category in NEED_REF_CATS else "single-v1"
            fields = {"question": question, "answer": answer}
            if version == "single-math-v1":
                fields["ref_answer_1"] = refs[q["question_id"]]
            runs.append({
                "relpath": str(run_dir.relative_to(RUNS)), "target": target, "method": method, "alpha": alpha,
                "case": case, "seed": run_dir.name.removeprefix("seed_"), "category": category,
                "question_id": q["question_id"], "prompt_version": version, "answer_chars": len(answer),
                "finish_reason": run.get("finish_reason"),
                "system": prompts[version]["system_prompt"],
                "user": prompts[version]["prompt_template"].format(**fields),
            })
    return runs


SB_SETTINGS = {  # setting -> (run-root condition, method -> alpha); step 7 = loosest, step 7.1 = gentlest
    "loosest": ("speedbench", {"strict": "strict", "spec_casc_opt": "0.05", "mentored_dec": "0.75", "cactus": "0.35",
                               "r_fuzzy": "0.25", "spec_casc_tok": "0.8"}),
    "gentlest": ("speedbench_gentle", {"spec_casc_opt": "-0.3", "mentored_dec": "0.15", "cactus": "0.03",
                                       "r_fuzzy": "0.03", "spec_casc_tok": "0.15"}),
}
SB_FAMILIES = (("speedbench", "gpt-oss-20b"), ("speedbench_qwen3", "qwen3-8b"))
SB_PROMPT = "single-v1"  # no reference answers in SPEED-Bench


def sb_params(method: str, alpha: str) -> str:
    return method if method == "strict" else f"alpha{float(alpha):g}".replace("-", "neg")


def collect_runs_sb(settings: list[str]) -> list[dict]:
    """SPEED-Bench runs to judge: every ok seed-0 run of the chosen settings' arms (step 7's strict is the
    lossless arm, setting 'lossless')."""
    prompts = {d["name"]: d for d in map(json.loads, (JUDGE_DIR / "judge_prompts.jsonl").open())}
    runs = []
    for ds, target in SB_FAMILIES:
        for setting in settings:
            condition, arms = SB_SETTINGS[setting]
            for method, alpha in arms.items():
                root = RUNS / "addendum" / condition / target / ds / method / sb_params(method, alpha)
                for run_json in sorted(root.glob("case_*/seed_0/run.json")):
                    run_dir = run_json.parent
                    run = json.loads(run_json.read_text(encoding="utf-8"))
                    if run.get("status") != "ok":
                        continue
                    case = run_dir.parent.name
                    case_dir = REPO / "prompts" / ds / case
                    question = json.loads((case_dir / "source.json").read_text(encoding="utf-8"))["problem"]
                    category = json.loads((case_dir / "metadata.json").read_text(encoding="utf-8"))["category"]
                    answer = answer_text((run_dir / "output.txt").read_text(encoding="utf-8", errors="replace"), target)
                    runs.append({
                        "relpath": str(run_dir.relative_to(RUNS)), "target": target, "method": method, "alpha": alpha,
                        "setting": "lossless" if method == "strict" else setting, "case": case, "seed": "0",
                        "category": category, "question_id": case, "prompt_version": SB_PROMPT,
                        "answer_chars": len(answer), "finish_reason": run.get("finish_reason"),
                        "system": prompts[SB_PROMPT]["system_prompt"],
                        "user": prompts[SB_PROMPT]["prompt_template"].format(question=question, answer=answer),
                    })
    return runs


def suite_runs(args) -> list[dict]:
    return collect_runs_sb(args.settings) if args.suite == "speedbench" else collect_runs(args.seeds)


def suite_paths(args) -> tuple[pathlib.Path, pathlib.Path, str]:
    """(batch state file, direct-call cache, output stem) of the suite."""
    if args.suite == "speedbench":
        return OUT / "speedbench_judge_batches.json", OUT / "speedbench_judge_direct.jsonl", "speedbench_judge"
    return STATE, OUT / "mtbench_judge_direct.jsonl", "mtbench_judge"


def prompt_hash() -> str:
    """sha256 of the single-v1 judge prompt (system prompt + template) as sent."""
    import hashlib
    p = {d["name"]: d for d in map(json.loads, (JUDGE_DIR / "judge_prompts.jsonl").open())}[SB_PROMPT]
    return hashlib.sha256((p["system_prompt"] + "\n\n" + p["prompt_template"]).encode()).hexdigest()


def custom_id(i: int) -> str:
    return f"r{i:06d}"


KEY_FILE = pathlib.Path.home() / ".config" / "lossy-token-eff" / "judge.env"


def load_key_file() -> None:
    """KEY=VALUE lines from ~/.config/lossy-token-eff/judge.env into the environment (values never printed;
    a variable already set in the environment wins)."""
    import os
    if not KEY_FILE.is_file():
        return
    for line in KEY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        os.environ.setdefault(name, value.strip().strip('"').strip("'"))


def cmd_plan(args) -> int:
    runs = suite_runs(args)
    to_judge = [r for r in runs if r["answer_chars"] > 0]
    chars_in = sum(len(r["system"]) + len(r["user"]) for r in to_judge)
    tok_in = chars_in / 3.5
    tok_out = len(to_judge) * args.est_output_tokens
    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT
    by = {}
    for r in runs:
        key = (r["target"], r.get("setting", ""), r["method"]) if args.suite == "speedbench" else (r["target"], r["seed"])
        by[key] = by.get(key, 0) + 1
    print(f"{len(runs)} {args.suite} runs; {len(runs) - len(to_judge)} have no answer")
    print("runs per arm:", by)
    print(f"to judge: {len(to_judge)} requests, ~{tok_in / 1e6:.1f}M input tokens, ~{tok_out / 1e6:.1f}M output tokens "
          f"(assumed {args.est_output_tokens}/request incl. thinking) -> ~${cost:.0f} with {args.model} on the Batches API")
    if args.suite == "speedbench":
        print(f"judge prompt {SB_PROMPT} sha256 {prompt_hash()}")
    return 0


def cmd_submit(args) -> int:
    load_key_file()
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    state_path, _, _ = suite_paths(args)
    runs = [r for r in suite_runs(args) if r["answer_chars"] > 0]
    state = json.loads(state_path.read_text()) if state_path.is_file() else {"batches": []}
    done = {rel for b in state["batches"] for rel in b["ids"].values()}
    runs = [r for r in runs if r["relpath"] not in done]
    if not runs:
        print("nothing new to judge")
        return 0
    client = anthropic.Anthropic()
    ids, requests = {}, []
    start = sum(len(b["ids"]) for b in state["batches"])
    for i, r in enumerate(runs, start=start):
        cid = custom_id(i)
        ids[cid] = r["relpath"]
        requests.append(Request(custom_id=cid, params=MessageCreateParamsNonStreaming(
            model=args.model, max_tokens=16000, system=r["system"],
            output_config={"effort": args.effort},
            messages=[{"role": "user", "content": r["user"]}],
        )))
    batch = client.messages.batches.create(requests=requests)
    state["batches"].append({"id": batch.id, "model": args.model, "effort": args.effort,
                             "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ids": ids})
    state_path.write_text(json.dumps(state, indent=1) + "\n")
    print(f"created batch {batch.id} with {len(requests)} requests ({args.model}, effort {args.effort})")
    return 0


RATING = re.compile(r"\[\[(\d+\.?\d*)\]\]")
RATING_LOOSE = re.compile(r"\[(\d+\.?\d*)\]")
DIRECT_CACHE = OUT / "mtbench_judge_direct.jsonl"  # one line per run judged by `direct`


def verdict_of(msg, model: str, effort: str, api: str) -> dict:
    row = {"judge_model": model, "judge_effort": effort, "judge_api": api,
           "judge_model_served": msg.model, "stop_reason": msg.stop_reason}
    if msg.stop_reason == "refusal":
        row.update(verdict="refusal", score=None)
    else:
        text = "".join(block.text for block in msg.content if block.type == "text")
        m = RATING.search(text) or RATING_LOOSE.search(text)
        row.update(verdict="ok" if m else "parse_error", score=float(m.group(1)) if m else None, judge_text=text[-600:])
    return row


def direct_results(path: pathlib.Path = DIRECT_CACHE) -> dict[str, dict]:
    out = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["relpath"]] = row
    return out


def cmd_direct(args) -> int:
    """Judge through the Messages API (streamed, --workers at a time) every run not scored yet by a batch
    or an earlier direct call; --cancel-batch first cancels unfinished batches in the state file. Same
    prompts, model and effort as `submit`; standard (not batch) price. Resumable."""
    load_key_file()
    import anthropic
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = anthropic.Anthropic(max_retries=8)
    state_path, cache_path, _ = suite_paths(args)
    state = json.loads(state_path.read_text()) if state_path.is_file() else {"batches": []}
    if args.cancel_batch:
        for b in state["batches"]:
            if b.get("canceled"):
                continue
            if client.messages.batches.retrieve(b["id"]).processing_status != "ended":
                client.messages.batches.cancel(b["id"])
                b["canceled"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                print(f"canceled batch {b['id']}", flush=True)
        state_path.write_text(json.dumps(state, indent=1) + "\n")
    done = direct_results(cache_path)
    if args.suite == "speedbench":
        # a batch still running scores its own runs; an ended batch's scores are in the last `collect` output, so only
        # its errored / unparsed requests are judged here
        pending = {rel for b in state["batches"] if not b.get("canceled")
                   and client.messages.batches.retrieve(b["id"]).processing_status != "ended" for rel in b["ids"].values()}
        stem_csv = OUT / f"{suite_paths(args)[2]}.csv"
        # a refusal or an unparsable verdict is the judge's answer (kept, as in step 1.9); only API failures retry
        batch_ok = ({r["relpath"] for r in csv.DictReader(stem_csv.open(encoding="utf-8"))
                     if r["judge_api"] == "batch" and not r["verdict"].startswith("batch_")} if stem_csv.is_file() else set())
        done = {**done, **{rel: {} for rel in pending | batch_ok}}
    runs = [r for r in suite_runs(args) if r["answer_chars"] > 0 and r["relpath"] not in done]
    print(f"{len(runs)} run(s) to judge directly ({len(done)} already judged or in a batch)", flush=True)

    def judge(r: dict) -> dict:
        with client.messages.stream(model=args.model, max_tokens=16000, system=r["system"],
                                    output_config={"effort": args.effort},
                                    messages=[{"role": "user", "content": r["user"]}]) as stream:
            msg = stream.get_final_message()
        return {"relpath": r["relpath"], **verdict_of(msg, args.model, args.effort, "messages"),
                "input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
                "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    tok_in = tok_out = failed = 0
    with ThreadPoolExecutor(args.workers) as pool, cache_path.open("a", encoding="utf-8") as out:
        futures = {pool.submit(judge, r): r for r in runs}
        for i, fut in enumerate(as_completed(futures), start=1):
            try:
                row = fut.result()
            except anthropic.APIError as exc:  # after the SDK's own retries; rerun `direct` to retry
                failed += 1
                print(f"{futures[fut]['relpath']}: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
                continue
            out.write(json.dumps(row) + "\n")
            out.flush()
            tok_in += row["input_tokens"]
            tok_out += row["output_tokens"]
            if i % 50 == 0 or i == len(runs):
                cost = tok_in / 1e6 * 2 * PRICE_IN + tok_out / 1e6 * 2 * PRICE_OUT
                print(f"{i}/{len(runs)} judged, {failed} failed, ~${cost:.2f} so far", flush=True)
    if failed:
        print(f"{failed} request(s) failed; run `direct` again to retry them")
        return 1
    args.no_wait = True
    return cmd_collect(args)


SB_CATS = ["coding", "math", "humanities", "stem", "writing", "summarization", "roleplay", "rag", "multilingual",
           "reasoning", "qa"]  # step 7's order


def boot_ci(x, rng, np) -> tuple[float, float]:
    boot = x[rng.integers(0, len(x), size=(10000, len(x)))].mean(axis=1)
    return round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)


def sb_summary(rows: list[dict], np) -> list[dict]:
    """Per (target, arm, category) and (target, arm, all): n, no-answer count, mean score with a 95% bootstrap
    interval (10,000 resamples over prompts, numpy seed 20261001), the answered-only mean, and the paired per-prompt
    difference arm - lossless (step 7's strict) on the prompts both have, with its bootstrap interval."""
    rng = np.random.default_rng(20261001)
    order = {"lossless": 0, "loosest": 1, "gentlest": 2}
    arms = sorted({(r["target"], r["setting"], r["method"], r["alpha"]) for r in rows},
                  key=lambda a: (a[0], order[a[1]], a[2]))
    lossless = {(r["target"], r["case"]): r["score"] for r in rows if r["setting"] == "lossless" and r["score"] is not None}
    out = []
    for target, setting, method, alpha in arms:
        for cat in ["all", *SB_CATS]:
            cell = [r for r in rows if (r["target"], r["setting"], r["method"], r["alpha"]) == (target, setting, method, alpha)
                    and (cat == "all" or r["category"] == cat)]
            if not cell:
                continue
            scores = np.array([r["score"] for r in cell if r["score"] is not None], float)
            answered = np.array([r["score"] for r in cell if r["score"] is not None and r["verdict"] == "ok"], float)
            row = {"target": target, "setting": setting, "method": method, "alpha": alpha, "category": cat,
                   "n": len(cell), "n_scored": len(scores), "n_no_answer": sum(r["verdict"] == "no_answer" for r in cell),
                   "n_refusal": sum(r["verdict"] == "refusal" for r in cell),
                   "n_parse_error": sum(r["verdict"] == "parse_error" for r in cell)}
            for name, x in (("mean_score", scores), ("mean_score_answered_only", answered)):
                if len(x):
                    row[name] = round(float(x.mean()), 4)
                    row[f"{name}_ci_lo"], row[f"{name}_ci_hi"] = boot_ci(x, rng, np)
            if setting != "lossless":
                d = np.array([r["score"] - lossless[(target, r["case"])] for r in cell
                              if r["score"] is not None and (target, r["case"]) in lossless], float)
                row["n_pairs"] = len(d)
                if len(d):
                    row["mean_diff_vs_lossless"] = round(float(d.mean()), 4)
                    row["mean_diff_vs_lossless_ci_lo"], row["mean_diff_vs_lossless_ci_hi"] = boot_ci(d, rng, np)
            out.append(row)
    return out


def cmd_collect(args) -> int:
    load_key_file()
    import anthropic
    import numpy as np

    client = anthropic.Anthropic()
    state_path, cache_path, stem = suite_paths(args)
    state = json.loads(state_path.read_text()) if state_path.is_file() else {"batches": []}
    runs = {r["relpath"]: r for r in suite_runs(args)}
    scored = {}
    tokens = {"batch_in": 0, "batch_out": 0, "direct_in": 0, "direct_out": 0}
    def retrying(fn, what: str):
        """Transient API trouble (5xx, e.g. a 503 'credential validation failed', or a dropped network) must
        not lose a submitted batch: keep retrying for up to 6 hours; 4xx errors still raise."""
        deadline = time.time() + 6 * 3600
        while True:
            try:
                return fn()
            except (anthropic.APIConnectionError, anthropic.InternalServerError) as exc:
                if time.time() > deadline:
                    raise
                print(f"{what}: transient {type(exc).__name__}: {str(exc)[:120]} -- retrying in 60 s", flush=True)
                time.sleep(60)
            except anthropic.APIStatusError as exc:
                if exc.status_code < 500 or time.time() > deadline:
                    raise
                print(f"{what}: HTTP {exc.status_code} {str(exc)[:120]} -- retrying in 60 s", flush=True)
                time.sleep(60)

    for b in state["batches"]:
        while True:
            batch = retrying(lambda: client.messages.batches.retrieve(b["id"]), "retrieve")
            if batch.processing_status == "ended":
                break
            if getattr(args, "no_wait", False) and not b.get("canceled"):
                print(f"batch {b['id']}: {batch.processing_status}, {batch.request_counts.processing} processing, "
                      f"{batch.request_counts.succeeded} succeeded -- not waiting", flush=True)
                batch = None  # still running: use what `direct` judged instead
                break
            print(f"batch {b['id']}: {batch.processing_status}, {batch.request_counts.processing} processing", flush=True)
            time.sleep(60)
        if batch is None:
            continue
        for result in retrying(lambda: list(client.messages.batches.results(b["id"])), "results"):
            rel = b["ids"][result.custom_id]
            if result.result.type != "succeeded":
                row = {"judge_model": b["model"], "judge_effort": b["effort"], "judge_api": "batch",
                       "judge_model_served": "", "stop_reason": "", "verdict": f"batch_{result.result.type}", "score": None}
            else:
                row = verdict_of(result.result.message, b["model"], b["effort"], "batch")
                tokens["batch_in"] += result.result.message.usage.input_tokens
                tokens["batch_out"] += result.result.message.usage.output_tokens
            scored[rel] = row
    for rel, row in direct_results(cache_path).items():  # direct calls fill whatever the batches did not score
        tokens["direct_in"] += row.get("input_tokens") or 0
        tokens["direct_out"] += row.get("output_tokens") or 0
        if rel not in scored or scored[rel].get("score") is None:
            scored[rel] = row
    rows = []
    for rel, r in sorted(runs.items()):
        s = scored.get(rel)
        if r["answer_chars"] == 0:
            s = {"verdict": "no_answer", "score": 1.0, "judge_model": "", "judge_effort": "", "judge_api": "",
                 "judge_model_served": "", "stop_reason": ""}
        if s is None:
            continue
        rows.append({k: r.get(k, "") for k in ("relpath", "target", "setting", "method", "alpha", "case", "seed",
                                               "category", "question_id", "prompt_version", "answer_chars",
                                               "finish_reason")} | s)
    fields = ["relpath", "target", "method", "alpha", "case", "seed", "category", "question_id", "prompt_version",
              "answer_chars", "finish_reason", "judge_model", "judge_effort", "judge_api", "judge_model_served",
              "stop_reason", "verdict", "score"]
    if args.suite == "speedbench":
        fields.insert(1, "setting")
    with (OUT / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    cost = ((tokens["batch_in"] * PRICE_IN + tokens["batch_out"] * PRICE_OUT)
            + 2 * (tokens["direct_in"] * PRICE_IN + tokens["direct_out"] * PRICE_OUT)) / 1e6
    print(f"judge tokens {tokens} -> ${cost:.2f} (batch at ${PRICE_IN:g}/${PRICE_OUT:g} per MTok, direct at twice that)")
    if args.suite == "speedbench":
        summary = sb_summary(rows, np)
        state["cost"] = {**tokens, "usd": round(cost, 2), "prompt": SB_PROMPT, "prompt_sha256": prompt_hash(),
                         "computed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        state_path.write_text(json.dumps(state, indent=1) + "\n")
        with (OUT / f"{stem}_summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(k for r in summary for k in r)),
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(summary)
        print(f"wrote {stem}.csv ({len(rows)} rows) and {stem}_summary.csv ({len(summary)} rows)")
        return 0
    rng = np.random.default_rng(20261001)
    summary = []
    arms = sorted({(r["target"], r["method"], r["alpha"], r["seed"]) for r in rows})
    for target, method, alpha, seed in arms:
        cell = [r for r in rows if (r["target"], r["method"], r["alpha"], r["seed"]) == (target, method, alpha, seed)]
        scores = np.array([r["score"] for r in cell if r["score"] is not None], float)
        answered = np.array([r["score"] for r in cell if r["score"] is not None and r["verdict"] == "ok"], float)
        row = {"target": target, "method": method, "alpha": alpha, "seed": seed, "n_runs": len(cell),
               "n_scored": len(scores), "n_no_answer": sum(r["verdict"] == "no_answer" for r in cell),
               "n_refusal": sum(r["verdict"] == "refusal" for r in cell),
               "n_parse_error": sum(r["verdict"] == "parse_error" for r in cell)}
        for name, x in (("mean_score", scores), ("mean_score_answered_only", answered)):
            if len(x):
                boot = x[rng.integers(0, len(x), size=(10000, len(x)))].mean(axis=1)
                row[name] = round(float(x.mean()), 4)
                row[f"{name}_ci_lo"] = round(float(np.percentile(boot, 2.5)), 4)
                row[f"{name}_ci_hi"] = round(float(np.percentile(boot, 97.5)), 4)
        summary.append(row)
    with (OUT / f"{stem}_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(k for r in summary for k in r)), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    print(f"wrote {stem}.csv ({len(rows)} rows) and {stem}_summary.csv ({len(summary)} arms)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="claude-fable-5-1")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--est-output-tokens", type=int, default=1500)
    parser.add_argument("--seeds", nargs="+", default=["0"], help="Request seeds to judge (default: 0, the campaign's runs).")
    parser.add_argument("--suite", default="mtbench", choices=["mtbench", "speedbench"])
    parser.add_argument("--settings", nargs="+", default=["loosest", "gentlest"], choices=sorted(SB_SETTINGS),
                        help="speedbench suite: which settings' arms (step 7 loosest + its lossless strict; step 7.1 "
                             "gentlest). Collect needs every setting that was submitted.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("plan", cmd_plan), ("submit", cmd_submit)):
        sub.add_parser(name).set_defaults(fn=fn)
    p = sub.add_parser("collect")
    p.add_argument("--no-wait", action="store_true", help="Skip batches still running instead of waiting for them.")
    p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("direct")
    p.add_argument("--cancel-batch", action="store_true", help="Cancel unfinished batches in the state file first.")
    p.add_argument("--workers", type=int, default=16)
    p.set_defaults(fn=cmd_direct)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
