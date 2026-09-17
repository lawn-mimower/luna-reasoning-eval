# Luna reasoning-effort evaluation

How much reasoning does a task actually need? This is the harness built to answer that
empirically for one model across four production use cases, rather than defaulting every
call to maximum effort and paying for it.

Four `reasoning_effort` modes (`none` / `low` / `medium` / `high`) are run across 11
suites, roughly 9,000 API calls, with a cost ledger attached to every call.

## The finding that mattered

Most suites **could not tell the modes apart.** Tool-calling accuracy moved less than a
point across all four settings; three other suites sat at their ceiling regardless. Only
two things separated cleanly — a multi-step handover chain, and a rule-application task
with a real tax ruleset. Everywhere else, `none` was as good as `high` and far cheaper.

A null result is the useful result here: it says where the effort budget is wasted.

## Read `AUDIT.md` first

`AUDIT.md` is an adversarial self-audit of this repo's own conclusions, written after the
fact and recomputing every number from the run artifacts rather than trusting the
summaries. It retracts a recommendation that had already shipped.

The headline defect: `parse_carry()` split on `;` while the prompt template joined keys
with `, `. Every two-key handover payload — 96 of 96 — was silently truncated. The
"sufficiency" finding built on top of that was an artifact of the separator, not model
behaviour. The audit also downgrades three claims from "measured" to "unsupported" after
McNemar tests put them inside noise, and corrects a cost ledger that was inflating
control runs by 1.7–2.7× because `Call.cost` hardcoded one model's rate.

Findings are classified as **(a) definitely wrong**, **(b) unsupported**, or **(c)
fragile**, with a column for whether each one changes a decision.

## Layout

```
harness/
  client.py      mode-aware API client
  runner.py      suite execution, parallel, resumable
  handover.py    multi-step chain where state passes between steps
  haystack.py    context-dilution ladder
  ladder.py      difficulty ladder construction
  judge.py       LLM-as-judge grading
  budget.py      per-call cost ledger
  suites.py      suite definitions
  bfcl/          Berkeley Function-Calling Leaderboard integration
  rulepacks/     prompt rulepacks per use case
cost_model.py    cost projection (see caveat)
plots.py         figures
make_pdf.py      report build
```

## Caveats worth keeping

- `cost_model.py`'s THINKING multipliers are **invented and unvalidated**. Its own
  docstring says so. Don't quote its point estimates.
- Several full-run cost totals in earlier write-ups were extrapolations from 40-item
  smoke runs, not measurements. The audit flags which is which.
- Outside the handover and tool-calling suites, most comparisons are single-rep and land
  inside their own confidence intervals.

## Running it

Needs an OpenAI-compatible endpoint:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
export LUNA_BASE_URL=...   # or OPENAI_BASE_URL
export LUNA_API_KEY=...    # or OPENAI_API_KEY
.venv/bin/python -m harness.runner --suite uc3_tax --mode medium
```

Run outputs, datasets and the model endpoint are not in this repo — only the harness and
the analysis. `datasets/MANIFEST.json` describes the corpora and where they come from.
