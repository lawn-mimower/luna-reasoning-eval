"""Dilution: put the real passage back into a body of real regulatory text.

WHY. The flat suites are trivial -- median prompt 646 chars, and the gold is
often a verbatim span of a passage short enough to contain exactly one candidate
answer. Measured consequence: a frontier model and a nano model score within
4.3pp of each other across eight model/mode configurations (McNemar p=0.549).
There is nothing to spot, select, or bind, so nothing discriminates.

CONSTRUCTION, and its honest label. Every token here is real SEBI/RBI text drawn
from the same corpus as the item. The question is unchanged, the gold is
unchanged, the true passage is still present. The only thing that changes is how
much genuine text surrounds it. That is a construction and is labelled as one --
the haystack is assembled, not natively occurring -- but it is the opposite of
fabricating data: it removes a simplification the dataset's authors applied.

DISTRACTOR CHOICE. Distractors are drawn from the SAME regulation first, falling
back to the wider corpus only when that runs out. Random distractors would be
far easier and would flatter the result: 60 snippets of unrelated statute is a
keyword search, 60 snippets of the same Mutual Funds regulation is not.

POSITION is randomised per item under a fixed seed and recorded, so that
position effects can be separated from length effects afterwards. Answer-at-the
-start and answer-at-the-end are known to behave differently in long context.

AMBIGUITY. A distractor that also answers the question would silently break the
item. Every candidate is checked against the gold's key quantities and spans and
rejected on overlap; items that cannot be made unambiguous are dropped and
reported rather than quietly kept.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

import tiktoken

ENC = tiktoken.get_encoding("o200k_base")
DATA = Path(__file__).parent.parent / "datasets"


def ntok(s: str) -> int:
    return len(ENC.encode(s))


@dataclass
class Diluted:
    user: str
    n_tokens: int
    n_distractors: int
    needle_index: int      # 0-based position of the true passage among all passages
    needle_frac: float     # 0.0 = first, 1.0 = last


def _key_terms(gold: str) -> set[str]:
    """Quantities and distinctive spans that would make a distractor ambiguous."""
    g = gold.lower()
    terms = set(re.findall(r"\d[\d,]*\.?\d*\s*(?:per\s*cent|percent|%|crore|lakh)?", g))
    terms |= {w for w in re.findall(r"regulation\s+\d+[a-z]*(?:\(\d+\))?", g)}
    return {t.strip() for t in terms if len(t.strip()) > 2}


def _pool(exclude_id: str) -> list[dict]:
    rows = json.loads((DATA / "indiafinbench/indiafinbench_qa.json").read_text())
    out = []
    for r in rows:
        if r["id"] == exclude_id:
            continue
        ctx = r.get("context") or ""
        if not ctx.strip():
            ctx = (r.get("context_a", "") + "\n" + r.get("context_b", "")).strip()
        if ctx:
            out.append({"ctx": ctx,
                        "reg": r.get("regulation") or r.get("regulation_a") or "",
                        "doc": r.get("document") or r.get("document_a") or "source"})
    return out


def dilute(row: dict, question: str, gold: str, target_tokens: int,
           seed: int, position: float | None = None) -> Diluted | None:
    """Rebuild one item's prompt with `target_tokens` of real surrounding text.

    BUG #9, fixed here. This used to do `random.Random(seed)` with the SAME seed on
    every item, so the "randomised" needle position was a deterministic function of
    the list sizes -- needle_frac came out spanning only 0.33-1.0, mean 0.77, with
    ZERO items in the first fifth of the context. Late in the prompt is the easiest
    place for a model to find something, so the flat 0-30k retrieval result was
    measured under the most favourable position and could not speak to any other.
    The seed is now mixed with the item id.

    `position` forces the needle to a specific fraction (0.0 = first block,
    1.0 = last) so position can be varied deliberately instead of hoped for.
    """
    rng = random.Random(f"{seed}:{row['id']}")
    true_reg = row.get("regulation") or row.get("document") or "source"
    true_ctx = row.get("context") or ""
    if not true_ctx.strip():
        return None
    true_block = f"PASSAGE ({true_reg}):\n{true_ctx}"

    banned = _key_terms(gold)
    pool = _pool(row["id"])
    # same regulation first -- topically adjacent distractors are the hard case
    same = [p for p in pool if p["reg"] and p["reg"] == true_reg]
    other = [p for p in pool if not (p["reg"] and p["reg"] == true_reg)]
    rng.shuffle(same); rng.shuffle(other)

    budget = target_tokens - ntok(true_block) - ntok(question) - 40
    picked: list[str] = []
    used = 0
    for p in same + other:
        if used >= budget:
            break
        low = p["ctx"].lower()
        if any(b in low for b in banned):        # would create a second answer
            continue
        blk = f"PASSAGE ({p['reg'] or p['doc']}):\n{p['ctx']}"
        t = ntok(blk)
        if used + t > budget:
            continue
        picked.append(blk); used += t

    # place the true passage -- forced when position is given, else random
    if position is None:
        idx = rng.randint(0, len(picked))
    else:
        idx = int(round(min(max(position, 0.0), 1.0) * len(picked)))
    blocks = picked[:idx] + [true_block] + picked[idx:]
    user = "\n\n".join(blocks) + f"\n\nQUESTION: {question}"
    return Diluted(user=user, n_tokens=ntok(user), n_distractors=len(picked),
                   needle_index=idx,
                   needle_frac=idx / max(1, len(picked)))
