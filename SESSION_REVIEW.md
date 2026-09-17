# Session review — Luna reasoning-mode eval

Written 2026-08-27 from the full session transcript (pre- and post-compaction),
`CLAUDE.md`, and the actual result files in `runs/`. Every number below was
recomputed from `runs/*/results.jsonl` and `runs/*/ledger.jsonl` unless it is
explicitly marked unverified.

---

## 1. The big picture — what is actually being attempted

You are about to put a model called `gpt-5.6-luna` ($0.20/M input, $1.20/M output)
into production behind four jobs:

1. **Calling tools without breaking.**
2. **Spotting relevant information.**
3. **Correctly applying rules and recalling them** during evaluation — rules that
   will be in the context, not retrieved.
4. **Correctly writing down formulae.** A deterministic `compute()` does the
   arithmetic downstream; what matters is that the model binds the right values
   into the right formula and emits them in an order `compute()` can consume.

The model exposes four reasoning settings — `none` / `low` / `medium` / `high` —
and thinking tokens are billed at the output rate. The question the work is meant
to answer is narrow and practical: **for each of the four jobs, what is the
cheapest reasoning setting that still works?** That is a per-use-case setting
decision, not a model bake-off. You explicitly ruled out comparing Luna against
other models as the goal, and you framed the eval shape yourself: *"it's like an
injection benchmark"* — context goes in the prompt, a question is asked, the
answer is compared to a gold. Not retrieval, not ranking.

Late in the session the frame widened, and this is the more important thing that
happened: you pointed out that in your real system a model's output does not end
at the answer. It gets summarised and handed to the next agent, which does more
work on it. So the setting you actually need is not "which effort answers this
item" but "which effort survives being chained." That reframe is currently
designed and unbuilt.

---

## 2. Achievements

**A working, resumable eval harness exists.** `harness/` has a client with
mode-aware token caps, a JSONL ledger written per call (so a run can be stopped
and resumed without losing spend history), an interleaved queue so early stopping
leaves balanced coverage, three graders, six suite loaders, and per-suite
rulepacks. It has `--model` / `--judge-model` / `--seed` / `--cap-usd` flags.
It has produced real measurements across three models.

**Datasets were triaged properly and the rejects were rejected for stated,
checkable reasons.** SARA (no statute in the data), IL-TUR (no question field,
CC BY-NC-SA), BNS/BNSS/BSA (ungrounded `consequence` type, lexical coverage
0.126), IndicLegalQA (GPT-4o-generated golds), several LegalBench tasks
(non-commercial or skewed), RuleArena NBA (too small), CA-Ben (never released).
That is a real piece of work and it is the reason the surviving suites are
usable at all.

**Four harness bugs were caught before they became conclusions.** Truncated
reasoning under a flat token cap; a RuleArena gold that included the airfare when
the prompt only asked for bag fees (scored 1/36 and *inverted the mode ranking*);
a numeric grader parsing the gold's parenthetical working; and then the same
grader again, this time splitting on `(` where the parenthetical was a regulation
citation (`"Under Regulation 21(1)... = March 26, 2025"` → grader demanded the
number 21). That last one had UC4 reading 42.5% when it was 95–100%. The
operating rule that came out of this — *a suite scoring uniformly zero is a
harness bug until proven otherwise* — has held four for four.

**The ceiling-not-floor finding, verified.** Reasoning effort is a budget the
model may decline to spend. On the same run at `high`, Luna spent a mean of
**43.2 thinking tokens** on uc4_formula items and **6,252.5** on RuleArena
airline items. Verified directly from `runs/smoke_all.json`. You pay for
thinking the model chose to do. The real cost of `high` is latency.

**The 138-item flat run (`runs/flat40/`).** 138 items across four suites
(uc2_spot 40, uc3_rules 40, uc3_contradiction 18, uc4_formula 40), all four
modes, one repetition, 552 target calls. Recomputed from disk, with UC4 taking
the corrected grader from `uc4_regraded.jsonl`:

| suite | n | none | low | medium | high |
|---|---|---|---|---|---|
| uc2_spot | 40 | 40/40 | 40/40 | 39/40 | 40/40 |
| uc3_rules | 40 | 37/40 | 37/40 | 37/40 | 37/40 |
| uc3_contradiction | 18 | 16/18 | 17/18 | 17/18 | 17/18 |
| uc4_formula | 40 | 38/40 | 40/40 | 39/40 | 38/40 |
| **total** | **138** | **94.9%** | **97.1%** | **95.7%** | **95.7%** |

Mean thinking tokens per call: none 0.0, low 18.2, medium 31.6, high 79.5.
Ledger cost $0.2321, plus roughly $0.025 for the UC4 re-grade.

**The negative controls — the single most valuable thing in the session.** Two
weaker models were run against the *identical* 138 items (verified: same item
IDs, zero extra, `random.Random(42)`), with the judge pinned to Luna so a weak
model could not grade itself:

| model | mode | accuracy (138 items) |
|---|---|---|
| gpt-5.6-luna | none | 94.9% |
| gpt-5.6-luna | low | 97.1% |
| gpt-5.6-luna | medium | 95.7% |
| gpt-5.6-luna | high | 95.7% |
| gpt-4.1-nano | (no reasoning) | 92.8% |
| gpt-5-nano | low | 92.8% |
| gpt-5-nano | medium | 93.5% |
| gpt-5-nano | high | 96.4% |

Total spread across three models and eight configurations: **4.3 percentage
points**. A cheap non-reasoning nano is statistically indistinguishable from
Luna (paired McNemar p = 0.549, per the transcript). `gpt-5-nano` at `high`
scores *above* Luna at `high`.

**The conclusion that follows, and it was drawn honestly:** uc2_spot,
uc3_rules, uc3_contradiction and uc4_formula **cannot discriminate anything.**
Not reasoning effort, not model tier three generations apart. They are
regression tests, not instruments. The earlier "ship at `none`" recommendation
was retracted as a statement about the suites' ceiling rather than about Luna.

**The reason was then measured directly, not guessed.** Median prompt across
those four suites is ~646 characters, about 120 words; range 325–1,197. The
RuleArena tax prompt is 19,538 characters. Golds appear verbatim in the passage
38% / 28% of the time for uc2/uc3. uc4_formula's hardest item is one
multiplication with both operands labelled. Your own read — *"these seem like
the datasets used for fine tuning models where answers are readily available
instead of having to be rederived"* — was correct, and four independent lines of
evidence agree: 4.3pp spread, 80 thinking tokens at `high`, 646-character
prompts, verbatim golds.

**A genuinely counterintuitive cost finding.** `gpt-5-nano` lists 4× cheaper on
input and 3× cheaper on output than Luna, and at `high` it costs **more** —
recomputed from `runs/ctl_5nano/ledger.jsonl` at real per-model rates,
$0.001291/call against Luna's $0.000383, about **3.4×** — because it burns a
mean of 3,005 thinking tokens where Luna spends 80. Latency 20.1s against 2.7s.
List price does not predict cost on a reasoning model; thinking volume does.

**The two suites that do separate**, from smoke runs (`runs/smoke_all.json`,
`runs/tax_smoke.json`):

| suite | n/mode | none | low | medium | high | high thinking | high latency |
|---|---|---|---|---|---|---|---|
| uc3_rulearena (airline) | 6 | 0/6 | 2/6 | 3/6 | 5/6 | 6,252 tok | 56.8s |
| uc3_tax | 10 | 3/10 | 5/10 | 8/10 | 8/10 | 6,962 tok | 96.3s |

Tax plateaus at `medium` — `high` costs about 2× the money and 2.6× the latency
for zero extra accuracy. Airline is still climbing at `high`.

**UC1 got unblocked.** BFCL was not merely un-run, it was never downloaded, and
`reasoning_effort` appears **nowhere** in its codebase — so out of the box it
cannot sweep the one variable this project exists to measure. A 40-line handler
(`harness/bfcl/luna_handler.py`) injects `effort` into the `reasoning` dict BFCL
already sends to the Responses API, keyed off the registry name so four
registered variants produce four result sets BFCL's own scorer compares natively.
`harness/bfcl/register.py` registers eight Luna entries. It lives in a separate
`.venv-bfcl` so it cannot disturb the `openai` version the working harness runs
on. Luna's four efforts were verified on the Responses API with tools attached.

**The Agno claim in your notebook photos was disproved.** `reasoning_effort="high"`
is supported across agno 1.8.4–3.0.1; the value historically missing was `none`.

---

## 3. Blockers and open problems

**Three of your four use cases currently have no working instrument.** This is
the headline blocker. UC2, UC3 and UC4 are measured on items whose hardest
instance is copying `11.9%` out of a sentence containing `11.9%`. Nothing you
conclude from them about reasoning effort is load-bearing. Until the items get
harder, those three questions are unanswered — not answered "none".

**The dilution ("haystack") rebuild is blocked on you.** The design is settled:
keep the question and gold identical, grow the surrounding *real* regulatory text,
find the length at which accuracy falls off — the knee. IndiaFinBench has
~165,197 characters (~41,300 tokens) across 406 snippets and 66 distinct
regulations on disk, enough for a 400× ladder with topically adjacent distractors
*(these corpus figures are from the transcript; I did not re-derive them)*. What
is missing is your number: you said you would measure how many tokens your
production ruleset occupies in one API call, so the ladder brackets it rather
than reaching an arbitrary ceiling. Nothing has been built pending that.

**The handover experiment is designed and unbuilt.** Not one line of code, not
one call. Design as agreed: hold the work constant, vary how many API boundaries
you cut across it; run each depth under *clean handover* (each step gets the gold
intermediate) and *live handover* (each step gets the model's own previous
output); the gap between them is per-hop drift. Estimated ~$11 for 20 items ×
5 depths × 4 modes, doubled for both conditions — **that is an extrapolation from
a measured $0.0066/call, not a measurement.**

**The source documents for UC2 do not exist on disk.** IndiaFinBench ships only
the snippet (median 337 chars, max 988). Native context cannot be restored; the
haystack has to be constructed from the corpus itself. That is a labelled
construction, not fabrication — every token is real regulatory text and the gold
is untouched — but it should be reported as constructed.

**Your quant → qual → quant chain cannot be graded honestly.** There is no
dataset where step 2 is a qualitative analysis with a labelled correct answer.
Building one means inventing the golds. The mechanical half *is* gradeable:
whether the numeric payload survives the boundary intact, whether it stays
parseable, whether the next step uses the value it was handed rather than
recomputing. The quality of the qualitative step is not.

**Issue spotting, in the strict sense, is still out of reach.** Dilution teaches
a model to find a *stated* fact in a large document. Recognising that a situation
raises a regulatory issue nobody named is a different task, and IndiaFinBench has
no items of that kind — every gold is stated or one arithmetic step away.

**`RA_tax_0_001` is unexplained.** All four modes converge on $2,911.68 against a
gold of $3,241.68, on the *easiest* complexity level. Systematic convergence on a
single wrong number is the signature of a bad gold, not a bad model. Given this
project's record, the gold should be checked first. Untouched.

---

## 4. To-dos

**Decided, not done:**

1. **Full BFCL AST sweep** — 996 items × 4 modes, quoted at ~$0.52 off a measured
   $0.00013/item at `high`. This is your first use case and it has no persisted
   results. It was offered and is awaiting your go-ahead.
2. **Build the dilution ladder** for UC2/UC3/UC4, with three different distractor
   recipes (other stated facts for UC2; other *rules*, especially superseded and
   near-identical ones, for UC3; other numbers of the same kind for UC4). Blocked
   on your ruleset token count.
3. **Build the handover ladder** on RuleArena tax.
4. **Check the `RA_tax_0_001` gold.**
5. **Full-scale runs of `uc3_tax` and `uc3_rulearena`** — the only two suites
   with any resolving power have still only ever been run at n=10 and n=6.

**Proposed, needing your call:**

6. **Add an `APPLIED: <provision>` line** to the UC3 and UC4 prompts, the same
   move you chose for `CHARGED_ORDER`. Costs a handful of output tokens, no extra
   run. Without it, when the knee appears you cannot tell whether the model
   *stopped finding the rule* or *started applying the wrong one* — different
   failures, different fixes. It also closes your rule-1-plus-rule-5 case on the
   selection axis. **Raised twice, never confirmed by you, not implemented.**
7. **Per-fact recall grading** instead of binary, for golds that assert multiple
   facts. This is the "gray area" you asked for. Evidence it matters: the only
   two items failing at all four modes are TMP_083 and TMP_084 (verified from
   disk), both completeness failures where the gold asserts three facts and Luna
   returned one of them *correctly*. Binary grading scores that identically to a
   hallucination.
8. **Faithfulness / sufficiency / precision metrics on the handover payload** —
   faithfulness (did the step pass on what it actually computed) and sufficiency
   (does the payload contain what step k+1 needs) are both deterministic and
   require no judge. Agreed in principle, needs building in from the start.
9. **Measure one BFCL multi-turn category** before committing to that tier; the
   AST cost does not extrapolate to it.

---

## 5. Missing points and risks

This is the section that matters. Everything below is either an unverified
assertion, a measurement resting on an untested assumption, scope of yours that
has quietly gone unaddressed, or a contradiction between what was decided and
what exists.

**5.1 `CLAUDE.md` labels an extrapolation as measured — in the section built to
prevent exactly that.** It says, under *Measured (real API calls, in `runs/`)*:
*"Full-run cost, 300 items × 3 reps × 4 modes: airline $14.48, tax $23.83.
Measured."* Those are not measured full runs. No such run exists in `runs/`.
They are the mean per-call cost from the 6-item and 10-item smoke runs multiplied
by 3,600 calls. I reproduced both to the cent: tax mean $/call = $0.00662 ×
3,600 = **$23.83**; airline mean $/call = $0.00402 × 3,600 = **$14.47**.
The state document's own measured/guessed firewall has a hole in it, and it is a
cost figure — the exact failure mode the document warns about twice.

**5.2 The `CLAUDE.md` suite table is stale and now contradicts the evidence.**
It still carries the n=6 smoke verdicts — *"uc2_spot saturated → none"*,
*"uc3_rules saturated → none"*, *"uc4_formula saturated → none"*, *"uc1 tools
not built"*. The session then ran 138 items, ran two controls, established that
those suites cannot discriminate at all, retracted the `none` recommendation, and
built the BFCL handler. None of that is in the file. If you compact again, or
hand this to anyone, the doc-of-record will hand them conclusions the work
already voided.

**5.3 Every mode comparison rests on a single repetition.** `runs/flat40/` has
`reps: [0]` — one shot per (item, mode). The argument that mode-to-mode
differences are noise leans on the *pattern* of failures (only 2 of 138 items
fail at all four modes; 10 flicker — both verified from disk). That is
reasonable, but the noise floor was never measured. No item was ever run twice at
the same mode with the same settings. A second rep on the 138 items costs roughly
what the first did (~$0.23) and would turn an inference into a measurement. The
runner already defaults to `--reps 5`; the run was made at 1.

**5.4 `budget.py` has a dead price table, and the control-run ledgers on disk are
wrong.** The module defines `PRICES` for five models and a `prices_for()` helper,
with the comment *"the others exist so that a weaker-model control run is not
silently costed at Luna's rate."* `prices_for()` is called **nowhere**.
`Call.cost` hardcodes `PRICE_IN`/`PRICE_OUT` at Luna's rates. So the control runs
are silently costed at Luna's rate — the precise thing the comment says must not
happen. As written on disk: `ctl_5nano` $0.9060, `ctl_41nano` $0.0662. At real
per-model prices: $0.3339 and $0.0399. Anyone who reads those ledgers later,
including a future session, gets numbers inflated 1.7× and 2.7×.

**5.5 The "$0.33 total across all three runs" figure does not reconcile.** Summing
the ledgers at correct per-model rates, with judge calls kept at Luna's rate
(the judge always ran on Luna): flat40 $0.2321 + ctl_41nano $0.0399 + ctl_5nano
$0.3339 = **$0.6059**, plus ~$0.025 for the UC4 re-grade, so about **$0.63**.
$0.33 is exactly the ctl_5nano subtotal — one run reported as three. Small money;
the pattern is not small. This is the fourth cost figure in this project that did
not survive being checked, and `CLAUDE.md` already warns twice about this exact
habit.

**5.6 Two other reported control numbers overstate the measurement.** Reported
`gpt-5-nano` thinking at `high`: 3,496 tokens. Recomputed over all 138 calls:
**3,004.8**. Reported $/call at `high`: $0.001559. Recomputed at $0.05/$0.40:
**$0.001291**. The "4.1× more expensive than Luna" claim is really about
**3.4×**. The finding survives — a weak reasoning model is more expensive than a
strong one on identical work — but the multiplier quoted is ~20% high. (The
thinking figure may have been read mid-run at 120/414 items; the cost figure I
cannot account for.)

**5.7 Luna is grading Luna, and the grader has never been validated.** Four of
six suites are scored by `grade_llm` / `grade_final_value` with the judge pinned
to `gpt-5.6-luna`. When UC4 swung from 42.5% to 95–100% on a grader change, the
audit of that swing was performed by the same model that produced the swing.
There is no human-labelled held-out sample, no second-judge agreement check, no
inter-rater number anywhere in this project. Given that grader bugs have caused
**four** wrong results here, the grader itself is now the least-verified component
in the stack, and it is the one every headline number passes through.

**5.8 Two files on disk disagree about UC4 and nothing marks which is right.**
`runs/flat40/results.jsonl` holds the old `grade_numeric` verdicts (17–18/40,
~42.5%). `runs/flat40/uc4_regraded.jsonl` holds the corrected `grade_final_value`
verdicts (38–40/40, 95–100%). Anyone reading the obvious file gets the wrong
answer. There is no README, no marker, no deletion.

**5.9 Nothing is under version control.** The project directory is not a git
repo. Four harness bugs have been fixed, the UC4 grader was swapped mid-project,
the runner was changed after `flat40` ran, and there is no way to tie any result
file to the code that produced it. For a project whose central lesson is "the
harness lied to me four times," that is the largest process risk here.

**5.10 The exclusions are unaudited and they push accuracy up.** `suites.py`
drops 18 IndiaFinBench items to `QUARANTINE` and relabels 19 as `NOT_NUMERIC` —
37 items, on the model's own judgment about which golds are wrong. Some
justifications are inline and look sound (`"NUM_010: 1 Apr + 120 days = 30 Jul,
gold says 29 Jul"`). None were checked by you. Every exclusion of a bad gold
raises measured accuracy, and measured accuracy at 95–100% is the number the
"these suites are saturated" conclusion rests on. The conclusion is almost
certainly still right — the controls carry it independently — but the exclusion
list has never been reviewed.

**5.11 The complexity gradient sized for the handover experiment does not match
the code.** The design leans on RuleArena tax shipping *"a genuine complexity
gradient (schedule count 0 through 4)"* and *"twenty items across the five
complexity levels."* `harness/suites.py` loads `uc3_tax(levels=(0, 1, 2))` — three
levels — and its own docstring says *"comp_2 has two to four"* schedules. Airline
is the same, `levels=(0, 1, 2)`. Either the loader needs widening or the
experiment is smaller than described. Nobody has reconciled these.

**5.12 The BFCL numbers exist only in the transcript.** 90% / 80% / 90% / 80% on
10 items, $0.00010–$0.00013/item, output tokens climbing 41 → 66 across the
ladder. I searched for BFCL result and score directories and **found none on
disk.** Treat all of it as unverified, including the token-monotonicity check
that was the actual point of the exercise (proving `effort` transmits rather than
being silently dropped). The `$0.52` for the full AST sweep extrapolates from
those unverified per-item figures. It is very likely right and very cheap either
way — but it should be re-measured with the output kept.

**5.13 Domain drift is acknowledged in `CLAUDE.md` and has never been acted on.**
Every suite is Indian financial regulation, US airline baggage, or US individual
income tax. Your production domain has not been named in this session. The note
says results transfer "by task shape, not subject" — that is an assumption, and
it is the assumption the entire project's external validity rests on. It has not
been tested and there is currently no plan to test it. Related: when the flat
suites turned out to be flat, the honest reading given was *"we have no evidence
either way"* about your real items — that caveat should travel with every
conclusion in this document.

**5.14 There is a live cost implication that was flagged once and then dropped.**
`gpt-4.1-nano` ($0.10/$0.40) is statistically indistinguishable from Luna
($0.20/$1.20) on 138 items — 3× cheaper on output. That was correctly caveated as
a statement about the suites, not about Luna. But if your production items
resemble these at all, it is real money, and there is currently no experiment
queued that would settle it. It is worth deciding whether you want one.

**5.15 The reframe you care about most is the least built.** Reading your own
messages in order, your interest migrated decisively — from "which reasoning mode
for these items" to handovers, compounding error, context pollution across agent
boundaries, and answer relevance of what gets passed forward. You said it
plainly: *"if it did that on flawed reasoning or just very little answer relevance
based on the reasoning, that becomes polluted context or low precision context for
the next step during the handover."* That question has a good design and zero
implementation, while the settled-and-void single-hop suites have three models'
worth of data. The centre of gravity of the evidence is not where the centre of
gravity of your interest is.

**5.16 A smaller one worth naming: `.env` has no `LUNA_*` variables.** The client
reads `LUNA_API_KEY`/`LUNA_BASE_URL` and falls back to `OPENAI_API_KEY`/
`OPENAI_BASE_URL`. Only the `OPENAI_*` pair exists (plus `HF_TOKEN`). It works
today entirely by fallback. If a `LUNA_*` variable is ever set to something stale,
it will silently take precedence.

---

## 6. State of play

| suite | items | status | what is known | resolving power |
|---|---|---|---|---|
| **uc1 tools (BFCL)** | 996 AST (+ live/multi-turn) | handler built, registered, 10-item pipeline check only | 90/80/90/80 at n=10; effort verified transmitting via token climb 41→66 — **all transcript-only, no files on disk** | unknown |
| **uc2_spot** | 190 (40 run) | measured, then invalidated | 100/100/97.5/100%; nano within 5pp; median prompt 591 chars, gold verbatim 38% | **none** |
| **uc3_rules** | 71 (40 run) | measured, then invalidated | 92.5% flat at all four modes; only 2 persistent failures, both recall-completeness | **none** |
| **uc3_contradiction** | 18 (all run) | measured, then invalidated | 88.9/94.4/94.4/94.4%; rebalanced 9 Yes / 9 No | **none**, and thin |
| **uc4_formula** | 69 (40 run) | measured after two grader fixes | 95/100/97.5/95%; raw `results.jsonl` still shows the wrong 42.5% | **none** |
| **uc3_rulearena (airline)** | 300 (6 run) | smoke only | 0/2/3/5 of 6; 6,252 thinking tok and 56.8s at `high`; still climbing | **yes**, no ceiling seen |
| **uc3_tax** | 300 (10 run) | smoke only | 3/5/8/8 of 10; plateaus at `medium`; `high` = 2× cost, 2.6× latency, zero gain; 19.5k-char prompts | **yes** — sharpest instrument in the project |
| **dilution / knee ladder** | — | designed, unbuilt | blocked on your production ruleset token count | — |
| **handover ladder** | — | designed, unbuilt | ~$11 estimate, extrapolated from $0.0066/call | — |

**Control models, same 138 items:** `gpt-4.1-nano` 92.8%; `gpt-5-nano`
92.8 / 93.5 / 96.4% at low/medium/high. Total spread across all eight
configurations: 4.3pp.

**Real spend to date, recomputed at correct per-model prices:** about **$0.63**
across `flat40`, `ctl_41nano`, `ctl_5nano` and the UC4 re-grade, plus roughly
$0.68 of earlier smoke runs reported pre-compaction (not independently
re-verified). Call it **under $1.50 total.** Four harness bugs were caught for
about $0.27 of that.
