"""Dilution ladder: hold the item fixed, grow the context, find the knee.

The question is the production one -- how much can you inject before the model
stops finding things -- and whether reasoning effort moves that point. If the
modes break at different lengths, effort buys context headroom and is worth
paying for on long calls. If they break together, the fix is retrieval, not
effort.

Only ONE thing varies from the flat baseline: the amount of surrounding text.
The prompt, the question and the gold are untouched, so these numbers are
directly comparable to runs/flat40/. No output-format requirements were added
for the same reason -- one variable at a time.

The judge sees the ORIGINAL short question, never the haystack. It is grading
the answer, not re-reading the corpus, and feeding it 10k tokens would cost real
money to make the grading worse.
"""
from __future__ import annotations

import argparse, json, random, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .budget import Call, Ledger, now
from .client import MODES, LunaClient
from .haystack import dilute, ntok
from .judge import grade_final_value, grade_llm
from .suites import _load_ifb, load

ROOT = Path(__file__).parent.parent
FINAL_VALUE = {"uc4_formula"}


class TokenBucket:
    """Throttle to the account's tokens-per-minute ceiling.

    The first ladder run lost 285 of 480 calls to 429s, and the loss scaled with
    rung size -- 2/120 at baseline, 112/120 at 10k. That is a TPM limit, not a
    request limit, and it is the failure mode a context-length experiment is
    most exposed to: the bigger the prompt, the likelier the call dies, so the
    surviving sample at the top rungs is both tiny and biased toward whatever
    slipped through a limit window. Read naively it looks exactly like a knee.

    A request-count concurrency cap cannot express this, because the cost of a
    call varies 20x across the ladder. So we meter tokens, not requests.
    """

    def __init__(self, tpm: int):
        self.capacity = float(tpm)
        self.tokens = float(tpm)
        self.rate = tpm / 60.0
        self.ts = time.monotonic()
        self.lock = threading.Lock()

    def settle(self, actual: int, reserved: int) -> None:
        """Repay the gap between what we reserved and what the call really cost."""
        if actual <= reserved:
            return
        with self.lock:
            self.tokens -= (actual - reserved)

    def take(self, n: int) -> None:
        n = min(float(n), self.capacity)
        while True:
            with self.lock:
                now_ = time.monotonic()
                self.tokens = min(self.capacity,
                                  self.tokens + (now_ - self.ts) * self.rate)
                self.ts = now_
                if self.tokens >= n:
                    self.tokens -= n
                    return
                wait = (n - self.tokens) / self.rate
            time.sleep(min(wait, 5.0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="ladder")
    ap.add_argument("--suites", default="uc2_spot,uc3_rules,uc4_formula")
    ap.add_argument("--rungs", default="0,2500,5000,10000",
                    help="target context tokens; 0 = undiluted baseline")
    ap.add_argument("--items", type=int, default=10)
    ap.add_argument("--positions", default="",
                    help="comma-separated needle fractions 0..1; forces position "
                         "instead of leaving it to chance (see bug #9)")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cap-usd", type=float, default=5.0)
    ap.add_argument("--tpm", type=int, default=180_000,
                    help="token/min ceiling to throttle under; account limit is "
                         "200k for gpt-5.6-luna, so leave headroom for the judge")
    a = ap.parse_args()

    rungs = [int(x) for x in a.rungs.split(",")]
    positions = [float(x) for x in a.positions.split(",") if x.strip()]
    modes = a.modes.split(",")
    raw = {r["id"]: r for r in _load_ifb()}
    outdir = ROOT / "runs" / a.run
    outdir.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(outdir / "ledger.jsonl", cap_usd=a.cap_usd)
    client = LunaClient(ROOT)
    judge = LunaClient(ROOT)

    units, dropped = [], []
    for s in a.suites.split(","):
        items = load(s)
        random.Random(a.seed).shuffle(items)      # same seed/order as the runner
        for it in items[: a.items]:
            row = raw.get(it.id)
            if row is None or not (row.get("context") or "").strip():
                dropped.append((s, it.id, "no single-passage context")); continue
            q = row["question"]
            for rung in rungs:
                if rung == 0:
                    user, meta = it.user, {"n_tokens": ntok(it.user), "n_distractors": 0,
                                           "needle_frac": 0.0, "target_pos": None}
                    for m in modes:
                        units.append((s, it, q, user, rung, m, meta))
                    continue
                for pos in (positions or [None]):
                    d = dilute(row, q, it.gold, rung, seed=a.seed, position=pos)
                    if d is None:
                        dropped.append((s, it.id, f"dilute failed at {rung}")); continue
                    meta = {"n_tokens": d.n_tokens, "n_distractors": d.n_distractors,
                            "needle_frac": round(d.needle_frac, 3),
                            "target_pos": pos}
                    for m in modes:
                        units.append((s, it, q, d.user, rung, m, meta))

    print(f"{len(units)} units, {len(dropped)} dropped")
    for d in dropped[:10]:
        print("   dropped:", d)

    bucket = TokenBucket(a.tpm)

    def work(u):
        s, it, q, user, rung, mode, meta = u
        # reserve this call's input cost before issuing it; output is small by
        # comparison on these suites and the headroom below 200k absorbs it
        bucket.take(meta["n_tokens"] + ntok(it.system))
        r = client.complete(it.system, user, mode)
        ledger.record(Call(now(), s, it.id, mode, rung, "target", r.prompt_tokens,
                           r.completion_tokens, r.reasoning_tokens, r.latency_s,
                           r.ok, r.error))
        if not r.ok:
            return None
        if r.truncated:
            return dict(suite=s, item_id=it.id, rung=rung, mode=mode, correct=False,
                        method="truncated", **meta)
        g = grade_final_value if s in FINAL_VALUE else grade_llm
        bucket.take(ntok(q) + ntok(it.gold) + ntok(r.text) + 200)
        v, jr = g(judge, q, it.gold, r.text)          # original question, not haystack
        ledger.record(Call(now(), s, it.id, mode, rung, "judge", jr.prompt_tokens,
                           jr.completion_tokens, jr.reasoning_tokens, jr.latency_s,
                           jr.ok, jr.error))
        return dict(suite=s, item_id=it.id, rung=rung, mode=mode, correct=v.correct,
                    method=v.method, detail=v.detail[:200], prediction=r.text,
                    gold=it.gold, think=r.reasoning_tokens, latency=r.latency_s, **meta)

    # Stream each result to disk as it lands. A previous run was killed at 39/480
    # units and lost every graded result because they were buffered until the end.
    res = []
    lock = threading.Lock()
    with open(outdir / "results.jsonl", "w", buffering=1) as f:
        with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
            for x in ex.map(work, units):
                if not x:
                    continue
                with lock:
                    f.write(json.dumps(x) + "\n")
                res.append(x)
    print(f"\n{len(res)} results -> {outdir/'results.jsonl'}")
    ledger.summary()


if __name__ == "__main__":
    main()
