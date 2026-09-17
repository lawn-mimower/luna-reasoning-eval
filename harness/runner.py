"""Batch runner.

Work is a flat queue of (suite, item, mode, rep) units, interleaved across all
suites and all four reasoning modes so that a run stopped early still has
balanced coverage rather than a complete first suite and nothing else.

Batches are executed in parallel. After every batch the ledger is printed and
stop conditions are re-checked, so a run can be halted the moment the spend or
the coverage target is met.
"""
from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

from .budget import Call, Ledger, now
from .client import MODES, LunaClient
from .judge import grade_final_value, grade_llm, grade_numeric
from .suites import Item, SUITES, load

ROOT = Path(__file__).parent.parent
RUNS = ROOT / "runs"

# uc4_formula used to live here. Its golds are prose carrying a regulation
# citation, the working and the answer, so bag-of-numbers grading scored correct
# answers wrong ~57% of the time; it now grades via grade_final_value(). Nothing
# is numeric-graded at present -- the set is kept for suites that become so.
NUMERIC_SUITES: set[str] = set()
FINAL_VALUE_SUITES = {"uc4_formula"}


@dataclass
class Unit:
    suite: str
    item: Item
    mode: str
    rep: int

    @property
    def key(self):
        return (self.suite, self.item.id, self.mode, self.rep)


@dataclass
class Result:
    suite: str
    item_id: str
    mode: str
    rep: int
    correct: bool
    method: str
    detail: str
    prediction: str
    gold: str
    meta: dict


def build_queue(suites: list[str], modes: list[str], reps: int,
                per_suite: int | None, seed: int) -> list[Unit]:
    rng = random.Random(seed)
    queue: list[Unit] = []
    for name in suites:
        items = load(name)
        rng.shuffle(items)                     # deterministic given the seed
        if per_suite:
            items = items[:per_suite]
        for rep in range(reps):
            for item in items:
                for mode in modes:
                    queue.append(Unit(name, item, mode, rep))
    # Interleave so early stopping still leaves balanced coverage.
    queue.sort(key=lambda u: (u.rep, u.item.id, u.suite, modes.index(u.mode)))
    return queue


def run_unit(u: Unit, client: LunaClient, ledger: Ledger, judge_mode: str,
             judge: LunaClient | None = None) -> Result | None:
    judge = judge or client
    r = client.complete(u.item.system, u.item.user, u.mode)
    ledger.record(Call(now(), u.suite, u.item.id, u.mode, u.rep, "target",
                       r.prompt_tokens, r.completion_tokens, r.reasoning_tokens,
                       r.latency_s, r.ok, r.error))
    if not r.ok:
        return None
    if r.truncated:
        # Output cap hit before the model finished. This is a harness limit, not
        # a model error; recording it as incorrect would bias against the modes
        # that think longest. Excluded from accuracy, counted in the ledger.
        return Result(u.suite, u.item.id, u.mode, u.rep, False, "truncated",
                      f"finish_reason=length at {r.completion_tokens} tokens",
                      r.text, u.item.gold, u.item.meta)

    if u.suite in FINAL_VALUE_SUITES:
        v, jr = grade_final_value(judge, u.item.user, u.item.gold, r.text, judge_mode)
        ledger.record(Call(now(), u.suite, u.item.id, u.mode, u.rep, "judge",
                           jr.prompt_tokens, jr.completion_tokens,
                           jr.reasoning_tokens, jr.latency_s, jr.ok, jr.error))
    elif u.suite in NUMERIC_SUITES:
        v = grade_numeric(r.text, u.item.gold)
        if v.method == "unparseable":          # fall back to the LLM judge
            v, jr = grade_llm(judge, u.item.user, u.item.gold, r.text, judge_mode)
            ledger.record(Call(now(), u.suite, u.item.id, u.mode, u.rep, "judge",
                               jr.prompt_tokens, jr.completion_tokens,
                               jr.reasoning_tokens, jr.latency_s, jr.ok, jr.error))
    else:
        v, jr = grade_llm(judge, u.item.user, u.item.gold, r.text, judge_mode)
        ledger.record(Call(now(), u.suite, u.item.id, u.mode, u.rep, "judge",
                           jr.prompt_tokens, jr.completion_tokens,
                           jr.reasoning_tokens, jr.latency_s, jr.ok, jr.error))

    return Result(u.suite, u.item.id, u.mode, u.rep, v.correct, v.method, v.detail,
                  r.text, u.item.gold, u.item.meta)


def main() -> None:
    ap = argparse.ArgumentParser(description="Luna reasoning-mode eval runner")
    ap.add_argument("--run", default="default", help="run name; results land in runs/<name>/")
    ap.add_argument("--suites", default=",".join(SUITES))
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--batch", type=int, default=20, help="units per parallel batch")
    ap.add_argument("--reps", type=int, default=5, help="repetitions per (item, mode)")
    ap.add_argument("--per-suite", type=int, default=100,
                    help="items sampled per suite; 0 for all")
    ap.add_argument("--cap-usd", type=float, default=None,
                    help="stop once the ledger reaches this spend")
    ap.add_argument("--max-batches", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--judge-mode", default="none",
                    help="reasoning mode for the grader; keep at none for cost and stability")
    ap.add_argument("--model", default="gpt-5.6-luna",
                    help="model id; use a weaker one as a floor-check control")
    ap.add_argument("--judge-model", default="gpt-5.6-luna",
                    help="grader; pinned to Luna so a control run is not self-graded")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true",
                    help="build the queue and project cost; make no API calls")
    args = ap.parse_args()

    suites = [s for s in args.suites.split(",") if s]
    modes = [m for m in args.modes.split(",") if m]
    outdir = RUNS / args.run
    outdir.mkdir(parents=True, exist_ok=True)

    ledger = Ledger(outdir / "ledger.jsonl", cap_usd=args.cap_usd)
    queue = build_queue(suites, modes, args.reps, args.per_suite or None, args.seed)

    done = ledger.done_keys()
    pending = [u for u in queue if u.key not in done]

    print(f"run          {args.run}")
    print(f"suites       {suites}")
    print(f"modes        {modes}")
    print(f"queue        {len(queue)} units ({len(done)} already done, {len(pending)} pending)")
    print(f"batch size   {args.batch}   concurrency {args.concurrency}")
    print(f"spent so far ${ledger.spent:.3f}" + (f" / cap ${args.cap_usd:.2f}" if args.cap_usd else ""))

    if args.dry_run:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        seen, tin = set(), 0
        for u in pending:
            k = (u.suite, u.item.id)
            if k not in seen:
                seen.add(k)
            tin += len(enc.encode(u.item.system)) + len(enc.encode(u.item.user))
        print(f"\ndry run: {len(pending)} pending units, "
              f"{tin:,} input tokens = ${tin * 0.2 / 1e6:.2f} before any output")
        by_suite: dict[str, int] = {}
        for u in pending:
            by_suite[u.suite] = by_suite.get(u.suite, 0) + 1
        for s, n in sorted(by_suite.items()):
            print(f"  {s:16s} {n:6d} units  ({len({x.item.id for x in pending if x.suite == s})} distinct items)")
        return

    client = LunaClient(ROOT, model=args.model)
    judge = LunaClient(ROOT, model=args.judge_model)
    results_path = outdir / "results.jsonl"
    batch_no = 0

    while pending:
        if ledger.exhausted():
            print(f"\nstopping: spend cap ${args.cap_usd:.2f} reached")
            break
        if args.max_batches and batch_no >= args.max_batches:
            print(f"\nstopping: max-batches {args.max_batches} reached")
            break

        batch, pending = pending[:args.batch], pending[args.batch:]
        batch_no += 1

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(pool.map(lambda u: run_unit(u, client, ledger, args.judge_mode, judge), batch))

        with open(results_path, "a") as f:
            for r in results:
                if r is not None:
                    f.write(json.dumps(asdict(r)) + "\n")

        ok = [r for r in results if r is not None]
        acc = sum(r.correct for r in ok) / len(ok) if ok else 0.0
        print(f"\nbatch {batch_no:3d}  {len(ok)}/{len(batch)} ok  "
              f"batch acc {acc:.1%}  spent ${ledger.spent:.3f}  "
              f"{len(pending)} units left")
        print(ledger.summary())

    print("\n" + "=" * 88)
    print(ledger.summary())
    print(f"\nresults -> {results_path}")


if __name__ == "__main__":
    main()
