"""
Token + cost projection for the Luna reasoning-mode eval.

Luna = gpt-5.6-luna.  Pricing: $0.20 / 1M input, $1.20 / 1M output.
Reasoning (thinking) tokens are billed at the OUTPUT rate.

Real input tokens are measured with tiktoken over the actual downloaded corpora.
Thinking-token budgets are UNVALIDATED GUESSES. They are not sourced from Luna's
docs or from any measurement — they are a generic prior for reasoning-effort tiers,
with an invented step between them. Treat the sensitivity table at the bottom as the
real output, not the point estimate. Replace THINKING[] with observed
`usage.reasoning_tokens` after the calibration run before quoting any figure.

High mode is OUT OF SCOPE — the matrix is none / low / medium.
"""
import json
from pathlib import Path

import tiktoken

ENC = tiktoken.get_encoding("o200k_base")
DATA = Path(__file__).parent / "datasets"

PRICE_IN = 0.20 / 1_000_000
PRICE_OUT = 1.20 / 1_000_000

# --- assumptions ------------------------------------------------------------
# GUESSED. No empirical basis — see module docstring. Calibrate before trusting.
THINKING = {"none": 0, "low": 400, "medium": 1_600}
# Mean visible answer tokens. UC4 emits a JSON formula object, so it runs longer.
VISIBLE = {"default": 120, "uc4": 260, "uc1": 180}
# Fixed prompt overhead per item: system prompt + injected rule pack.
SYSTEM_TOKENS = 200
RULEPACK_TOKENS = 700          # pending subagent output; revise when known
REPEATS = 5                    # runs per item, for variance on mode-to-mode deltas


def ntok(s):
    return len(ENC.encode(s)) if isinstance(s, str) else 0


def measure_indiafinbench():
    rows = json.loads((DATA / "indiafinbench/indiafinbench_qa.json").read_text())
    out = {}
    for r in rows:
        ctx = r.get("context") or (r.get("context_a", "") + r.get("context_b", ""))
        out.setdefault(r["task_type"], []).append(ntok(ctx) + ntok(r["question"]))
    return rows, out


def measure_bns(section_tokens_assumed=450):
    """No section text on disk yet — parameterised until the sourcing agent reports."""
    rows = [json.loads(l) for l in
            open(DATA / "bns_bnss_bsa/bns_bnss_bsa_combined_clean.jsonl", encoding="utf-8-sig")]
    q = [ntok(r["question"]) for r in rows]
    return rows, [x + section_tokens_assumed for x in q]


def cost(n_items, in_tok_each, visible, mode, repeats=REPEATS):
    calls = n_items * repeats
    tin = calls * (in_tok_each + SYSTEM_TOKENS + RULEPACK_TOKENS)
    tout = calls * (visible + THINKING[mode])
    return tin, tout, tin * PRICE_IN + tout * PRICE_OUT


def mean(xs):
    return sum(xs) / len(xs) if xs else 0


if __name__ == "__main__":
    ifb_rows, ifb_by_task = measure_indiafinbench()
    bns_rows, bns_in = measure_bns()

    calc = [r for r in ifb_rows if r["answer_type"] == "calculated"]
    numr = [r for r in ifb_rows if r["task_type"] == "numerical_reasoning"]
    uc4_rows = {r["id"]: r for r in calc + numr}.values()

    def ifb_in(rows):
        return mean([ntok(r.get("context") or
                          (r.get("context_a", "") + r.get("context_b", ""))) + ntok(r["question"])
                     for r in rows])

    print("=" * 92)
    print("MEASURED INPUT TOKENS (tiktoken o200k_base, context + question only)")
    print("=" * 92)
    for t, v in sorted(ifb_by_task.items()):
        print(f"  IndiaFinBench {t:28s} n={len(v):4d}  mean={mean(v):7.0f}  max={max(v):7.0f}")
    print(f"  BNS/BNSS/BSA  question only          n={len(bns_rows):4d}  "
          f"mean={mean([ntok(r['question']) for r in bns_rows]):7.0f}")
    print(f"  BNS/BNSS/BSA  + assumed section text                   mean={mean(bns_in):7.0f}")

    SUITES = [
        ("UC2  spot-relevant   (IFB extractive)",
         len([r for r in ifb_rows if r["answer_type"] == "extractive"]),
         ifb_in([r for r in ifb_rows if r["answer_type"] == "extractive"]), "default"),
        ("UC3  rule-apply      (IFB full 406)",
         len(ifb_rows), ifb_in(ifb_rows), "default"),
        ("UC3b rule-apply      (BNS full 6354)",
         len(bns_rows), mean(bns_in), "default"),
        ("UC3b rule-apply      (BNS sampled 600)",
         600, mean(bns_in), "default"),
        ("UC4  formulae        (IFB numeric)",
         len(uc4_rows), ifb_in(list(uc4_rows)), "uc4"),
    ]

    print()
    print("=" * 92)
    print(f"COST PER SUITE PER REASONING MODE   (x{REPEATS} runs/item, thinking billed as output)")
    print("=" * 92)
    print(f"{'suite':40s} {'items':>6s} " + "".join(f"{m:>11s}" for m in THINKING))
    print("-" * 92)
    grand = dict.fromkeys(THINKING, 0.0)
    for name, n, tin_each, vk in SUITES:
        cells = []
        for m in THINKING:
            _, _, usd = cost(n, tin_each, VISIBLE[vk], m)
            cells.append(f"${usd:>10.2f}")
            if "sampled" in name or "full 6354" not in name:
                pass
        print(f"{name:40s} {n:6d} " + "".join(cells))
    print("-" * 92)

    # headline: the recommended configuration
    print()
    print("=" * 92)
    print("RECOMMENDED CONFIG — IFB 406 + BNS sample 600 + UC4 96, x5 runs, 3 modes")
    print("=" * 92)
    total_in = total_out = total_usd = 0
    for name, n, tin_each, vk in SUITES:
        if "full 6354" in name or "extractive" in name:
            continue
        for m in THINKING:
            ti, to, usd = cost(n, tin_each, VISIBLE[vk], m)
            total_in += ti
            total_out += to
            total_usd += usd
    print(f"  input tokens   {int(total_in):>14,d}   ${total_in * PRICE_IN:>9.2f}")
    print(f"  output+think   {int(total_out):>14,d}   ${total_out * PRICE_OUT:>9.2f}")
    print(f"  TOTAL                          ${total_usd:>9.2f}")
    print()
    print(f"  (BFCL for UC1 not included — item counts pending)")
    print()
    print("  the guess is unvalidated — full-run total vs medium-mode thinking tokens:")
    saved = THINKING["medium"]
    for t in (200, 400, 800, 1_600, 3_200, 6_400, 12_800):
        THINKING["medium"] = t
        tot = sum(cost(n, ti, VISIBLE[v], m)[2]
                  for nm, n, ti, v in SUITES
                  if "full 6354" not in nm and "extractive" not in nm
                  for m in THINKING)
        mark = "  <- current guess" if t == saved else ""
        print(f"    medium={t:6d} think tok/item -> ${tot:7.2f} all-in{mark}")
    THINKING["medium"] = saved
