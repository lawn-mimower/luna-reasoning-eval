"""Test-item loaders, one per use case.

Every suite yields Item(id, system, user, gold, meta) so the runner does not
need to know anything about where an item came from.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "datasets"
RULEPACKS = Path(__file__).parent / "rulepacks"

# Items whose gold answer is wrong, unanswerable from its own context, or a
# duplicate. Established by full reads of all 406 items; see datasets/README.md.
QUARANTINE = {
    "NUM_009",  # gold breaches the 18-month cap stated in its own context
    "NUM_010",  # arithmetic error: 1 Apr + 120 days = 30 Jul, gold says 29 Jul
    "NUM_086",  # invents an unstated premise (Rs 375 crore residual base)
    "NUM_118",  # applies a proviso absent from the shipped context
    "NUM_126",  # gold argues both conclusions in one paragraph
    "NUM_134",  # 26 weeks from 15 Mar 2024 = 13 Sep, gold says "approximately 15 Sep"
    "NUM_135",  # question premise is arithmetically false
    "NUM_137",  # gold contradicts the question's "no non-working days" stipulation
    "REG_008",  # gold gives the trigger threshold, question asked for the allowance
    "REG_079",  # question posits a term loan, context covers only deposits
    "REG_090",  # exact duplicate of NUM_093
    "TMP_059",  # context collapses two amendment generations the gold separates
    "TMP_075",  # gold asserts a 3-year validity unverifiable from context
    "TMP_086",  # gold is explicit speculation ("likely subsumed into")
    "CON_005",  # literal reading of the context supports the opposite label
    "CON_010",  # compound question forced into one yes/no
    "CON_050",  # compound question forced into one yes/no
    "CON_052",  # quantifier mismatch between question and gold
}

# Mislabelled: task_type == numerical_reasoning but answer_type == extractive.
# These are table lookups with no formula and must not enter the UC4 pool.
NOT_NUMERIC = {
    "NUM_076", "NUM_079", "NUM_082", "NUM_083", "NUM_084", "NUM_085", "NUM_087",
    "NUM_088", "NUM_089", "NUM_090", "NUM_091", "NUM_092", "NUM_093", "NUM_094",
    "NUM_098", "NUM_099", "NUM_101", "NUM_102", "NUM_106",
}


@dataclass
class Item:
    id: str
    system: str
    user: str
    gold: str
    meta: dict = field(default_factory=dict)


def _rulepack(name: str) -> str:
    p = RULEPACKS / f"{name}.md"
    return p.read_text().strip() if p.exists() else ""


def _load_ifb() -> list[dict]:
    rows = json.loads((DATA / "indiafinbench/indiafinbench_qa.json").read_text())
    return [r for r in rows if r["id"] not in QUARANTINE]


def _context_of(r: dict) -> str:
    if "context_a" in r:
        return (f"PASSAGE A ({r.get('regulation_a', r.get('document_a', 'source A'))}):\n"
                f"{r['context_a']}\n\n"
                f"PASSAGE B ({r.get('regulation_b', r.get('document_b', 'source B'))}):\n"
                f"{r['context_b']}")
    label = r.get("regulation") or r.get("document") or "source"
    return f"PASSAGE ({label}):\n{r['context']}"


# --------------------------------------------------------------------------
# UC2 — spotting relevant information
# --------------------------------------------------------------------------
def uc2_spot() -> list[Item]:
    """Locating the relevant fact in a supplied passage.

    regulatory_interpretation with an extractive gold, plus the 19 items
    mislabelled numerical_reasoning that are really table lookups. These are
    find-the-span tasks: the answer is present, the work is finding it.
    """
    rules = _rulepack("uc2_spot")
    out = []
    for r in _load_ifb():
        is_lookup = (r["task_type"] == "regulatory_interpretation"
                     or r["id"] in NOT_NUMERIC)
        if r["answer_type"] != "extractive" or not is_lookup:
            continue
        out.append(Item(
            id=r["id"],
            system=rules,
            user=f"{_context_of(r)}\n\nQUESTION: {r['question']}",
            gold=r["answer"],
            meta={"task_type": r["task_type"], "difficulty": r["difficulty"],
                  "answer_type": r["answer_type"], "source": r["source"]},
        ))
    return out


# --------------------------------------------------------------------------
# UC3 — applying rules present in the context
# --------------------------------------------------------------------------
def uc3_rules(include_contradiction: bool = False) -> list[Item]:
    """Applying a rule that is present in the prompt.

    temporal_reasoning — work out what is in force, or when a period expires,
    by applying the effective dates and periods stated in the passage. The
    answer is a conclusion, not a span.

    contradiction_detection is EXCLUDED by default: golds run 49 No / 9 Yes,
    so a constant-'No' predictor scores 85% and the subset cannot separate
    reasoning modes. Enable only if scoring balanced accuracy.

    This is the thinnest suite (71 items with contradiction off) and is the
    reason we are sourcing a dedicated rule-application corpus.
    """
    rules = _rulepack("uc3_rules")
    keep = {"temporal_reasoning"}
    if include_contradiction:
        keep.add("contradiction_detection")
    out = []
    for r in _load_ifb():
        if r["task_type"] not in keep:
            continue
        if r["answer_type"] == "calculated":       # those belong to UC4
            continue
        out.append(Item(
            id=r["id"],
            system=rules,
            user=f"{_context_of(r)}\n\nQUESTION: {r['question']}",
            gold=r["answer"],
            meta={"task_type": r["task_type"], "difficulty": r["difficulty"],
                  "answer_type": r["answer_type"], "source": r["source"]},
        ))
    return out


# --------------------------------------------------------------------------
# UC4 — formulae, graded on the final computed value only
# --------------------------------------------------------------------------
def uc4_formula() -> list[Item]:
    """Per the v1 decision: score the final value, not the formula.

    A correct final value implies the right numbers went into the right formula
    in the overwhelming majority of cases. It cannot catch a wrong formula that
    happens to produce the right number, nor compensating errors. Accepted
    limitation — revisit if UC4 scores look implausibly high.

    The model is still asked to emit the formula and its substitutions, so the
    transcripts support a later structural pass without re-running anything.
    """
    rules = _rulepack("uc4_formula")
    out = []
    for r in _load_ifb():
        if r["answer_type"] != "calculated" or r["id"] in NOT_NUMERIC:
            continue
        out.append(Item(
            id=r["id"],
            system=rules,
            user=f"{_context_of(r)}\n\nQUESTION: {r['question']}",
            gold=r["answer"],
            meta={"task_type": r["task_type"], "difficulty": r["difficulty"],
                  "answer_type": r["answer_type"], "source": r["source"]},
        ))
    return out


def uc3_contradiction(balanced: bool = True, seed: int = 42) -> list[Item]:
    """Deciding whether two passages of regulation conflict.

    The full clean set is 49 No / 9 Yes, so raw accuracy is meaningless -- a
    constant "No" scores 84.5%. Balanced sampling takes all 9 Yes and 9 No,
    matched on difficulty (the Yes items happen to be a clean 3 easy / 3 medium
    / 3 hard, so the match is exact). Chance becomes 50%.

    18 items is small, and the ceiling on precision here is the 9 Yes items --
    that is true of any scheme, balanced subsample or balanced accuracy over
    all 58. The subsample buys interpretability; balanced accuracy over the
    full set would use all 49 No items and estimate No-recall more tightly.
    Use balanced=False with per-class scoring if you want that instead.
    """
    import random
    rules = _rulepack("uc3_rules")
    rows = [r for r in _load_ifb() if r["task_type"] == "contradiction_detection"]
    if balanced:
        rng = random.Random(seed)
        yes = [r for r in rows if r["answer"].strip() == "Yes"]
        no = [r for r in rows if r["answer"].strip() == "No"]
        want = {}
        for r in yes:
            want[r["difficulty"]] = want.get(r["difficulty"], 0) + 1
        picked = []
        for diff, n in want.items():
            pool = [r for r in no if r["difficulty"] == diff]
            picked += rng.sample(pool, min(n, len(pool)))
        rows = yes + picked
    return [Item(
        id=r["id"],
        system=rules,
        user=f"{_context_of(r)}\n\nQUESTION: {r['question']}",
        gold=r["answer"],
        meta={"task_type": r["task_type"], "difficulty": r["difficulty"],
              "answer_type": r["answer_type"], "source": r["source"],
              "label": r["answer"].strip()},
    ) for r in rows]


SUITES = {
    "uc2_spot": uc2_spot,
    "uc3_contradiction": uc3_contradiction,
    "uc3_rules": uc3_rules,
    "uc4_formula": uc4_formula,
    # uc1_tools runs through BFCL out-of-process; see harness/bfcl/README.md
}


def load(name: str) -> list[Item]:
    if name not in SUITES:
        raise KeyError(f"unknown suite {name!r}; have {sorted(SUITES)}")
    return SUITES[name]()


# --------------------------------------------------------------------------
# UC3b — RuleArena airline: apply a full published rulebook to a fact pattern
# --------------------------------------------------------------------------
RULEARENA = DATA / "rulearena" / "airline"


def uc3_rulearena(levels=(0, 1, 2)) -> list[Item]:
    """RuleArena airline baggage fees (MIT). ACL 2025.

    The complete 3,597-token American Airlines baggage rulebook goes in the
    prompt; the item is a passenger with 5-11 bags; the gold is the total fee,
    computed deterministically by the benchmark's own scorer.

    Gold values are near-unique (97/94/98 distinct per level) and appear
    verbatim in neither the fact pattern nor the rulebook (0/300 for both), so
    there is nothing to extract and no majority class to guess.

    The scorer re-orders bags into the cheapest allocation of free-bag
    allowances, an optimisation the published rules never state. Rather than
    dropping the 74/300 items where that changes the answer, the prompt states
    the requirement explicitly and additionally asks for the charge ordering —
    which is itself a signal we want, since downstream compute() consumes
    values in a fixed order.
    """
    import os
    import sys

    # compute_answer.py reads fee_tables/*.csv by relative path at import time,
    # so it has to be imported from inside its own directory.
    cwd = os.getcwd()
    try:
        os.chdir(RULEARENA)
        sys.path.insert(0, str(RULEARENA))
        import compute_answer as CA
        tables = CA.load_checking_fee()
    finally:
        os.chdir(cwd)

    rules = (RULEARENA / "reference_rules.txt").read_text()
    system = _rulepack("uc3_rulearena").replace("{RULES}", rules)

    out = []
    for lvl in levels:
        path = RULEARENA / "synthesized_problems" / f"comp_{lvl}.jsonl"
        for i, line in enumerate(path.read_text().splitlines()):
            if not line.strip():
                continue
            r = json.loads(line)
            gold = int(CA.compute_answer(**r["info"], check_base_tables=tables)[0])
            out.append(Item(
                id=f"RA_air_{lvl}_{i:03d}",
                system=system,
                user=(r["prompt"].rstrip() + "\n\nCompute the total cost for this "
                      "passenger step by step, without omitting any bag."),
                gold=f"${gold}",
                meta={"task_type": "rule_application", "difficulty": ["easy", "medium", "hard"][lvl],
                      "answer_type": "calculated", "source": "RuleArena/airline",
                      "complexity": lvl, "n_bags": len(r["info"]["bag_list"]),
                      "customer_class": r["info"]["customer_class"],
                      "routine": r["info"]["routine"]},
            ))
    return out


SUITES["uc3_rulearena"] = uc3_rulearena


# --------------------------------------------------------------------------
# UC3c — RuleArena tax: fill a US Form 1040 from the forms in the prompt
# --------------------------------------------------------------------------
TAXDIR = DATA / "rulearena" / "tax"


def uc3_tax(levels=(0, 1, 2)) -> list[Item]:
    """RuleArena US individual income tax (MIT). ACL 2025.

    The prompt carries a partly-filled Form 1040 plus whichever schedules the
    taxpayer's situation attaches -- itemized deductions, Schedule C
    self-employment, education credits, Schedule 8812. Fields the model must
    compute are marked [__]. Complexity is the number of attached schedules:
    comp_0 has none, comp_2 has two to four, and they feed each other (the
    self-employment deductible moves AGI, which moves the child-credit phase-out).

    Golds are 100% unique per level, spanning -$24,981 to $55,292, roughly
    70% owing / 30% refund -- no majority class to guess.

    Faithful to the benchmark's own build_prompt: values substituted from
    data[], "$TBD" entries become [__] blanks, then top-level payer fields.
    """
    import os
    import sys

    cwd = os.getcwd()
    try:
        os.chdir(TAXDIR)
        sys.path.insert(0, str(TAXDIR))
        sys.modules.setdefault("openai", __import__("types").ModuleType("openai"))
        sys.modules["openai"].OpenAI = object
        from micro_evaluation import compute_answer
        from structured_forms import TaxPayer
        from prompt import (basic_forms, itemized_forms, self_employ_forms,
                            edu_forms, schedule_8812)
        rows_by_level = {lvl: json.loads((TAXDIR / "synthesized_problems" /
                                          f"comp_{lvl}.json").read_text())
                         for lvl in levels}
        golds = {lvl: [compute_answer(TaxPayer(**r["pydantic"]))[0] for r in rows]
                 for lvl, rows in rows_by_level.items()}
    finally:
        os.chdir(cwd)

    template = _rulepack("uc3_tax")
    out = []
    for lvl, rows in rows_by_level.items():
        for i, r in enumerate(rows):
            payer = r["dict"]
            forms = [basic_forms]
            if payer.get("itemized"):
                forms.append(itemized_forms)
            if payer.get("self_employed"):
                forms.append(self_employ_forms)
            if payer.get("has_student_loans_or_education_expenses"):
                forms.append(edu_forms)
            if payer.get("num_qualifying_children"):
                forms.append(schedule_8812)
            f = "".join(forms)
            for k, v in payer.get("data", {}).items():
                f = f.replace("$" + k, "$" + f"{v:,}" if not isinstance(v, str) else v)
            f = f.replace("$TBD", "[__]")
            for k in ("name", "age", "spouse_age", "blind", "spouse_blind",
                      "filing_status", "itemized", "num_qualifying_children",
                      "num_other_dependents"):
                if k in payer:
                    f = f.replace("$" + k, str(payer[k]))

            g = float(golds[lvl][i])
            out.append(Item(
                id=f"RA_tax_{lvl}_{i:03d}",
                system=template.replace("{FORMS}", f),
                user=(f"Calculate the tax owed by {payer.get('name', 'the payer')} "
                      f"step by step, computing every [__] field."),
                gold=(f"OWED ${g:,.2f}" if g > 0 else f"OVERPAID ${abs(g):,.2f}"),
                meta={"task_type": "rule_application", "answer_type": "calculated",
                      "difficulty": ["easy", "medium", "hard"][lvl],
                      "source": "RuleArena/tax", "complexity": lvl,
                      "raw_gold": round(g, 2),
                      "schedules": sum(bool(payer.get(k)) for k in
                                       ("itemized", "self_employed",
                                        "has_student_loans_or_education_expenses",
                                        "num_qualifying_children"))},
            ))
    return out


SUITES["uc3_tax"] = uc3_tax
