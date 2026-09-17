"""Grading.

UC4 is graded deterministically where possible — the gold is a number, so parse
both sides and compare with a tolerance. That is cheaper and more reproducible
than an LLM judge. The LLM judge is the fallback and handles UC2/UC3 free text.

The judge prompt carries an explicit instruction not to punish brevity. This is
not politeness: 45.7% of the extractive golds are heavy paraphrases of their own
context, and 16 golds assert facts their context does not support. A strict judge
marks a context-faithful model wrong on those, which would be a grading artefact
attributed to the model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .client import LunaClient

WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "eighteen": 18, "twenty": 20, "twenty one": 21, "twenty five": 25, "thirty": 30,
    "fifty": 50, "sixty": 60, "ninety": 90, "hundred": 100, "thousand": 1_000,
}
SCALE = {"lakh": 10**5, "lakhs": 10**5, "crore": 10**7, "crores": 10**7}


@dataclass
class Verdict:
    correct: bool
    method: str          # "numeric" | "llm" | "unparseable"
    detail: str = ""


def _numbers(text: str) -> list[float]:
    """Pull scaled numeric quantities out of free text."""
    t = text.lower().replace(",", "")
    out: list[float] = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)?", t):
        val = float(m.group(1))
        if m.group(2):
            val *= SCALE[m.group(2)]
        out.append(val)
    for words, n in WORD_NUM.items():
        for m in re.finditer(rf"\b{words}\s+(lakh|lakhs|crore|crores)\b", t):
            out.append(n * SCALE[m.group(1)])
    return out


def _percentages(text: str) -> list[float]:
    return [float(m.group(1)) for m in
            re.finditer(r"(\d+(?:\.\d+)?)\s*(?:%|per\s*cent|percent)", text.lower())]


def _answer_line(text: str) -> str:
    m = re.search(r"^\s*ANSWER\s*:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else text


def _gold_head(gold: str) -> str:
    """The quantity actually asked for, without the gold's parenthetical working.

    IndiaFinBench golds are written "VALUE (working)" in 58 of 77 cases. The
    working restates the inputs, so parsing the whole string pulls in operands
    that were never the answer -- and a percentage inside the working routes a
    non-percentage answer down the percentage branch. Both were scoring every
    correct answer as wrong.
    """
    return gold.split("(")[0].strip() or gold


def grade_numeric(prediction: str, gold: str) -> Verdict:
    """Final-value-only grading for UC4.

    Limitation, accepted for v1: a wrong formula that happens to produce the
    right number passes, as do compensating errors. The transcripts retain the
    model's stated formula and substitutions for a later structural pass.
    """
    pred = _answer_line(prediction)
    gold = _gold_head(gold)

    gp, pp = _percentages(gold), _percentages(pred)
    if gp:
        # percentage golds are inconsistently rounded (1dp and 2dp both appear),
        # so compare on a tolerance rather than a decimal count
        return Verdict(any(abs(g - p) <= 0.05 for g in gp for p in pp),
                       "numeric", f"gold%={gp} pred%={pp}")

    gn, pn = _numbers(gold), _numbers(pred)
    if not gn:
        return Verdict(False, "unparseable", "no number found in gold")
    if not pn:
        return Verdict(False, "numeric", f"gold={gn} pred=<none>")
    # every quantity the gold requires must appear; several golds carry more
    # than one required figure
    hits = [g for g in gn if any(abs(g - p) <= max(1e-9, abs(g) * 1e-9) for p in pn)]
    return Verdict(len(hits) == len(gn), "numeric", f"gold={gn} pred={pn} matched={hits}")


JUDGE_SYSTEM = """You grade answers to questions about Indian financial regulation.

You are given a QUESTION, a REFERENCE answer, and a CANDIDATE answer. Decide whether the
candidate asserts the same key facts as the reference.

Grade on semantic equivalence of the key facts — numbers, durations, entity names,
thresholds, qualifiers. Not on wording or length.

Mark CORRECT when the candidate asserts every key fact in the reference.

Do NOT mark a candidate wrong for:
- being shorter than the reference
- omitting regulation numbers, effective dates, or background the question did not ask for
- paraphrasing rather than quoting
- omitting explanatory material that the reference includes but the supplied passage does
  not support

Do mark a candidate wrong when it contradicts a key fact, omits one, or invents a fact.

For yes/no questions, only the first Yes/No matters; ignore the justification.

Reply with exactly one line: CORRECT or INCORRECT, then a semicolon and a brief reason."""


def grade_llm(client: LunaClient, question: str, gold: str, prediction: str,
              mode: str = "none") -> tuple[Verdict, object]:
    user = (f"QUESTION:\n{question}\n\nREFERENCE:\n{gold}\n\nCANDIDATE:\n{prediction}")
    r = client.complete(JUDGE_SYSTEM, user, mode=mode, max_tokens=256)
    if not r.ok:
        return Verdict(False, "llm", f"judge failed: {r.error}"), r
    verdict = r.text.strip().upper().startswith("CORRECT")
    return Verdict(verdict, "llm", r.text.strip()[:200]), r


# ---------------------------------------------------------------------------
# UC4 final-value grading.
#
# grade_numeric() above is retained for genuinely numeric golds, but it is the
# WRONG instrument for uc4_formula and was scoring correct answers wrong at a
# rate of ~57%. Two independent reasons:
#
#   1. _gold_head() splits on "(", assuming the parenthetical is the gold's
#      working. In this suite the parentheses are usually REGULATION CITATIONS
#      -- "Regulation 21(1)", "Regulation 28A(1)" -- so the head keeps the whole
#      working and the split contributes the citation number as a required
#      quantity. Gold "Regulation 28A(1) ... not exceeding twelve months" became
#      "must contain 28"; the model answered "12 months" and was marked wrong.
#   2. Many golds are dates ("March 26, 2025") or yes/no with numeric
#      justification. A bag-of-numbers comparison cannot grade either.
#
# The golds are prose carrying a citation, the working, and the answer. Only a
# reader can pick out which quantity was actually asked for, so UC4 is graded by
# the judge on final-value equivalence -- matching the standing decision to
# grade the final value only.
JUDGE_FINAL_VALUE = """You grade numeric answers to questions about Indian financial regulation.

You are given a QUESTION, a REFERENCE answer, and a CANDIDATE answer.

The reference is written as prose. It usually contains a regulation citation, the
working, and the final answer all in one paragraph. Your job is to identify the single
quantity the QUESTION actually asked for, and decide whether the candidate reports the
same quantity.

Compare ONLY that final quantity. Specifically:

- Ignore regulation numbers entirely. "Regulation 28A(1)" is a citation, never an answer.
- Ignore the intermediate operands in the reference's working. The candidate is not
  required to restate them.
- A date answer matches if it is the same calendar date, however formatted.
- A number matches if it is the same value, however formatted: "₹38,000 crore",
  "38000 crore", and "Rs 38,000 crore" are the same. "12 months" and "twelve months"
  are the same.
- A percentage matches within 0.1 percentage points, since the references round
  inconsistently ("8.9%" and "8.888...%" are the same).
- For a yes/no question, the Yes/No must match. If the reference also states a
  quantity, that quantity must match too.
- The candidate may be much shorter than the reference. Never penalise brevity.

Mark INCORRECT when the candidate's final quantity differs from the reference's, when
it is missing, or when the yes/no polarity is wrong.

Reply with exactly one line: CORRECT or INCORRECT, then a semicolon and a brief reason."""


def grade_final_value(client: LunaClient, question: str, gold: str, prediction: str,
                      mode: str = "none") -> tuple[Verdict, object]:
    user = f"QUESTION:\n{question}\n\nREFERENCE:\n{gold}\n\nCANDIDATE:\n{prediction}"
    r = client.complete(JUDGE_FINAL_VALUE, user, mode=mode, max_tokens=256)
    if not r.ok:
        return Verdict(False, "final_value", f"judge failed: {r.error}"), r
    return Verdict(r.text.strip().upper().startswith("CORRECT"),
                   "final_value", r.text.strip()[:200]), r
