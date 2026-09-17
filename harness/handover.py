"""Handover ladder: same tax problem, cut into 1 / 2 / 3 / 4 API calls.

THE QUESTION. Production chains agents: one computes, hands a value to the next,
which does further work. What an agent passes forward is not its reasoning but a
compaction of it, so there are two ways to poison step k+1 -- the reasoning was
wrong and the summary carries the error faithfully, or the reasoning was right
and the summary drops or distorts what the next step needed. The second is the
nastier one: every single-step metric says the step succeeded.

WHAT VARIES. Only the number of API boundaries. The work is identical at every
depth -- the same Form 1040, the same 19.5k-token rulebook, the same arithmetic.
Depth 4 is not a harder problem than depth 1, it is the same problem chopped
into more pieces. So any accuracy difference across depths is the cost of
handover and nothing else.

THE CUTS ARE REAL. RuleArena's own compute_answer() populates the intermediate
values as it goes, so total income, AGI and taxable income all have deterministic
gold. Those are the boundaries -- the form's own lines, not splits invented to
pad a ladder. Depth 8 was considered and rejected: the remaining stages have no
separately verifiable gold, and cutting there would measure our arbitrary
splitting rather than the model's handover.

TWO CONDITIONS.
  live  -- each stage receives the previous stage's ACTUAL output. Errors compound.
  clean -- each stage receives the GOLD intermediate. Isolates per-stage ability.
The gap between them is the price of a handover.

MEASURED PER HOP, mechanically, no judge:
  faithfulness -- does the CARRY payload match the value the step's own working
                  derived? A step that computes 84,300 and passes 84,000 has
                  corrupted the chain while looking correct in isolation.
  sufficiency  -- does the payload carry the fields the next stage needs?
Both are string comparisons against values we already hold.
"""
from __future__ import annotations

import argparse, json, os, re, sys, types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .budget import Call, Ledger, now
from .client import MODES, LunaClient
from .ladder import TokenBucket
from .suites import load

ROOT = Path(__file__).parent.parent
TAX = ROOT / "datasets/rulearena/tax"

# (key, human label, gold attribute on the mutated TaxPayer)
STAGES = [
    ("TOTAL_INCOME", "Form 1040 lines 1-9: every income component and their total "
                     "(line 9). Include Schedule 1 additional income if attached.",
     "computed_total_income"),
    ("AGI", "Form 1040 line 10-11: total adjustments, then adjusted gross income.",
     "adjusted_gross_income"),
    ("TAXABLE_INCOME", "Form 1040 lines 12-15: deductions (standard or itemized), "
                       "qualified business income deduction, and taxable income.",
     "computed_taxable_income"),
    ("FINAL", "Form 1040 lines 16-37: tax on taxable income, Schedule 2 additional "
              "taxes, credits, payments, and the final amount owed or overpaid.",
     None),   # graded against the suite's existing final gold
]

# how the four stages merge at each depth
DEPTHS = {1: [[0, 1, 2, 3]],
          2: [[0, 1], [2, 3]],
          3: [[0, 1], [2], [3]],
          4: [[0], [1], [2], [3]]}


def gold_intermediates(level: int, idx: int) -> dict:
    """RuleArena's own arithmetic, read off the object compute_answer() mutates."""
    cwd = os.getcwd()
    try:
        os.chdir(TAX); sys.path.insert(0, str(TAX))
        sys.modules.setdefault("openai", types.ModuleType("openai"))
        sys.modules["openai"].OpenAI = object
        from micro_evaluation import compute_answer
        from structured_forms import TaxPayer
        rows = json.loads((TAX / "synthesized_problems" / f"comp_{level}.json").read_text())
        p = TaxPayer(**rows[idx]["pydantic"])
        final = compute_answer(p)[0]
    finally:
        os.chdir(cwd)
    out = {k: getattr(p, attr, None) for k, _, attr in STAGES if attr}
    out["FINAL"] = float(final)
    return out


CARRY_RE = re.compile(r"^\s*CARRY\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
NUM_RE = re.compile(r"-?\$?[\d,]+\.?\d*")


def parse_carry(text: str) -> dict:
    """CARRY: KEY=value; KEY=value  -> {KEY: float}"""
    m = CARRY_RE.search(text)
    if not m:
        return {}
    out = {}
    # stage_instruction() asks for "KEY=v, KEY=v" but this split on ";" alone,
    # so every two-key payload parsed as one field: the first value was kept and
    # the second SILENTLY DROPPED. All 96 two-key hops were scored insufficient
    # while emitting perfectly correct payloads, and the dropped value never
    # reached the next stage -- corrupting the live arm at depths 2 and 3.
    for part in re.split(r"[;,]", m.group(1)):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        nums = NUM_RE.findall(v)
        if nums:
            try:
                out[k.strip().upper()] = float(nums[0].replace("$", "").replace(",", ""))
            except ValueError:
                pass
    return out


def stage_instruction(stage_ids: list[int], carried: dict, is_last: bool) -> str:
    todo = "\n".join(f"- {STAGES[i][1]}" for i in stage_ids)
    given = ""
    if carried:
        given = ("\nVALUES ALREADY COMPUTED BY THE PREVIOUS STEP -- use these as given, "
                 "do not recompute them:\n"
                 + "\n".join(f"  {k} = {v:,.2f}" for k, v in carried.items()) + "\n")
    if is_last:
        tail = ("\nEnd with exactly:\nANSWER: $<amount owed, or negative if overpaid>")
    else:
        keys = ", ".join(f"{STAGES[i][0]}=<value>" for i in stage_ids)
        tail = (f"\nEnd with exactly one line handing your results to the next step:\n"
                f"CARRY: {keys}\n"
                f"Values must be the ones you derived above, copied exactly.")
    return f"{given}\nCOMPUTE ONLY THESE STEPS:\n{todo}\n{tail}"


def run_chain(client, item, depth, mode, condition, golds, ledger, bucket,
              ntok) -> dict:
    carried, hops = {}, []
    groups = DEPTHS[depth]
    for gi, stage_ids in enumerate(groups):
        is_last = gi == len(groups) - 1
        user = item.user + "\n" + stage_instruction(stage_ids, carried, is_last)
        reserved = ntok(item.system) + ntok(user) + 1500
        bucket.take(reserved)
        r = client.complete(item.system, user, mode)
        bucket.settle(r.prompt_tokens + r.completion_tokens, reserved)
        ledger.record(Call(now(), "uc3_handover", item.id, mode, depth, "target",
                           r.prompt_tokens, r.completion_tokens, r.reasoning_tokens,
                           r.latency_s, r.ok, r.error))
        if not r.ok:
            return {"error": r.error[:120], "hops": hops}
        emitted = parse_carry(r.text)
        # faithfulness: did the payload carry the number this step actually derived?
        faithful = None
        if not is_last and emitted:
            faithful = True
            for i in stage_ids:
                k, _, attr = STAGES[i]
                if k in emitted and attr and golds.get(k) is not None:
                    # compare the payload against the step's own stated working
                    body = r.text[: r.text.upper().rfind("CARRY:")] if "CARRY:" in r.text.upper() else r.text
                    stated = []
                    for x in NUM_RE.findall(body):
                        try:
                            stated.append(float(x.replace("$", "").replace(",", "")))
                        except ValueError:
                            pass
                    if stated and not any(abs(emitted[k] - s) < 0.51 for s in stated):
                        faithful = False
        hops.append({"stage_ids": stage_ids, "emitted": emitted,
                     "faithful": faithful, "think": r.reasoning_tokens,
                     "latency": round(r.latency_s, 1),
                     "sufficient": all(STAGES[i][0] in emitted for i in stage_ids)
                                   if not is_last else None,
                     "text": r.text[-600:]})
        if is_last:
            # The tax rulepack's own gold format is "OWED $x" / "OVERPAID $x", and
            # the model follows it -- "ANSWER: OVERPAID $16734.00". A signed-number
            # regex alone scored 38 of 48 high-mode chains unparseable when their
            # answers were right, which read as a catastrophic collapse at high
            # effort. Accept the word form, the "$-16734" form, and "-$16734".
            pred = None
            m = re.search(r"ANSWER\s*:\s*(OWED|OVERPAID)\s*\$?\s*([\d,]+\.?\d*)",
                          r.text, re.I)
            if m:
                v = float(m.group(2).replace(",", ""))
                pred = -v if m.group(1).upper() == "OVERPAID" else v
            else:
                m = re.search(r"ANSWER\s*:\s*\$?\s*(-?)\s*\$?\s*([\d,]+\.?\d*)",
                              r.text, re.I)
                if m:
                    pred = float((m.group(1) or "") + m.group(2).replace(",", ""))
            gold = golds["FINAL"]
            return {"pred": pred, "gold": gold,
                    "correct": pred is not None and abs(pred - gold) < 1.0,
                    "hops": hops}
        # feed the next stage
        if condition == "clean":
            carried.update({STAGES[i][0]: golds[STAGES[i][0]] for i in stage_ids
                            if golds.get(STAGES[i][0]) is not None})
        else:
            carried.update(emitted)
    return {"hops": hops}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="handover")
    ap.add_argument("--items", type=int, default=12)
    ap.add_argument("--levels", default="0,1,2")
    ap.add_argument("--depths", default="1,2,3,4")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--conditions", default="live")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--tpm", type=int, default=170_000)
    ap.add_argument("--cap-usd", type=float, default=6.0)
    a = ap.parse_args()

    import tiktoken
    enc = tiktoken.get_encoding("o200k_base")
    ntok = lambda s: len(enc.encode(s))

    levels = tuple(int(x) for x in a.levels.split(","))
    items = load("uc3_tax")
    by_level = {}
    for it in items:
        by_level.setdefault(it.meta["complexity"], []).append(it)
    chosen = []
    per = max(1, a.items // len(levels))
    for lvl in levels:
        chosen += by_level.get(lvl, [])[:per]

    outdir = ROOT / "runs" / a.run
    outdir.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(outdir / "ledger.jsonl", cap_usd=a.cap_usd)
    client = LunaClient(ROOT)
    bucket = TokenBucket(a.tpm)

    units = [(it, d, m, c)
             for it in chosen
             for d in (int(x) for x in a.depths.split(","))
             for m in a.modes.split(",")
             for c in a.conditions.split(",")]
    print(f"{len(chosen)} items x depths x modes x conditions = {len(units)} chains")

    gcache = {}

    def work(u):
        it, d, m, c = u
        key = it.id
        if key not in gcache:
            lvl, idx = int(it.id.split("_")[2]), int(it.id.split("_")[3])
            gcache[key] = gold_intermediates(lvl, idx)
        res = run_chain(client, it, d, m, c, gcache[key], ledger, bucket, ntok)
        return {"item_id": it.id, "level": it.meta["complexity"], "depth": d,
                "mode": m, "condition": c, **res}

    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        out = list(ex.map(work, units))
    with open(outdir / "results.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(f"{len(out)} chains -> {outdir/'results.jsonl'}")
    ledger.summary()


if __name__ == "__main__":
    main()
