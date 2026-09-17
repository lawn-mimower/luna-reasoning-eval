"""Luna API client.

ASSUMPTION: gpt-5.6-luna is served over an OpenAI-compatible
POST /v1/chat/completions accepting a flat `reasoning_effort` parameter.
If the gateway wants a nested shape instead (some do, e.g.
`extra_body={"thinking": {...}}`), change _effort_kwargs() only — nothing
else in the harness touches the wire format.

Verify with one curl before a full run:
  curl $LUNA_BASE_URL/chat/completions -H "Authorization: Bearer $LUNA_API_KEY" \
    -H 'content-type: application/json' \
    -d '{"model":"gpt-5.6-luna","reasoning_effort":"high",
         "messages":[{"role":"user","content":"hi"}]}'
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

MODES = ("none", "low", "medium", "high")


def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


@dataclass
class Response:
    text: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    latency_s: float
    ok: bool
    error: str = ""
    truncated: bool = False


class LunaClient:
    def __init__(self, root: Path, model: str = "gpt-5.6-luna"):
        env = {**load_env(root / ".env"), **os.environ}
        self.model = model
        self.client = OpenAI(
            api_key=env.get("LUNA_API_KEY") or env.get("OPENAI_API_KEY", ""),
            base_url=env.get("LUNA_BASE_URL") or env.get("OPENAI_BASE_URL") or None,
            timeout=900.0,
            max_retries=4,
        )

    # Only the reasoning families accept reasoning_effort. A gpt-4.x model
    # returns 400 on it, so a floor-check control has to omit the parameter
    # rather than pass mode="none".
    @staticmethod
    def supports_effort(model: str) -> bool:
        return model.startswith(("gpt-5", "o1", "o3", "o4"))

    def _effort_kwargs(self, mode: str) -> dict:
        if mode not in MODES:
            raise ValueError(f"unknown reasoning mode {mode!r}; expected one of {MODES}")
        if not self.supports_effort(self.model):
            return {}
        return {"reasoning_effort": mode}

    # Reasoning tokens are drawn from the same completion budget as the visible
    # answer, so the cap must leave room for BOTH. A cap that truncates thinking
    # silently penalises the higher modes -- the exact effect under measurement.
    MAX_TOKENS = {"none": 4_000, "low": 8_000, "medium": 16_000, "high": 32_000}

    def complete(self, system: str, user: str, mode: str,
                 max_tokens: int | None = None) -> Response:
        max_tokens = max_tokens or self.MAX_TOKENS[mode]
        t0 = time.time()
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                max_completion_tokens=max_tokens,
                **self._effort_kwargs(mode),
            )
        except Exception as e:                                  # noqa: BLE001
            return Response("", 0, 0, 0, time.time() - t0, False,
                            f"{type(e).__name__}: {e}")

        u = r.usage
        details = getattr(u, "completion_tokens_details", None)
        return Response(
            text=(r.choices[0].message.content or "").strip(),
            truncated=(r.choices[0].finish_reason == "length"),
            prompt_tokens=u.prompt_tokens,
            completion_tokens=u.completion_tokens,
            reasoning_tokens=getattr(details, "reasoning_tokens", 0) or 0,
            latency_s=time.time() - t0,
            ok=True,
        )
