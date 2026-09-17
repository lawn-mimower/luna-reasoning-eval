"""BFCL handler for gpt-5.6-luna with a selectable reasoning effort.

BFCL has no reasoning-effort flag -- `reasoning_effort` appears nowhere in the
package, so out of the box every run happens at whatever default the endpoint
picks, and the variable this whole project measures is not controllable.

It does, however, already send a `reasoning` dict to the Responses API for any
model whose name contains "gpt-5". So the entire fix is to inject `effort` into
that dict. We key the effort off the REGISTRY name rather than adding a CLI flag:
BFCL writes results into a directory named after the registry entry, so four
registered variants give four separate result sets that its own scorer can
compare, with no changes to the runner or the scorer.

Verified against the live endpoint: all four efforts are accepted by
responses.create() with tools attached, and Luna emits a correct function_call
at each one.
"""
from bfcl_eval.model_handler.api_inference.openai_response import OpenAIResponsesHandler

EFFORTS = ("none", "low", "medium", "high")


class LunaEffortHandler(OpenAIResponsesHandler):
    def _effort(self) -> str:
        # registry names look like "gpt-5.6-luna-medium-FC"
        parts = self.registry_name.split("-")
        for e in EFFORTS:
            if e in parts:
                return e
        raise ValueError(
            f"registry name {self.registry_name!r} carries no reasoning effort; "
            f"expected one of {EFFORTS} as a hyphen-separated component"
        )

    def generate_with_backoff(self, **kwargs):
        # Overriding here rather than in _query_FC covers the prompting path too,
        # and leaves BFCL's retry/backoff behaviour untouched.
        if "reasoning" in kwargs:
            kwargs["reasoning"] = {**kwargs["reasoning"], "effort": self._effort()}
        return super().generate_with_backoff(**kwargs)
