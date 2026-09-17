# VIZ_GUIDELINES.md

Visualization spec for the Luna reasoning-mode results presentation.
Written 2026-08-27. **This is a build spec, not the deck.** No charts exist yet.

**Audience:** senior engineering staff. They will judge the *method*, not the bar heights.
Every section must justify a choice before it shows a number.

**Every number in this file was recomputed from disk on 2026-08-27.** Provenance table in
§12. Where a number does not exist, it is marked `TBD — chart spec only`. Do not fill a TBD
with an estimate.

---

## 0. How to use this document

1. Build order is §1 (spine) → §2 (design system) → §3 (honesty encodings) → §4–7 (per use
   case) → §8–10 (cross-cutting) → §12 (provenance appendix, ships in the deck).
2. Every chart below has a fixed ID (`UC1-C2`, `NC-1`, …). Use those IDs as the HTML
   `id` attribute on the chart's `<figure>` so review comments can address them.
3. Every chart spec states **the one sentence the viewer should conclude**. That sentence
   goes into the deck as the chart's subtitle, verbatim. If a chart cannot support its
   sentence, cut the chart — do not soften the sentence.
4. **Do not re-derive numbers by eye from a previous chart.** Recompute from the cited file.
   This project has produced five confidently wrong numbers by not doing that (§3.4).

---

## 1. Deck spine

Fixed order. Each use case repeats the same four beats, so engineers learn the rhythm once.

| # | Slide | Content |
|---|---|---|
| 0 | Title | What was measured, over what period, total spend (~$1.50, §12) |
| 1 | The question | Per use case, cheapest `reasoning_effort` that still works. Not a model bake-off. |
| 2 | Evidence tiers legend | §3.1. Show this **before** any chart. |
| 3–6 | **UC1 tool calling** | why-BFCL / verbatim items / what it tests / results (§4) |
| 7–10 | **UC2 spotting** | (§5) |
| 11–15 | **UC3 rules** | (§6) — two instruments, opposite verdicts |
| 16–19 | **UC4 formulae** | (§7) |
| 20–22 | **Negative controls** | (§8) — the methodological centrepiece |
| 23–25 | **Cost / latency / accuracy frontier** | (§9) |
| 26–27 | **Knee plots** | (§10) — dilution + handover |
| 28 | **Five harness bugs** | (§3.4). Not a footnote. A slide. |
| 29 | **Retractions** | (§3.5) |
| 30 | What we do not know | domain drift, judge unvalidated, exclusions unreviewed |
| 31 | Provenance appendix | (§12) |

Per use case, the four beats in order, always:
**B1** why this benchmark (+ what was rejected, why) · **B2** verbatim item, so they can
judge difficulty themselves · **B3** what it tests and what it does *not* · **B4** results.

---

## 2. Design system

### 2.1 Output constraints

- Self-contained HTML artifact, published via the Artifact tool. Single file.
- **No external chart libraries will load** (strict CSP). All charts are hand-authored
  **inline SVG**. Canvas only if a chart exceeds ~2,000 marks — none here does.
- Google Fonts are the one permitted external host. Give every face a real fallback.
- Theme-aware: define the full light palette on bare `:root`, redefine only the changed
  tokens under `@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]) }`
  **and** under `:root[data-theme="dark"]`. Never define a colour only inside a media block.
- SVG must inherit theme via `currentColor` or `var(--token)` on `fill`/`stroke`. No
  hardcoded hex inside `<svg>`.
- Wide charts sit inside `overflow-x:auto`; the page body never scrolls horizontally.
- Favicon: `📉` — keep stable across every redeploy.
- `<title>`: `Luna Effort Eval` (a name, not a summary).

### 2.2 Palette — brand-neutral, fixed

**Reasoning effort is ordinal** (`none` < `low` < `medium` < `high`). It gets a *sequential*
single-hue ramp, never four categorical colours. This is load-bearing: categorical colours
imply the modes are unordered alternatives, which is exactly the wrong reading.

```css
:root{
  /* surfaces & ink */
  --bg:#F7F9FB; --surface:#FFFFFF; --ink:#111827; --ink-muted:#5B6672;
  --rule:#E3E8EF; --grid:#EDF1F6;

  /* EFFORT — sequential, 4 stops, use in this order always */
  --e-none:#C3D8EC; --e-low:#8DB4D8; --e-med:#4C84BB; --e-high:#1D4E79;

  /* MODEL — categorical, 3 series, deuteranopia-safe */
  --m-luna:#1F6FB2;      /* gpt-5.6-luna   */
  --m-5nano:#C2410C;     /* gpt-5-nano     */
  --m-41nano:#6B7280;    /* gpt-4.1-nano   */

  /* SEMANTIC */
  --ok:#15803D; --fail:#B91C1C; --warn:#B45309;
  --est:#94A3B8;        /* estimated — always with hatch */
  --retracted:#9CA3AF;  /* retracted — always at 40% opacity */
  --band:#1F6FB2;       /* "indistinguishable band" fill, use at 10% alpha */
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#0B0F14; --surface:#10151B; --ink:#E8EDF4; --ink-muted:#9AA7B4;
  --rule:#243040; --grid:#1A2430;
  --e-none:#2C4056; --e-low:#456E97; --e-med:#79A5D1; --e-high:#B9D4F0;
  --m-luna:#5EA3DC; --m-5nano:#F08A4B; --m-41nano:#98A2AE;
  --ok:#4ADE80; --fail:#F87171; --warn:#FBBF24;
  --est:#64748B; --retracted:#5B6672;
}}
:root[data-theme="dark"]{ /* repeat the dark block verbatim */ }
```

**Rules.**
- Effort ramp always renders `none`→`high` left-to-right / bottom-to-top. Never re-order,
  never sort by value.
- In dark theme the effort ramp *inverts* (dark→light) so `high` stays the most salient.
- Never use `--ok`/`--fail` as the only channel. Pair with a shape (● pass / ✕ fail) or a
  label — some of this audience is colour-blind and all of it will see this projected.
- `--m-41nano` is deliberately grey: gpt-4.1-nano is the boring baseline and should look
  like one right up until §8 reveals it is not distinguishable from Luna.

### 2.3 Type hierarchy

Stack: `"Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif`
Mono (verbatim items, IDs, JSON): `"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace`

| Role | Size / line-height | Weight | Colour |
|---|---|---|---|
| Deck title | 40 / 1.1 | 700 | `--ink` |
| Section head | 28 / 1.2 | 650 | `--ink` |
| Slide head | 21 / 1.25 | 600 | `--ink` |
| **Chart title** | 17 / 1.3 | 600 | `--ink` |
| **Chart conclusion (subtitle)** | 14 / 1.45 | 450 | `--ink-muted` |
| Body | 15 / 1.6 | 400 | `--ink` |
| Axis label | 12 / 1.2 | 500 | `--ink-muted` |
| Tick label | 11 / 1 | 400 `tabular-nums` | `--ink-muted` |
| Verbatim item block | 13 / 1.55 mono | 400 | `--ink` |
| Item ID chip | 11 / 1 mono | 500 | `--ink-muted` |
| Provenance / footnote | 11.5 / 1.5 | 400 | `--ink-muted` |

All numerals in charts and tables: `font-variant-numeric: tabular-nums`.

### 2.4 Chart conventions (apply to every chart, no exceptions)

1. **Accuracy y-axis starts at 0.** If a zoom is genuinely needed (only `UC1-C2` qualifies),
   draw an explicit axis break glyph *and* state the range in the conclusion line.
2. **Every accuracy point carries a Wilson 95% CI.** Formula and computed values in §3.3.
   No CI = the chart does not ship.
3. **Every chart carries an `n =` chip** in its top-right, coloured by evidence tier (§3.1).
4. **No sorting by value.** Effort in ramp order; suites in deck order; models in fixed
   order (luna, 5-nano, 4.1-nano). Sorting descending manufactures a ranking out of noise.
5. Gridlines `--grid`, 1px, horizontal only. No chart borders, no drop shadows, no 3D,
   no gradients on data marks.
6. Direct-label series at the line end. Legends only where >3 series and labels collide.
7. Mark minimum 3px; touch/hover targets are not needed (static deck).
8. Every `<figure>` gets `role="img"` and an `aria-label` restating the conclusion line.

---

## 3. Honesty rules — non-negotiable

This project produced **five** harness bugs that yielded confidently wrong numbers. The deck
must not launder that history. These encodings are how it doesn't.

### 3.1 Evidence tiers — the legend slide (slide 2)

| Tier | Meaning | Where it applies | Visual encoding |
|---|---|---|---|
| **T1** | Measured, powered (n ≥ 1000/cell) | BFCL only | solid fill, 100% opacity, `n` chip in `--ink` |
| **T2** | Measured, single rep (n = 138) | flat40, both controls | solid fill + **mandatory CI bars**, `n` chip in `--ink-muted` |
| **T3** | Smoke (n ≤ 10/cell) | uc3_tax, uc3_rulearena, all `smoke_all.json` | **outline only, no solid fill**, CI bars mandatory, `n` chip in `--warn`, connecting lines dashed `4 2` |
| **T4** | Estimated / extrapolated | full-run costs, handover budget | 45° hatch `<pattern>` over `--est`, label suffixed `(est.)`, multiplier stated inline |
| **T5** | Retracted | see §3.5 | 40% opacity, strikethrough label, caption `retracted <date> — <reason>` |
| **T6** | Invalid, do not plot | `runs/ladder10/`, raw `flat40/results.jsonl` UC4 rows, on-disk control costs | **absent from all charts**; named in §12 with the reason |

Put the legend on its own slide *before* any chart, and repeat a compact 3-item version in
the footer of every results slide.

### 3.2 The n-chip

Top-right of every chart, 11px mono, in a 1px `--rule` pill:

```
n = 1000 / mode        ← T1, ink
n = 138 / mode         ← T2, ink-muted
n = 10 / mode  ⚠       ← T3, warn
```

A 6-item smoke must never occupy the same visual weight as a 1000-item result. T3 charts
additionally render at **60% of the panel width** of a T1 chart on the same slide. Size is
the fastest-read uncertainty channel and it costs nothing.

### 3.3 Uncertainty — computed Wilson 95% intervals

Wilson score interval, z = 1.96. Precomputed for every headline figure — **use these, do not
re-derive**:

| Figure | k/n | acc | 95% CI | width |
|---|---|---|---|---|
| BFCL none | 817/1000 | 81.7% | [79.2, 84.0] | 4.8pp |
| BFCL low | 806/1000 | 80.6% | [78.0, 82.9] | 4.9pp |
| BFCL medium | 809/1000 | 80.9% | [78.3, 83.2] | 4.9pp |
| BFCL high | 812/1000 | 81.2% | [78.7, 83.5] | 4.8pp |
| Luna none (flat40) | 131/138 | 94.9% | [89.9, 97.5] | 7.6pp |
| Luna low | 134/138 | 97.1% | [92.8, 98.9] | 6.1pp |
| Luna medium | 132/138 | 95.7% | [90.8, 98.0] | 7.2pp |
| Luna high | 132/138 | 95.7% | [90.8, 98.0] | 7.2pp |
| gpt-4.1-nano (no reasoning) | 128/138 | 92.8% | [87.2, 96.0] | 8.8pp |
| gpt-5-nano low | 128/138 | 92.8% | [87.2, 96.0] | 8.8pp |
| gpt-5-nano medium | 129/138 | 93.5% | [88.1, 96.5] | 8.5pp |
| gpt-5-nano high | 133/138 | 96.4% | [91.8, 98.4] | 6.6pp |
| smoke 6/6 | 6/6 | 100% | [61.0, 100.0] | **39.0pp** |
| tax 8/10 | 8/10 | 80.0% | [49.0, 94.3] | **45.3pp** |

The last two rows are the argument for T3 existing. A 6/6 smoke has a 39-point interval.
**Consider putting the `smoke 6/6 → [61, 100]` bar on the legend slide itself** as the
worked example of why tiers exist.

### 3.4 The five harness bugs — slide 28

Horizontal timeline, one lane, five markers. Each marker: bug name, the wrong number it
produced, the right number, the cost to find it. Marker fill `--fail`, resolved state ringed
`--ok`.

| # | Bug | Wrong reading | Correct reading | Source |
|---|---|---|---|---|
| 1 | `max_completion_tokens` truncated reasoning under a flat cap | scored-wrong instead of excluded | caps now mode-aware; truncated responses excluded | `CLAUDE.md` "Working rule" |
| 2 | RuleArena gold included airfare; prompt asked bag fees only | 1/36 — **and it inverted the mode ranking** | prompt now asks for total cost | `CLAUDE.md`; `runs/smoke_all.json` system prompt |
| 3 | numeric grader parsed the gold's parenthetical working | uc4 0/6 at every mode | 5/6 | `CLAUDE.md` |
| 4 | `_gold_head()` splits on `(`, but the paren was a **regulation citation** | **uc4 42.5%** | **95–100%** | `harness/judge.py:142-145`; exemplar item `NUM_111` |
| 5 | ladder run rate-limited; loss scaled with rung size | a clean-looking knee | an artifact of 429s | `harness/ladder.py` `TokenBucket` docstring; `runs/ladder10/ledger.jsonl` |

Conclusion line: **"Four of these five produced a confident number that survived until
someone checked. That is why every chart in this deck carries its evidence tier."**

Bug 5 gets its own chart (`UC2-C4`) because it is the most instructive: the artifact was
*shaped like the finding we were looking for*.

### 3.5 Retractions — slide 29

Two-column "was / is", `--retracted` at 40% opacity on the left, live colour on the right.

| Was | Is | Why |
|---|---|---|
| "Ship at `none`" | **Withdrawn.** Statement about the suites' ceiling, not about Luna. | Suites cannot discriminate (§8) |
| UC4 = 42.5% | **95–100%** | Grader bug 4 |
| Total spend "$0.33 across all three runs" | **~$0.63** (flat40 $0.2321 + ctl_41nano $0.0399 + ctl_5nano $0.3339 + ~$0.025 regrade) | $0.33 was the ctl_5nano subtotal reported as the total |
| gpt-5-nano `high` = 3,496 thinking tok, 4.1× Luna's cost | **3,004.8 tok, 3.4×** | Recomputed over all 138 calls at real per-model prices |
| "BFCL results are transcript-only, nothing on disk" (`SESSION_REVIEW.md` §5.12) | **Superseded — 4 result sets and 4 score sets now exist on disk**, n=1000/mode | See §4 |

Also correct on this slide: `CLAUDE.md` labels the airline **$14.48** and tax **$23.83**
full-run costs as *Measured*. **They are not.** They are smoke-run mean $/call × 3,600 calls.
Render them **T4 hatched** everywhere they appear, with the multiplier shown.
And: `cost_model.py`'s `THINKING` dict is invented and unvalidated — **never quote its point
estimates in any chart or caption.**

### 3.6 What may not be plotted

- `runs/ladder10/*` accuracy — biased sample, 285/637 target calls lost to 429s (§5).
- Raw UC4 rows in `runs/flat40/results.jsonl` — superseded by `uc4_regraded.jsonl`.
- On-disk `cost` fields in `ctl_41nano` / `ctl_5nano` ledgers — `budget.py` hardcodes Luna's
  rates (`PRICE_IN`/`PRICE_OUT`); `prices_for()` is defined but called nowhere. Use the
  corrected figures in §12.
- BFCL's own `Non-Live Overall Acc` (68.38%) and `Overall Acc` (6.84%) — see §4.4.

---

## 4. UC1 — Tool calling (BFCL v4 AST). **T1. The only powered result in the project.**

### 4.1 B1 — why BFCL, what was rejected

Slat, not a chart. Three points:
- BFCL v4 non-live AST is the standard tool-calling instrument and its scorer compares
  registered model variants natively.
- **`reasoning_effort` appears nowhere in the BFCL codebase.** Out of the box it cannot
  sweep the one variable this project exists to measure. A ~40-line custom handler
  (`harness/bfcl/luna_handler.py`) injects `effort` into the `reasoning` dict BFCL already
  sends to the Responses API, keyed off the registry name, producing four result sets.
- Scope cut, stated: phase 3 (live web) skipped — needs SerpAPI + live web, non-reproducible.
  Live and multi-turn categories not run.

### 4.2 B2 — verbatim items (quote all four, mono blocks)

All from `.venv-bfcl/lib/python3.12/site-packages/bfcl_eval/data/BFCL_v4_<cat>.json`.

| ID | file | why it's on the slide |
|---|---|---|
| `simple_python_0` | `BFCL_v4_simple_python.json` | the easy end. *"Find the area of a triangle with a base of 10 units and height of 5 units."* One function, two required int params. Show this first so nobody assumes 81% means the set is hard. |
| `simple_python_13` | `BFCL_v4_simple_python.json` | **fails at all four modes.** *"Calculate the area under the curve y=x^2 from x=1 to x=3."* Schema declares `interval` as `array of float`; Luna emits `[1, 3]`. Error `type_error:nested`. This is a **type-fidelity** failure, not a reasoning failure — thinking harder cannot fix it. |
| `parallel_3` | `BFCL_v4_parallel.json` | **fails at all four modes.** *"Get the protein sequence of human HbA1c, normal hemoglobin, and rat hemoglobin and their 3D models"*. Gold accepts `'human HbA1c'` or `'HbA1c'`; Luna emits `'human HbA1c (glycated adult hemoglobin A; HbA1c, alpha2 beta2)'` — and **elaborates it differently at every effort setting**. Over-specification, and more effort makes it worse. Quote all four variants side by side; it lands hard. |
| `parallel_multiple_3` | `BFCL_v4_parallel_multiple.json` | `ast_decoder:decoder_failed` at low/medium/high, `wrong_count` at none. Shows the same item failing for *different reasons* by mode. |

Render each as: question (mono), the relevant slice of the function schema (mono, dimmed),
Luna's emitted call, and the checker's error string. Four cards, one grid.

### 4.3 B3 — what it tests / does not test

**Tests:** single-turn function selection, argument binding, type fidelity, parallel call
enumeration against an AST checker. Deterministic, no LLM judge anywhere in this suite.
**Does not test:** multi-turn state, tool *results* feeding back, live APIs, irrelevance
detection, latency under load, or anything resembling the user's production tool schemas.
Say this out loud — it is the section's main caveat.

### 4.4 B4 — charts

---

**`UC1-C1` — Accuracy by category × effort**
- Type: grouped vertical bars. 4 category groups × 4 effort bars.
- x: category, in fixed order with n: `simple_python (400)`, `multiple (200)`,
  `parallel (200)`, `parallel_multiple (200)`
- y: accuracy %, **0–100**
- Encoding: effort sequential ramp `--e-none`→`--e-high`. Wilson CI whiskers on every bar.
- Data (`correct_count` / `total_count`, from `score/gpt-5.6-luna-<mode>-FC/non_live/*_score.json` line 1):

| category | none | low | medium | high |
|---|---|---|---|---|
| simple_python (400) | 324 (81.0%) | 328 (82.0%) | 331 (82.75%) | 338 (84.5%) |
| multiple (200) | 171 (85.5%) | 167 (83.5%) | 169 (84.5%) | 168 (84.0%) |
| parallel (200) | 168 (84.0%) | 170 (85.0%) | 171 (85.5%) | 166 (83.0%) |
| parallel_multiple (200) | 154 (77.0%) | 141 (70.5%) | 138 (69.0%) | 140 (70.0%) |

- **Conclusion sentence:** "Task category moves tool-calling accuracy by up to 15 points;
  reasoning effort moves it by about one."
- **Misleading if:** the four category bars are averaged unweighted (gives 81.9%, wrong —
  simple_python is 40% of the set). Always weight by n. Also: `parallel_multiple` is the
  only category where `none` is the *best* setting (77.0% vs 69–70.5%) — do not bury it,
  annotate it, it is a genuine finding and it argues against a blanket "more effort is safer".

---

**`UC1-C2` — Overall AST accuracy vs effort (the null result)**
- Type: line + point, with CI band.
- x: effort, ordinal, `none`→`high`. y: accuracy, **zoomed 70–90 with an explicit axis-break
  glyph**, and the range restated in the conclusion line. This is the one permitted zoom.
- Series: one line, `--m-luna`. Shaded Wilson CI ribbon per point.
- Data (weighted, n=1000/mode): none **81.7%** (817), low **80.6%** (806),
  medium **80.9%** (809), high **81.2%** (812). Total spread **1.1pp**.
- **Conclusion sentence:** "Across 1,000 items per mode, all four reasoning settings land
  within 1.1 points and their confidence intervals overlap completely — on tool calling,
  effort buys nothing."
- **Misleading if:** the zoom is not flagged. At 70–90 the 1.1pp spread looks like a trend
  with a dip at `low`. Draw the CI ribbon *first*, under the line, so overlap is the dominant
  visual, and put a horizontal reference line at the grand mean 81.1%.
- **Do not plot** BFCL's own `Non-Live Overall Acc` (68.38 / 66.58 / 66.65 / 66.29%) or
  `Overall Acc` (6.84 / 6.66 / 6.66 / 6.63%) from `score/data_non_live.csv` and
  `score/data_overall.csv`. Those divide by categories we never ran (Java/JS simple,
  irrelevance detection, live, multi-turn, web search, memory) and score them as zero. They
  are aggregation artifacts of a partial run, not results. If anyone in the room has seen the
  BFCL leaderboard they will ask — have this ready as a spoken answer, not a slide.

---

**`UC1-C3` — Failure-set decomposition** *(one of the three most important charts, §13)*
- Type: single horizontal stacked bar, 1000 units wide, three segments. Or a 40×25 waffle
  if you want it to bite harder.
- Segments: **744 pass at all four modes** (`--ok`, 30% alpha) · **129 flicker** (pass at
  some modes, fail at others) (`--warn`) · **127 fail at all four modes** (`--fail`).
- Below it, the persistent-failure breakdown by category: simple_python 43, parallel_multiple
  42, parallel 24, multiple 18.
- **Conclusion sentence:** "Effort does not convert failures into passes — it reshuffles the
  129 items that were already unstable, while the same 127 fail at every setting."
- **Misleading if:** presented as if 129 flickering items means 129 items *improve* with
  effort. They do not: the totals are flat (817/806/809/812). Add the mode-by-mode counts as
  a caption so the reader sees flicker is churn, not gain.

---

**`UC1-C4` — Error-type composition by effort**
- Type: 4 horizontal stacked bars (one per effort), normalised to total failures
  (183/194/191/188).
- Segments, in fixed order: `parallel_..._cannot_find_match`, `value_error:string`,
  `ast_decoder:decoder_failed`, `parallel_..._wrong_count`, `value_error:others`, other.
- Data:

| error type | none | low | medium | high |
|---|---|---|---|---|
| parallel cannot_find_match | 54 | 53 | 52 | 58 |
| value_error:string | 50 | 46 | 48 | 48 |
| ast_decoder:decoder_failed | 23 | 32 | 25 | 23 |
| parallel wrong_count | 20 | 26 | 33 | 27 |
| value_error:others | 15 | 19 | 14 | 15 |
| value_error:list/tuple | 6 | 5 | 6 | 5 |
| type_error:nested | 4 | 4 | 4 | 4 |

- **Conclusion sentence:** "The failure *mix* is near-constant across effort — these are
  schema-fidelity and over-specification errors, and they are not the kind of error more
  thinking fixes."
- **Misleading if:** the segments are re-ordered per bar (kills comparison) or the bars are
  drawn on raw counts without noting the denominators differ. Normalise, and print the
  denominator on each bar.

---

## 5. UC2 — Spotting information (IndiaFinBench extractive). **T2 → invalidated.**

### 5.1 B1 — why, and the rejections

This is the slide where the dataset triage earns its keep. Show the reject list as a table
with the *checkable* reason for each — it is what makes the surviving choice credible:
SARA (statute absent, only fact patterns; no licence) · IL-TUR (no question field in any of
8 tasks; CC BY-NC-SA) · BNS/BNSS/BSA (`consequence` type ungrounded, lexical coverage 0.126;
`exceptions` 90% "No"; 13% of questions say "this section" with no identifier) ·
IndicLegalQA (no context field; golds GPT-4o-generated) · LegalBench `diversity_1/2` 76/24
skewed, `learned_hands_*` non-commercial, `canada_tax_court_outcomes` 92% span extraction ·
RuleArena NBA (216 items) · CA-Ben (never released, email-gated).

### 5.2 B2 — verbatim items

From `datasets/indiafinbench/indiafinbench_qa.json`.

| ID | why |
|---|---|
| `REG_003` | The archetype. Context 664 chars. Q: *"…what is the minimum percentage of post-issue capital that promoters must hold following a public issue?"* Gold: *"At least twenty per cent."* — **verbatim in the passage.** Show the passage with the gold span highlighted in `--ok`. This single card is the argument for §5.4. |
| `REG_001` | Same shape, 725 chars, gold *"At least fifteen crore rupees"*, also verbatim. Two in a row makes the point without a chart. |
| `REG_015` | **Labelled `difficulty: hard`** — and it is a 473-char passage whose gold is still a single lift: *"One hundred and twenty calendar days from the expiry of the sixty-day period, or after the first hearing, whichever is earlier."* Use this to pre-empt "but you only showed the easy ones." |

### 5.3 B3 — what it tests / does not test

**Tests:** locating one stated fact in a short supplied passage.
**Does not test:** retrieval, ranking, or issue spotting in the strict sense — *recognising
that a situation raises a regulatory issue nobody named*. Every gold here is stated or one
arithmetic step away. Say this explicitly; it is the honest limit of the whole UC2 line.

### 5.4 B4 — charts

---

**`UC2-C1` — Prompt size, our suites vs production-shaped**
- Type: horizontal bars, **log x**, `n=` on each.
- x: median prompt tokens (from ledgers, target calls at `none`)
- Data: `uc2_spot` **889** · `uc3_contradiction` **937** · `uc3_rules` **940** ·
  `uc4_formula` **1,081** · `uc3_rulearena` **4,096** · `uc3_tax` **6,427** (range 6,083–11,158)
- Character-level, if you prefer the plainer unit: median *user* prompt across the four flat
  suites **643 chars** (range 325–1,197) vs RuleArena airline **21,405 chars**
  (20,966 system + 439 user).
- **Conclusion sentence:** "The four suites our first conclusions came from have prompts
  roughly seven times smaller than the two suites that actually separate the modes."
- **Misleading if:** chars and tokens are mixed on one axis. Pick one unit per chart. Also
  annotate that `uc2_spot`'s ~889 prompt tokens include the ~600-token shared rulepack —
  the *passage* is only ~150 tokens.

---

**`UC2-C2` — Gold-appears-verbatim rate**
- Type: 4 stacked bars (verbatim / not), one per suite.
- Data (case-insensitive substring of the gold in the user prompt, full pools):
  `uc2_spot` 63/190 (**33%**) · `uc3_contradiction` 7/18 (**39%**) · `uc3_rules` 12/71 (**17%**)
  · `uc4_formula` 0/69 (**0%**)
- **Conclusion sentence:** "A third of the spotting items can be answered by copying a span
  — there is nothing to spot."
- **Misleading if:** read as "33% is the ceiling on how easy it is." It is a *lower bound* —
  it only counts exact substring matches and misses near-verbatim paraphrase. Say "at least
  33%" in the caption. Also note the `uc4_formula` 0% is expected by construction (the gold
  is a computed value) and is **not** evidence that UC4 is hard.

---

**`UC2-C3` — Dilution ladder knee.** **TBD — chart spec only.**
Blocked on: (a) the throttled rerun (`harness/ladder.py` now has a `TokenBucket`; the run on
disk predates it), (b) the user's production ruleset token count, which sets the top rung.
- Type: line + point, **log x**.
- x: context tokens per prompt, rungs `~150 (baseline) / 2,500 / 5,000 / 10,000 / +TBD`
- y: accuracy %, 0–100
- Series: 4 lines, effort ramp. Wilson CI ribbon per point. Points at each rung, **straight
  segments only — never a smoothed spline through 4–5 rungs.**
- Annotation: vertical dashed rule at the user's production ruleset size, labelled
  "your ruleset" — this is the whole point of the chart.
- **Conclusion sentence (when data exists):** "Accuracy holds to N tokens and falls after;
  the modes break at [the same / different] length, so the fix is [retrieval / effort]."
- Mark the knee **only** if a segment's slope change exceeds the CI width. Otherwise state
  "no knee observed within the tested range."
- **Companion panel `UC2-C3b`:** accuracy vs `needle_frac` (recorded per item by
  `harness/haystack.py`), bucketed 0–0.2 … 0.8–1.0, so position effects are visibly separated
  from length effects. Without it a knee could be a lost-in-the-middle artifact.
- Label the haystack as **constructed**: every token is real SEBI/RBI text from the same
  corpus, distractors drawn from the *same regulation* first, question and gold untouched,
  ambiguous distractors rejected against the gold's key terms. Say "constructed, not native"
  on the slide. The source documents for UC2 do not exist on disk — IndiaFinBench ships only
  the snippet — so native long context cannot be restored.

---

**`UC2-C4` — "The knee that was a rate limiter"** *(one of the three most important charts, §13)*
- Type: dual-axis is banned; use two stacked panels sharing the x axis.
- x (both): rung — `0`, `2,500`, `5,000`, `10,000`
- Top panel y: **% of target calls that survived**, bars. Data from `runs/ladder10/ledger.jsonl`:
  **159/161 = 99%** · **90/160 = 56%** · **59/160 = 37%** · **44/156 = 28%**.
  All 285 failures are `RateLimitError: 429`.
- Bottom panel y: the accuracy curve that biased sample *would* have produced — render it
  entirely in `--retracted` at 40% opacity with a red ✕ watermark and the caption
  **"DO NOT USE."**
- **Conclusion sentence:** "The first dilution ladder lost 285 of 637 calls to rate limits,
  and the loss scaled with prompt size — which is exactly the shape of the knee we were
  looking for."
- Follow-on line: the fix is a **token**-metered bucket, not a request-count cap, because the
  cost of a call varies ~20× across the ladder (`harness/ladder.py`, `TokenBucket` docstring).
- **Misleading if:** the bad accuracy curve is drawn at full fidelity anywhere. It must look
  disabled. Consider showing only the survival panel and describing the curve in words.

---

## 6. UC3 — Applying rules. **Two instruments, opposite verdicts. Lead with that.**

Structure this section as a split: **6A IndiaFinBench temporal + contradiction (T2, no
resolving power)** and **6B RuleArena tax + airline (T3, the sharpest instruments we have)**.
The contrast *is* the narrative beat.

### 6.1 B2 — verbatim items

| ID | file | why |
|---|---|---|
| `TMP_083`, `TMP_084` | `datasets/indiafinbench/indiafinbench_qa.json` | **The only two items in flat40 that fail at all four modes.** Both are **completeness** failures: the gold asserts three facts (e.g. TMP_083: 49% threshold, effective 05-05-2021, *plus* the simultaneous IGP rename) and Luna returned one of them correctly. Binary grading scores that identically to a hallucination. This is the case for per-fact recall grading — put both golds up in full. |
| `CON_001` | same | **A flicker item where `none` is arguably right and the gold is arguably wrong.** Passage A says 3 years, Passage B says 18 months; gold = "Yes, they differ". Luna at `none` answered *"No"* — reasoning that B is the 2018 Regulations as amended in 2021 and therefore supersedes A. Show the model's actual text (`runs/flat40/results.jsonl`, `CON_001`/`none`). It is the most honest slide in the deck about what "accuracy" means here. |
| `RA_air_0_000` | `runs/smoke_all.json` | The full RuleArena worked example. 20,966-char system prompt of real AA baggage policy; 439-char passenger. Show the **tail of Luna's answer** with the `BAG n: base/oversize/overweight/charged` lines and the `CHARGED_ORDER: 5, 4, 2, 3, 1` line — that ordered output is what the downstream `compute()` consumes, and it is why the bag-ordering ambiguity was handled by prompt ("assign allowances to minimise cost") rather than by dropping the 74/300 affected items. |

### 6.2 B3 — what it tests / does not test

**6A tests:** applying a stated effective date / period to reach a conclusion.
**6B tests:** selecting among ~40 interacting published rules, applying them in the right
order, and emitting a machine-consumable ordered result. This is the closest thing in the
project to the production shape.
**Neither tests:** retrieving a rule that is not in the context. All rules are in-prompt, by
design — that matches the stated production setup.

### 6.3 B4 — charts

---

**`UC3-C1` — IndiaFinBench temporal, flat across modes**
- Type: bars + CI, 4 effort bars. Data (`runs/flat40/`): `uc3_rules` **37/40 at all four
  modes**; `uc3_contradiction` 16/17/17/17 of 18.
- **Conclusion sentence:** "Identical at every setting — and it is the same three items
  failing each time."
- **Misleading if:** the y-axis is zoomed. Keep 0–100 here; the flatness is the message and
  a zoom would invent texture.

---

**`UC3-C2` — RuleArena separates**
- Type: line + point, T3 styling (**outline marks, dashed connectors, `n=` chip in `--warn`**),
  CI whiskers that will be enormous and should be.
- x: effort. y: accuracy 0–100. Two series: airline `--m-luna`, tax `--m-luna` dashed —
  or better, two small-multiple panels side by side, to avoid implying they share a scale of
  difficulty.
- Data:

| suite | n/mode | none | low | medium | high |
|---|---|---|---|---|---|
| uc3_rulearena (airline) | 6 | 0/6 (0%) | 2/6 (33%) | 3/6 (50%) | 5/6 (83%) |
| uc3_tax | 10 | 3/10 (30%) | 5/10 (50%) | 8/10 (80%) | 8/10 (80%) |

- **Conclusion sentence:** "These are the only two suites where effort changes the answer —
  tax plateaus at `medium`, airline is still climbing at `high`."
- **Misleading if:** these are shown at the same visual weight as `UC1-C2`. n=6 and n=10.
  Tax 8/10 has a 95% CI of [49.0, 94.3] — a 45-point interval. **Draw it.** The honest
  reading is "separates, direction established, magnitude unknown."
- Also annotate: airline's `none` = 0/6 comes from the run made *after* harness bug 2 was
  fixed (the gold/prompt scope mismatch that previously scored 1/36 and inverted the ranking).
  Say so on the slide — someone will ask whether a 0 is another bug, and by our own working
  rule ("a suite scoring uniformly zero is a harness bug until proven otherwise") they should.

---

**`UC3-C3` — Tax by complexity level.** T3, borderline unplottable — n = 4/4/2 per level.
If shown at all: small multiples, level 0 / 1 / 2, effort on x. Data:
L0 3/3/3/3 of 4 · L1 0/2/4/4 of 4 · L2 0/0/1/1 of 2.
- **Conclusion sentence:** "The separation is concentrated at complexity level 1 — at level 0
  every mode already passes."
- **Misleading if:** presented as a gradient claim. **Prefer to cut this chart** and state the
  L1 observation in text until the full 300-item run exists. Note also that
  `harness/suites.py` loads `levels=(0,1,2)` — three levels — while the handover design
  assumes a 0–4 gradient. Reconcile before claiming a gradient anywhere.

---

**`UC3-C4` — `RA_tax_0_001`: the open anomaly**
- Type: a small annotated number strip, not a chart. Gold **$3,241.68**. Predictions:
  `none` **$2,955.68**, `low`/`medium`/`high` all **$2,911.68**.
- **Conclusion sentence:** "Three of four modes converge on the same wrong number on the
  easiest complexity level — that is the signature of a bad gold, and it has not been checked."
- Correction to carry: `CLAUDE.md` says all four converge on $2,911.68. `none` gives
  $2,955.68 (`runs/tax_smoke.json`). Fix it in the deck and in `CLAUDE.md`.

---

## 7. UC4 — Formulae + substitution. **The grader is the story.**

### 7.1 B1 — why, and the stated blind spot

**UC4 grades the final value only.** No formula/binding annotation. Accepted blind spot,
stated on the slide: right number via wrong formula, and compensating errors, both pass. The
model still emits formula + substitutions, so the transcripts support a structural pass later
without re-running anything. Say this *before* showing 95–100%.

### 7.2 B2 — verbatim items

| ID | why |
|---|---|
| `NUM_111` | **The exhibit for harness bug 4.** Gold: *"Under Regulation 21(1), the investment adviser must redress the grievance not later than 21 calendar days… March 5, 2025 + 21 calendar days = March 26, 2025."* `_gold_head()` (`harness/judge.py:70`) splits the gold on `(` assuming the parenthetical is working — here it is a **regulation citation**, so the grader demanded the number **21** and marked correct answers wrong. Show the gold, the one-line `split("(")`, and the verdict flip. |
| `TMP_044` | A clean, genuinely representative item: buy-back completed 15 Jun 2025, one-year bar, gold 15 Jun 2026. One date-arithmetic step, both operands labelled. Shows the suite's real difficulty honestly. |
| `TMP_030` | Gold: *"Approximately 8 years and 10 months elapsed…"* — a gold no numeric grader can parse at all. Justifies why `grade_final_value` uses a judge here, and hands the audience the judge-validation caveat (§7.4). |
| `NUM_010` | **A quarantined item.** Context gives a 120-day gap; 1 Apr + 120 days = 30 Jul; the gold says 29 Jul. Show it as the worked example of the exclusion policy, then show `UC4-C2`. |

### 7.3 B3 — what it tests / does not test

**Tests:** binding the right stated values into the right operation and producing the right
final value.
**Does not test:** whether the formula was right (final-value grading, by decision), whether
the emitted substitutions are in an order `compute()` can consume, or arithmetic at any real
depth — the hardest item in the pool is a single operation with both operands labelled.

### 7.4 B4 — charts

---

**`UC4-C1` — The grader retraction** *(one of the three most important charts, §13)*
- Type: paired/slope bars. Same 40 items, same 4 modes, same model responses — **only the
  grader changed.**
- Left group `--retracted` 40% opacity, strikethrough label "grade_numeric (buggy)":
  none 17/40 (42.5%) · low 18/40 (45%) · medium 17/40 (42.5%) · high 18/40 (45%)
- Right group solid `--m-luna`, "grade_final_value (corrected)":
  none 38/40 (95%) · low 40/40 (100%) · medium 39/40 (97.5%) · high 38/40 (95%)
- Connect each mode's pair with a thin slope line so the +52.5pp jump is one gesture.
- **Conclusion sentence:** "A one-line bug in how the grader parsed the gold moved this use
  case's headline by 52 points. The model's answers never changed."
- **Misleading if:** framed as an improvement. It is not a result, it is a **correction**.
  Title it "Grader correction", never "UC4 improved". Also disclose that both files are still
  on disk with nothing marking which is right: `runs/flat40/results.jsonl` holds the wrong
  verdicts, `runs/flat40/uc4_regraded.jsonl` the right ones.

---

**`UC4-C2` — Exclusion waterfall**
- Type: waterfall / funnel, 5 steps.
- `406 IndiaFinBench rows` → −18 `QUARANTINE` → −19 `NOT_NUMERIC` (mislabelled table lookups)
  → **69 in the UC4 pool** → **40 run in flat40**.
- **Conclusion sentence:** "Every UC4 number here is computed on 40 of 406 rows after 37
  exclusions we made ourselves, none of which has been reviewed by anyone outside this work."
- **Misleading if:** omitted. Every exclusion of a bad gold *raises* measured accuracy, and
  measured accuracy at 95–100% is exactly what the "saturated" conclusion rests on. Showing
  the funnel is what makes the 95% credible rather than suspicious. List all 18 quarantine
  reasons in the appendix (`harness/suites.py:18-46` has them inline).

---

**`UC4-C3` — Accuracy across modes.** Bars + CI, 0–100. 38/40/39/38 of 40.
- **Conclusion sentence:** "Flat within noise at every setting — and with a 6-point
  confidence interval on 40 items, that is all this suite can tell us."

**Judge caveat, on the UC4 slide (not the appendix):** four of six suites are graded by
`grade_llm` / `grade_final_value` with the judge pinned to `gpt-5.6-luna` — **Luna grading
Luna**. There is no human-labelled held-out sample, no second-judge agreement check, no
inter-rater number anywhere in this project. The 42.5%→95% audit was performed by the same
model that produced the swing. Given that grader bugs caused four of five known wrong
results, the grader is the least-verified component in the stack and every headline number
passes through it.

---

## 8. Cross-cutting: the negative-control story. **The most important methodological result.**

Give it three slides. The claim is *"this benchmark cannot tell these apart"* — and the
hardest part of the visual design is showing that **honestly**, without accidentally drawing
a ranking.

**The banned chart:** bars sorted descending by accuracy. It manufactures a leaderboard out
of an 4.3-point band and it is the single most likely thing a builder will reach for.

---

**`NC-1` — Eight configurations, one indistinguishable band** *(one of the three most
important charts, §13)*
- Type: **horizontal dot plot with CI whiskers.** One row per configuration, **fixed order,
  never sorted**: Luna none/low/medium/high, then gpt-5-nano low/medium/high, then
  gpt-4.1-nano.
- x: accuracy %, **0–100** (do not zoom — the point is that all eight sit in a narrow band,
  and a zoom destroys that).
- Dot colour = model (`--m-luna` / `--m-5nano` / `--m-41nano`). Whiskers = Wilson 95% (§3.3).
- **Behind the dots:** a `--band` fill at 10% alpha spanning **92.8% → 97.1%**, labelled
  **"4.3pp — total spread across 3 models, 3 generations, 8 configurations."**
- Data, all on the **identical 138 items** (verified: same item IDs, zero extra,
  `random.Random(42)`), judge pinned to Luna so a weak model cannot grade itself:

| model | mode | k/138 | acc |
|---|---|---|---|
| gpt-5.6-luna | none | 131 | 94.9% |
| gpt-5.6-luna | low | 134 | 97.1% |
| gpt-5.6-luna | medium | 132 | 95.7% |
| gpt-5.6-luna | high | 132 | 95.7% |
| gpt-5-nano | low | 128 | 92.8% |
| gpt-5-nano | medium | 129 | 93.5% |
| gpt-5-nano | high | 133 | **96.4%** |
| gpt-4.1-nano | (none) | 128 | 92.8% |

- **Conclusion sentence:** "Three models three generations apart, eight configurations, all
  within 4.3 points with overlapping intervals — and `gpt-5-nano` at `high` scores above Luna
  at `high`. These four suites cannot discriminate anything."
- **Misleading if:** sorted; zoomed; or if the whiskers are omitted, which would make the
  4.3pp band look like a real ordering. Also: annotate the gpt-5-nano `high` = 96.4% row
  explicitly. Burying the row where the cheap model wins is the exact dishonesty this
  section exists to avoid.

---

**`NC-2` — McNemar discordance panel**
- Type: 2×2 matrix + a discordant-pairs strip. Not a bar chart.
- Primary pair: **Luna `none` vs gpt-4.1-nano**, paired on 138 items.
  Concordant 127 · Luna-only-correct **b = 7** · nano-only-correct **c = 4** ·
  **exact two-sided p = 0.549** (recomputed; matches the reported figure).
- Draw the 127 concordant items as a dense grey field, the 11 discordant as individual marks.
- **Conclusion sentence:** "127 of 138 items agree. The entire gap between a frontier model
  and a 3-generation-old nano is eleven items split seven to four — p = 0.549."
- Secondary rows (small, same panel, so nobody thinks 0.549 was cherry-picked). All
  recomputed, exact binomial two-sided:

| comparison | b | c | p |
|---|---|---|---|
| Luna none vs gpt-4.1-nano | 7 | 4 | 0.549 |
| Luna low vs gpt-4.1-nano | 8 | 2 | 0.109 |
| Luna medium vs gpt-4.1-nano | 5 | 1 | 0.219 |
| Luna high vs gpt-4.1-nano | 7 | 3 | 0.344 |
| Luna low vs gpt-5-nano low | 9 | 3 | 0.146 |
| Luna medium vs gpt-5-nano medium | 4 | 1 | 0.375 |
| Luna high vs gpt-5-nano high | 2 | 3 | 1.000 |
| Luna none vs Luna low | 1 | 4 | 0.375 |

- **Misleading if:** a p-value is presented as proof of equivalence. It is not — it is a
  failure to detect a difference at n=138. Caption: **"Not evidence they are the same.
  Evidence this instrument cannot tell."** The last row matters too: Luna `none` vs Luna `low`
  is p = 0.375, so the suite cannot separate Luna from *itself* across settings.
- **State the power limitation:** every comparison rests on a **single repetition**
  (`runs/flat40/` has `reps:[0]`). No item was ever run twice at the same mode. The noise
  floor was never measured. A second rep costs ~$0.23. Put that on the slide as a to-do.

---

**`NC-3` — Why the suites can't discriminate: four independent lines**
- Type: four small stat tiles in a row, no chart chrome.
  `4.3pp` spread across 8 configs · `79.5` mean thinking tokens at `high` on flat40 ·
  `643 chars` median prompt · `≥33%` of uc2 golds verbatim in the passage.
- **Conclusion sentence:** "Four independent measurements agree: there is nothing in these
  items to spot, select, or bind."

---

## 9. Cost / latency / accuracy — show a frontier, not a leaderboard

**Framing beat, stated before any chart: reasoning effort is a *ceiling, not a floor.* You
are billed only for thinking the model chose to do.** At `high` on the same run, Luna spent
a mean of **43.2** thinking tokens on `uc4_formula` items and **6,252.5** on RuleArena
airline items — a **145×** range at one setting. The real cost of `high` is **latency**
(96.3s vs 15.5s on tax).

---

**`CLA-1` — Thinking actually spent, by suite, at each effort**
- Type: grouped bars or dot-strip, **log y**.
- x: suite. y: mean thinking tokens. Series: effort ramp.
- Data at `high` (`runs/smoke_all.json`, `runs/tax_smoke.json`):
  uc2_spot **42.7** · uc4_formula **43.2** · uc3_rules **51.8** · uc3_contradiction **232.3**
  · uc3_rulearena **6,252.5** · uc3_tax **6,962.2**.
  At `none`: 0 everywhere. On flat40 (138 items): none 0.0 / low 18.2 / medium 31.6 / high 79.5.
- **Conclusion sentence:** "`high` is a budget, not an instruction — on an easy item Luna
  spends 43 thinking tokens, on a hard one 6,252, at the identical setting."
- **Misleading if:** on a linear axis (the small suites vanish) or if `none` = 0 is drawn as a
  log-scale bar (it can't be — render `none` as an explicit "0" label at the axis).

---

**`CLA-2` — The frontier** *(the chart to lead the section with)*
- Type: scatter, one point per (suite, mode), points within a suite connected in effort order
  by a thin `--ink-muted` path.
- x: mean latency, seconds, **log**. y: accuracy %, 0–100. **Point area ∝ $/item.**
- Draw the Pareto frontier as a stepped line; render **dominated** points hollow with a
  `--ink-muted` "dominated" label.
- Data (T3, per-item cost recomputed at Luna's $0.20/$1.20):

| suite | mode | acc | latency | $/item |
|---|---|---|---|---|
| uc3_tax | none | 3/10 | 15.5s | $0.003582 |
| uc3_tax | low | 5/10 | 25.5s | $0.004670 |
| uc3_tax | **medium** | **8/10** | **37.4s** | **$0.006004** |
| uc3_tax | high | 8/10 | 96.3s | $0.012227 |
| uc3_rulearena | none | 0/6 | 2.8s | $0.001084 |
| uc3_rulearena | low | 2/6 | 13.7s | $0.002443 |
| uc3_rulearena | medium | 3/6 | 22.8s | $0.003774 |
| uc3_rulearena | high | 5/6 | 56.8s | $0.008791 |

- **Conclusion sentence:** "On tax, `medium` is on the frontier and `high` is strictly
  dominated — identical 8/10 for 2.0× the money and 2.6× the latency; on airline nothing is
  dominated yet, because accuracy is still climbing at `high`."
- **Misleading if:** the two suites are read as a single frontier — they are different tasks
  and different difficulty. Two panels, or clear per-suite paths. And: at n=6/n=10 "8/10 =
  8/10" is not proof of a true plateau; the CI is [49.0, 94.3]. Caption it as *"dominated on
  the evidence we have"*, not *"dominated"*.
- Repeat the same scatter for the flat40 suites as a muted inset — all four modes pile into
  one blob at ~95%, 2s, which is the visual form of "no frontier, no signal."

---

**`CLA-3` — List price does not predict cost**
- Type: paired bars, 2 groups × 3 models.
- Left group: **list price** ($/M output): gpt-4.1-nano $0.40 · gpt-5-nano $0.40 ·
  gpt-5.6-luna $1.20.
- Right group: **realised $/call at `high`** on the identical 138 items:
  Luna **$0.000383** · gpt-5-nano **$0.001291** (**3.4×** Luna) · gpt-4.1-nano $0.000144 (`none`).
  Mean latency: Luna **2.71s**, gpt-5-nano **20.13s**.
  Driver: thinking tokens — Luna **79.5**, gpt-5-nano **3,004.8**.
- **Conclusion sentence:** "gpt-5-nano lists 3× cheaper on output and costs 3.4× more per
  call, because it burns 3,005 thinking tokens where Luna spends 80 — on a reasoning model,
  thinking volume sets the bill, not list price."
- **Misleading if:** the on-disk ledger costs are used. `budget.py` hardcodes Luna's rates
  for every model (`prices_for()` is defined and never called), so the ledgers say
  ctl_5nano **$0.9060** and ctl_41nano **$0.0662**. The correct figures at real per-model
  prices are **$0.3339** and **$0.0399** — inflated 2.7× and 1.7×. Use the corrected ones and
  footnote the discrepancy.
- Carry the live implication rather than hiding it: **gpt-4.1-nano ($0.10/$0.40) is
  statistically indistinguishable from Luna ($0.20/$1.20) on these 138 items and is 3× cheaper
  on output.** Correctly caveated as a statement about the suites, not about Luna — but if
  production items resemble these at all, it is real money and no experiment is queued that
  would settle it.

---

**`CLA-4` — Full-run cost projections. T4 — HATCHED, mandatory.**
- Airline **$14.48**, tax **$23.83** for 300 items × 3 reps × 4 modes.
- These are **not measured**, despite `CLAUDE.md` filing them under "Measured". They are
  smoke-run mean $/call × 3,600: tax $0.00662 × 3,600 = $23.83; airline $0.00402 × 3,600 =
  $14.47. Render hatched, suffix "(est.)", and **print the multiplier on the bar**.
- Show measured spend beside them, solid, for scale: flat40 **$0.2321**, ctl_41nano
  **$0.0399**, ctl_5nano **$0.3339**, ladder10 **$0.2803**, + ~$0.025 regrade →
  **~$0.91 measured to date** in `runs/` (plus ~$0.68 of earlier smoke runs reported
  pre-compaction and not independently re-verified — mark *that* T4 too).
- **Conclusion sentence:** "Everything measured so far cost under a dollar; the two full runs
  that would actually settle UC3 are estimated at $38 combined."
- **Never** source a cost figure from `cost_model.py`'s `THINKING` dict. It is invented and
  its own docstring says so.

---

## 10. Diminishing returns / knee plots

Shared rules for both ladders:
- **Straight segments between measured rungs. No spline, no smoothing, no interpolation.**
  With 4–5 rungs a smooth curve invents a knee position that was never measured.
- Every rung point carries its Wilson CI and its surviving-n. If n differs across rungs,
  print n at each point — unequal n across a ladder is exactly how bug 5 hid.
- Declare a knee only when a segment's slope change exceeds the CI width. Otherwise the
  caption reads "no knee observed within the tested range."
- Log x for context length; linear x for hop depth.

**`KNEE-1` — Dilution ladder.** See `UC2-C3` / `UC2-C3b`. **Data invalid on disk; rerun
pending.** The only currently plottable cells are the rung-0 baselines (99% call survival,
n=10/cell): uc2_spot 10/9/9/10, uc3_rules 9/9/8/10, uc4_formula 10/10/10/10 — i.e. flat, in
agreement with §8.

---

**`KNEE-2` — Handover ladder. TBD — chart spec only. Zero calls made.**

Build the spec now so the run is designed against a chart rather than the reverse.

- **Panel A — accuracy vs boundaries.**
  x: number of API boundaries the work is cut across, depth **1…5**, linear.
  y: end-to-end task accuracy, 0–100.
  **Two series, and the gap between them is the whole chart:**
  - **clean handover** — each step receives the *gold* intermediate. `--m-luna`, solid.
  - **live handover** — each step receives the *model's own* previous output. `--m-5nano`,
    solid.
  - Fill the area between them in `--warn` at 12% alpha, labelled **"per-hop drift"**.
  Small multiples: one panel per effort mode (4 panels), so "does effort buy hops" is
  answerable by eye.
  - **Conclusion sentence (when data exists):** "Accuracy under live handover falls X points
    per boundary while clean handover holds flat — the loss is drift across the boundary, not
    difficulty of the work."
  - **Misleading if:** only the live series is plotted. Without the clean control, a falling
    curve is indistinguishable from the task simply getting harder with depth. The control is
    not optional.

- **Panel B — per-hop drift.** x: hop index 1…5. y: pp lost at that hop. Bars.
  Shows whether drift compounds or is front-loaded.

- **Panel C — the deterministic sub-metrics** (no judge required, so no judge caveat):
  small multiples, x = depth, y = rate, three series —
  **faithfulness** (did the step pass on what it actually computed) ·
  **sufficiency** (does the payload contain what step k+1 needs) ·
  **numeric-payload survival** (did the number arrive intact and parseable).
  - **Conclusion sentence (when data exists):** "Most of what is lost across a boundary is
    lost before the next model reads it — the payload, not the reasoning."
  - This panel is the most defensible thing in the handover experiment because it needs no
    LLM judge. Prioritise it.

- **Honesty note for this section, mandatory:** the budget (~$11 for 20 items × 5 depths ×
  4 modes, doubled for both conditions) is **T4** — extrapolated from a measured $0.0066/call,
  not measured. And the *qualitative* half of the user's quant → qual → quant chain **cannot
  be graded honestly** — there is no dataset where step 2 is a qualitative analysis with a
  labelled correct answer. Say so on the slide. Panel C is the mechanical half; the quality
  of the qualitative step is not measured by anything here.

---

## 11. What we do not know — slide 30

Not a chart. A plain list, in `--ink`, no hedging:
1. **Domain drift.** Every suite is Indian financial regulation, US airline baggage, or US
   individual income tax. None is the production domain. "Results transfer by task shape, not
   subject" is an **assumption**, untested, and it is what the project's external validity
   rests on.
2. **The judge is unvalidated.** Luna grades Luna. No human-labelled sample, no second-judge
   agreement, no inter-rater number (§7.4).
3. **Single repetition.** Noise floor never measured (§8, `NC-2`).
4. **37 exclusions unreviewed** (§7, `UC4-C2`).
5. **Nothing under version control.** No way to tie a result file to the code that produced
   it — for a project whose central lesson is "the harness lied five times," that is the
   largest process risk.
6. **The reframe the user cares about most — handover — has zero implementation.**

---

## 12. Provenance appendix (ships in the deck)

Every number in the deck, its file, and how it was computed. Table, 11.5px, mono paths.

| Figure group | Source file(s) | Computation |
|---|---|---|
| BFCL per-category k/n | `.venv-bfcl/lib/python3.12/site-packages/score/gpt-5.6-luna-{none,low,medium,high}-FC/non_live/BFCL_v4_{simple_python,multiple,parallel,parallel_multiple}_score.json` | line 1 of each file: `{"accuracy","correct_count","total_count"}` |
| BFCL weighted accuracy (817/806/809/812 of 1000) | same | sum `correct_count` / sum `total_count` over 4 categories |
| BFCL failure decomposition (744/129/127) | same, lines 2+ | set ops on failing `id`s across the 4 modes |
| BFCL error-type mix | same, `error_type` field | counted per mode |
| BFCL raw items quoted | `.venv-bfcl/.../bfcl_eval/data/BFCL_v4_{cat}.json` | by `id` |
| flat40 accuracy (T2) | `runs/flat40/results.jsonl` **+ `runs/flat40/uc4_regraded.jsonl`** | UC4 rows overridden by the regrade file, keyed `(item_id, mode)` |
| flat40 raw UC4 42.5% | `runs/flat40/results.jsonl` only | **superseded — retraction chart only** |
| Control accuracies | `runs/ctl_41nano/results.jsonl`, `runs/ctl_5nano/results.jsonl` | item set verified identical to flat40 (138 ids) |
| McNemar b/c/p | the three `results.jsonl` above | exact two-sided binomial on discordant pairs |
| Wilson CIs | — | z=1.96, values precomputed in §3.3 |
| Thinking tokens, latency, $/call | `runs/*/ledger.jsonl`, `role=="target"` | **recompute cost** as `prompt_tokens*p_in + completion_tokens*p_out` at real per-model rates; the on-disk `cost` field is Luna-rated for all models |
| Corrected run costs | as above | flat40 **$0.2321** · ctl_41nano **$0.0399** (disk says $0.0662) · ctl_5nano **$0.3339** (disk says $0.9060) · ladder10 **$0.2803** |
| Smoke accuracies, $/item | `runs/smoke_all.json`, `runs/tax_smoke.json` | `correct` / `hit` fields; cost from `inp`,`out` at $0.20/$1.20 per M |
| Prompt-size medians | `runs/flat40/ledger.jsonl` (mode=none), `runs/smoke_all.json`, `runs/tax_smoke.json` | median `prompt_tokens` / `inp` |
| Gold-verbatim rates | `harness/suites.py` loaders + `datasets/indiafinbench/indiafinbench_qa.json` | case-insensitive substring of gold in `item.user` |
| Item text quoted | `datasets/indiafinbench/indiafinbench_qa.json`, `runs/smoke_all.json` | by `id` |
| Ladder call survival | `runs/ladder10/ledger.jsonl` | `ok` rate grouped by `rep` (which stores the rung) |
| Exclusion counts | `harness/suites.py` `QUARANTINE` (18), `NOT_NUMERIC` (19) | literal set sizes |
| Full-run cost projections | — | **T4.** smoke mean $/call × 3,600 |

---

## 13. The three charts that matter most

If the deck has to shrink, these three survive. They are the ones that make the work credible
rather than merely presentable.

1. **`NC-1` — the eight-configuration dot plot with the 4.3pp band.** It is the project's
   most important methodological finding, and it is the chart that stops the audience from
   believing the other accuracy numbers too readily.
2. **`UC4-C1` — the grader retraction slope chart.** A one-line bug moved a headline 52
   points. Nothing else in the deck demonstrates as economically why the evidence tiers exist.
3. **`UC1-C3` — the BFCL failure decomposition (744 / 129 / 127).** The only powered result
   in the project, and it answers the actual question — effort does not fix failures, it
   reshuffles the unstable ones.

`CLA-2` (the frontier) is the fourth, and the first one to add back.

---

## 14. Build checklist

- [ ] Palette tokens defined on bare `:root` and redefined in **both** dark blocks
- [ ] `body` has an explicit token background
- [ ] No hardcoded hex inside any `<svg>`
- [ ] Every chart: title, one-sentence conclusion subtitle, `n=` chip, tier styling
- [ ] Every accuracy mark: Wilson CI drawn
- [ ] No chart sorted by value
- [ ] Every T4 number hatched and suffixed "(est.)" with its multiplier shown
- [ ] `runs/ladder10` accuracy appears nowhere except `UC2-C4`, disabled
- [ ] On-disk control ledger costs appear nowhere; corrected figures used
- [ ] BFCL `Non-Live Overall Acc` / `Overall Acc` appear nowhere
- [ ] `cost_model.py` `THINKING` values appear nowhere
- [ ] Provenance appendix included, paths absolute
- [ ] Wide tables/charts wrapped in `overflow-x:auto`
- [ ] `<title>Luna Effort Eval</title>`, favicon `📉`, both stable across redeploys
