"""Token and cost ledger.

Every API call is appended to a JSONL ledger on disk so a run can be stopped,
inspected, and resumed without losing spend history. The ledger is the single
source of truth for "how much have we spent so far" — nothing is held only in
memory.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path

# USD per token, (input, output). Luna is the default; the others exist so that
# a weaker-model control run is not silently costed at Luna's rate.
PRICES = {
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-5-nano":   (0.05, 0.40),
    "gpt-5-mini":   (0.25, 2.00),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o-mini":  (0.15, 0.60),
}
PRICE_IN = 0.20 / 1_000_000
PRICE_OUT = 1.20 / 1_000_000


def prices_for(model: str) -> tuple[float, float]:
    """Per-token (in, out). Unknown models fall back to Luna's rate and the
    caller is expected to treat the resulting dollar figure as unverified."""
    p_in, p_out = PRICES.get(model, (0.20, 1.20))
    return p_in / 1_000_000, p_out / 1_000_000


@dataclass
class Call:
    ts: float
    suite: str
    item_id: str
    mode: str          # none | low | medium | high
    rep: int           # which repetition of this (item, mode)
    role: str          # "target" for Luna under test, "judge" for the grader
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int      # subset of completion, reported separately when available
    latency_s: float
    ok: bool
    error: str = ""

    @property
    def cost(self) -> float:
        # Reasoning tokens are billed at the output rate. Providers differ on
        # whether they are already included in completion_tokens; we assume they
        # ARE included (OpenAI's convention) and do not double-count.
        return self.prompt_tokens * PRICE_IN + self.completion_tokens * PRICE_OUT


class Ledger:
    def __init__(self, path: Path, cap_usd: float | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cap_usd = cap_usd
        self._lock = threading.Lock()
        self._calls: list[Call] = []
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        for line in self.path.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                d.pop("cost", None)
                self._calls.append(Call(**d))

    def record(self, call: Call) -> None:
        with self._lock:
            self._calls.append(call)
            with open(self.path, "a") as f:
                f.write(json.dumps({**asdict(call), "cost": round(call.cost, 8)}) + "\n")

    # --- queries ----------------------------------------------------------
    @property
    def spent(self) -> float:
        return sum(c.cost for c in self._calls)

    @property
    def remaining(self) -> float:
        return float("inf") if self.cap_usd is None else max(0.0, self.cap_usd - self.spent)

    def exhausted(self) -> bool:
        return self.cap_usd is not None and self.spent >= self.cap_usd

    def n_items_done(self, suite: str, mode: str) -> int:
        return len({c.item_id for c in self._calls
                    if c.suite == suite and c.mode == mode and c.role == "target" and c.ok})

    def done_keys(self) -> set[tuple[str, str, str, int]]:
        """(suite, item_id, mode, rep) already completed successfully."""
        return {(c.suite, c.item_id, c.mode, c.rep)
                for c in self._calls if c.role == "target" and c.ok}

    def observed_reasoning_tokens(self) -> dict[str, float]:
        """Mean reasoning tokens per mode — replaces the guesses in cost_model.py
        once a calibration batch has run."""
        out: dict[str, list[int]] = {}
        for c in self._calls:
            if c.role == "target" and c.ok:
                out.setdefault(c.mode, []).append(c.reasoning_tokens)
        return {m: sum(v) / len(v) for m, v in out.items() if v}

    def summary(self) -> str:
        by: dict[tuple[str, str], list[Call]] = {}
        for c in self._calls:
            by.setdefault((c.suite, c.mode), []).append(c)
        lines = [f"{'suite':22s} {'mode':8s} {'calls':>6s} {'items':>6s} "
                 f"{'in':>10s} {'out':>10s} {'think':>9s} {'$':>8s}"]
        lines.append("-" * 88)
        for (suite, mode), cs in sorted(by.items()):
            tgt = [c for c in cs if c.role == "target"]
            lines.append(
                f"{suite:22s} {mode:8s} {len(cs):6d} {len({c.item_id for c in tgt}):6d} "
                f"{sum(c.prompt_tokens for c in cs):10,d} "
                f"{sum(c.completion_tokens for c in cs):10,d} "
                f"{sum(c.reasoning_tokens for c in cs):9,d} "
                f"{sum(c.cost for c in cs):8.3f}")
        lines.append("-" * 88)
        cap = f" / cap ${self.cap_usd:.2f}" if self.cap_usd else ""
        lines.append(f"{'TOTAL':22s} {'':8s} {len(self._calls):6d} {'':6s} "
                     f"{sum(c.prompt_tokens for c in self._calls):10,d} "
                     f"{sum(c.completion_tokens for c in self._calls):10,d} "
                     f"{sum(c.reasoning_tokens for c in self._calls):9,d} "
                     f"{self.spent:8.3f}{cap}")
        obs = self.observed_reasoning_tokens()
        if obs:
            lines.append("")
            lines.append("observed mean reasoning tokens/item: " +
                         "  ".join(f"{m}={v:.0f}" for m, v in sorted(obs.items())))
        return "\n".join(lines)


def now() -> float:
    return time.time()
