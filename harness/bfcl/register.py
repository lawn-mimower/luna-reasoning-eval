"""Register the four Luna effort variants into BFCL's model registry.

Appends to the installed package inside .venv-bfcl (isolated, so this cannot
affect the eval harness). Idempotent -- safe to re-run after a reinstall.
"""
import sys
from pathlib import Path

VENV = Path(__file__).resolve().parents[2] / ".venv-bfcl"
CFG = next(VENV.glob("lib/python*/site-packages/bfcl_eval/constants/model_config.py"))
MARK = "# --- luna effort variants ---"

BLOCK = '''

# --- luna effort variants ---
# Added by harness/bfcl/register.py. One registry entry per reasoning effort so
# that BFCL writes four separate result sets its own scorer can compare.
import sys as _sys
_sys.path.insert(0, "{proj}")
from harness.bfcl.luna_handler import LunaEffortHandler as _LunaEffortHandler

for _eff in ("none", "low", "medium", "high"):
    for _fc in (True, False):
        _name = f"gpt-5.6-luna-{{_eff}}" + ("-FC" if _fc else "")
        MODEL_CONFIG_MAPPING[_name] = ModelConfig(
            model_name="gpt-5.6-luna",
            display_name=f"GPT-5.6-Luna effort={{_eff}}" + (" (FC)" if _fc else " (Prompt)"),
            url="https://platform.openai.com/docs/models",
            org="OpenAI",
            license="Proprietary",
            model_handler=_LunaEffortHandler,
            input_price=0.20,
            output_price=1.20,
            is_fc_model=_fc,
            underscore_to_dot=True,
        )
'''

def main() -> None:
    text = CFG.read_text()
    if MARK in text:
        print("already registered")
        return
    proj = str(Path(__file__).resolve().parents[2])
    CFG.write_text(text + BLOCK.format(proj=proj))
    print(f"registered 8 luna entries in {CFG}")

if __name__ == "__main__":
    main()
