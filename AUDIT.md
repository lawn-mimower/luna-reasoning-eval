# Adversarial audit — Luna reasoning-effort evaluation

Date: 2026-08-27. Every number below was recomputed from `runs/*` and
`.venv-bfcl/.../result|score` on this machine. Nothing is quoted from
`CLAUDE.md`, `SESSION_REVIEW.md` or the report without re-deriving it.

Classification used throughout:
**(a) definitely wrong** — the code or the data contradicts the claim;
**(b) unsupported** — the claim may be true but the evidence does not carry it;
**(c) fragile** — currently correct, but held together by something that will break.

---

## Summary of decision impact

| # | Finding | Class | Changes a decision? |
|---|---|---|---|
| 1 | `parse_carry()` splits on `;`, `stage_instruction()` templates `, ` — 96/96 two-key payloads silently truncated. The "sufficiency 66%" finding and the schema recommendation are pure artifact; the live-vs-clean "price of a handover" is contaminated. | (a) | **Yes** — retracts a shipped recommendation |
| 2 | UC2/UC3 "flat to 30k tokens" is a null measured on the three suites the report itself retracts in §03. Rung-0 accuracy is 95%; the ladder never left the ceiling. 34 errors in 840 calls, 25 of them from 2 items. | (b) | **Yes** — two `none` recommendations rest on it |
| 3 | BFCL "`none` is top of the weighted table" is noise: `none` vs `high` McNemar p = 0.675, `none` vs `low` p = 0.248. Only the cost half of the UC1 argument survives (and the `parallel_multiple` regression, which is real at p = 0.0009). | (b) | **Yes** — downgrades a "High confidence" row |
| 4 | Handover n = 12 items chosen as `[:4]` per level, not sampled. 2 of the 12 are unsolvable at every mode/depth; excluding them the ladder is 17.5 / 70 / 92.5 / 95%, not 15 / 58 / 77 / 79%. | (c) | Shifts magnitudes, not the sign |
| 5 | `needle_frac` spans 0.33–1.0, mean 0.772; **zero** observations below 0.33, and position is ~fixed per item. "Position randomised" is false and the position plot is an item-identity plot. | (a) | Retracts a figure |
| 6 | `_key_terms()` returns an **empty** ban-list for 10 of 12 sampled ladder golds — the "no distractor can also answer it" guarantee is not enforced for most items. | (c) | Weakens a construction claim |
| 7 | Every mode comparison outside handover/BFCL is reps = 1 and lands inside its own CI. | (b) | Already caveated, under-caveated in §08 |
| 8 | `budget.py` costs control runs at Luna's rate; ledgers on disk are inflated 1.7× / 2.7×. The report's `$6.99` is nonetheless correct (it applied real prices); the `9,426 calls` headline is not. | (a) | Cosmetic + audit-trail risk |
| 9 | `results_regraded.jsonl` was produced by a script that is not on disk; `runs/flat40/results.jsonl` still holds superseded UC4 verdicts. Nothing is in version control. | (a) | Reproducibility |

---

## 1. **(a) The sufficiency finding is a separator bug, not a model behaviour**

This is bug #10 and it is the same species as #8 and #9.

`harness/handover.py:123`
```python
keys = ", ".join(f"{STAGES[i][0]}=<value>" for i in stage_ids)
tail = (f"\nEnd with exactly one line handing your results to the next step:\n"
        f"CARRY: {keys}\n" ...)
```
`harness/handover.py:100`
```python
for part in m.group(1).split(";"):
```
The instruction tells the model to emit `CARRY: TOTAL_INCOME=<value>, AGI=<value>`.
The parser splits on `;`. The module docstring (`handover.py:94`) says the contract
is `CARRY: KEY=value; KEY=value` — the docstring and the prompt disagree, and the
parser follows the docstring.

Recomputed from `runs/ho_live2/results_regraded.jsonl`:

| group size | hops | judged `sufficient` |
|---|---|---|
| 1 key | 192 | 190 True / 2 False |
| 2 keys (`[0,1]`, at depths 2 and 3) | 96 | **0 True / 96 False** |

All 96 two-key hops emitted a complete, correct payload. A verbatim example
(mode `none`, depth 2):

```
CARRY: TOTAL_INCOME=88732, AGI=81318      ->  emitted = {'TOTAL_INCOME': 88732.0}
```

`AGI` was present and correct and was thrown away by `.split(";")`.
Separator census across all 288 non-final hops: `{('comma',2): 96, ('single',1): 191, ('comma',1): 1}` —
i.e. **100% of multi-key hops used the comma the prompt asked for.**

Consequences, in order of severity:

1. **The report's contract recommendation is void.** §05: *"Sufficiency is the
   weak link at 66%: a third of payloads omit a field the next stage needed"*, and
   §08: *"Pin the handover payload to an explicit schema and a third of the
   observed failures disappear."* True sufficiency is **286/288 = 99.3%** — the
   only two genuine failures are `none` emitting `TAXABLE_INCOME=UNDETERMINED`.
   Acting on this recommendation means rewriting a production payload schema to
   fix a defect that does not exist.
2. **The `live` condition was crippled at depths 2 and 3.** `run_chain` does
   `carried.update(emitted)` (`handover.py:196`), so at those depths the next
   stage was handed `TOTAL_INCOME` only and had to re-derive AGI, while the
   `clean` condition supplied both golds (`handover.py:193`). The live-vs-clean
   gap at depths 2–3 therefore measures the harness dropping half the payload,
   not the model dropping it. The reported "handover cost" (−22 / −17 / −6 / −11)
   does not survive restriction to depth 4, the only depth with no two-key group:

   | effort | live d4 | clean d4 | gap |
   |---|---|---|---|
   | none | 2/12 | 4/12 | −17 pts |
   | low | 8/12 | 10/12 | −17 pts |
   | medium | 10/12 | 11/12 | −8 pts |
   | high | 10/12 | 11/12 | −8 pts |

   The claimed ordering ("largest at `none` 22 points, smallest at `medium` 6")
   is gone; every cell differs by 1–2 items out of 12. The sentence *"Reasoning
   effort … makes the chain more robust to its own upstream errors"* is not
   supported at any usable confidence.
3. **`AGI` faithfulness was never checked at depths 2–3**, because the key never
   reached `emitted` (`handover.py:158`, `if k in emitted`).

Credit where due: the Live/Clean **columns** are correctly matched — `ho_clean`
only ran depths 2–4 (432 target calls = 12 items × 4 modes × (2+3+4)) and the
report's Live column recomputes to exactly 3/36, 23/36, 28/36, 28/36 = 8/64/78/78%
on the same depths. That comparison is not confounded by depth. It is confounded
by the parser.

### 1b. **(b) Faithfulness is weak, and it is not the metric that matters**

`handover.py:146–163` scores a hop faithful if the carried number matches **any**
number anywhere in the body, within $0.51. The bodies contain a median of 39
numbers. A permutation null — testing each emitted value against a *randomly
chosen other hop's* body — passes 13/286 = 4.5% of the time, so the metric is not
literally vacuous, but 99.7% observed against a 4.5% floor on a check with 39
chances to match is a low bar. It also measures self-consistency, never
correctness, and `faithful=None` when no CARRY is emitted, so a step that drops
the payload entirely is excluded rather than counted against.

The metric that matters is in the data and is not reported. Carried value vs
RuleArena's own gold intermediate:

| effort | TOTAL_INCOME | AGI | TAXABLE_INCOME | all |
|---|---|---|---|---|
| none | 31/36 | 4/12 | 3/22 | **38/70 = 54%** |
| low | 36/36 | 11/12 | 20/24 | 67/72 = 93% |
| medium | 36/36 | 11/12 | 21/24 | 68/72 = 94% |
| high | 36/36 | 10/12 | 18/24 | 64/72 = 89% |

This is a better version of the report's own argument and it should replace both
published payload metrics. (AGI n is 12, not 36, precisely because of finding 1.)

---

## 2. **(b) The dilution ladder is a null result on retracted instruments**

`harness/ladder.py:80` defaults `--suites uc2_spot,uc3_rules,uc4_formula` — the
three suites the report withdraws in §03 (*"A benchmark that cannot separate
models three tiers apart cannot justify a reasoning setting"*). §04 then rebuilds
the same 30 items and draws a positive conclusion from their flatness.

Recomputed (`runs/ladder10` + `runs/ladder_hi`, 840 rows, all cells n=30):

| rung | none | low | medium | high | pooled |
|---|---|---|---|---|---|
| 0 | 30/30 | 28/30 | 28/30 | 28/30 | 114/120 |
| 2,500 | 29 | 29 | 29 | 30 | 117/120 |
| 5,000 | 29 | 30 | 29 | 30 | 118/120 |
| 10,000 | 28 | 28 | 28 | 28 | 112/120 |
| 15,000 | 29 | 27 | 28 | 29 | 113/120 |
| 20,000 | 29 | 28 | 29 | 29 | 115/120 |
| 30,000 | 29 | 29 | 29 | 30 | 117/120 |

The report's §04 table reproduces exactly. But:

- **Rung 0 is already 95%.** The ladder starts at the ceiling and never leaves it.
  A null here is what §03 predicts for these items regardless of context length —
  it is not independent evidence that effort buys no context headroom.
- **34 errors in 840 calls, and 25 of them come from two items**: `REG_015` (15)
  and `TMP_062` (10). `REG_015` is a grader-consistency failure, not a retrieval
  failure — at rung 0 the judge accepts *"120 calendar days from the expiry of the
  sixty-day window"* for `high`, and at diluted rungs marks the same shape of
  answer INCORRECT for *"omitting the qualifying condition … or the first hearing"*.
  Over half the ladder's total error signal is one item being graded inconsistently.
- **No comparison in the ladder is significant.** `none` vs `high` pooled:
  203/210 vs 204/210, McNemar b01=6/b10=7, **p = 1.0**. Rung 0 vs rung 30,000
  pooled across modes: b01=3/b10=6, **p = 0.51**. The headline "Retrieval: 0 pts"
  is accurate as a point estimate (+0.5 pp) and honest, but the surrounding claim
  *"Reasoning effort buys no context headroom because there is no cliff to hold
  back from"* is a null on a saturated instrument, not a finding.
- §08 rates UC2 (`none`, Medium confidence, evidence *"flat to 30k tokens"*) and
  UC3 single-call (`none`, Medium confidence, evidence *"flat across the dilution
  ladder"*). Both rows inherit the retraction in §03. They should read "no
  instrument", not "`none`".

**What does hold:** the 429 problem was genuinely fixed. `runs/ladder10/ledger.jsonl`
contains two passes (960 target rows). Pass 1 lost **285/480** to `RateLimitError 429`,
scaling with rung (0/60 at rung 0 → 28/60 at 10k). Pass 2 lost **0/480**.
`ladder.py` writes `results.jsonl` with mode `"w"`, so the file on disk is the
clean pass. No survivorship bias in the published ladder numbers. `ladder_hi` has
zero failures. Confirmed.

Also confirmed clean: no call in any run hit its `max_completion_tokens` cap
(`client.py:78`). Max completions observed — flat40 840/32000, ladder 979/32000,
ho_live2 14,471/32,000, `none` max 2,824/4,000. The mode-dependent cap is not
biasing anything at present, though it remains a per-mode selection lever if
prompts grow.

---

## 3. **(b) BFCL: the accuracy half of the UC1 recommendation is noise**

Recomputed from `.venv-bfcl/.../score/gpt-5.6-luna-*-FC/non_live/*.json`:

| effort | simple(400) | multiple(200) | parallel(200) | parallel_multiple(200) | weighted /1000 |
|---|---|---|---|---|---|
| none | 324 | 171 | 168 | 154 | **817 = 81.70%** |
| low | 328 | 167 | 170 | 141 | 806 = 80.60% |
| medium | 331 | 169 | 171 | 138 | 809 = 80.90% |
| high | 338 | 168 | 166 | 140 | 812 = 81.20% |

The report's four figures are exact. Cost recomputed from `input_token_count`/
`output_token_count`: $0.1169 / $0.1388 / $0.1456 / $0.1571, total **$0.5585**
(report: $0.56 ✓), high/none per item **1.34×** (report: "34% more" ✓). Input
tokens identical (208,301) across all four — same items, apples to apples.
Effort demonstrably transmitted: `reasoning_content` is present in the `low`/
`medium`/`high` result rows and absent from `none`, and mean output tokens climb
62.7 → 81.0 → 86.6 → 96.2. `luna_handler.py:38` hooks `generate_with_backoff`,
which both `_query_FC` (`openai_response.py:124`) and `_query_prompting`
(`:240`) call after setting `reasoning`, so the injection does cover both paths —
though only the `-FC` variants were actually run.

**What fails:** paired McNemar over the 1,000 items —

- `none` vs `high`: b01=48, b10=43, **p = 0.675**
- `none` vs `low`: b01=43, b10=32, **p = 0.248**
- `none` vs `medium`: b01=42, b10=34, **p = 0.422**
- `medium` vs `high`: **p = 0.801**

§08 lists UC1 as `none`, confidence **High**, evidence *"best weighted score and
cheapest"*. "Best weighted score" is unsupported — the four settings are
indistinguishable. "Cheapest" is real and sufficient on its own; the
recommendation is right, the stated reason is half wrong.

**What holds, strongly:** the `parallel_multiple` regression is real —
`none` vs `medium` b01=19/b10=3, **p = 0.0009**; vs `low` p = 0.0044; vs `high`
p = 0.0026 (n=200 each, survives Bonferroni over 12 comparisons). Reasoning
genuinely hurts on the hardest tool category. That is the most defensible single
result in the BFCL section and it is under-sold relative to the null.

One presentation note: BFCL's own `data_non_live.csv` reports these runs at
66–68% Non-Live Overall, because Irrelevance Detection was not run and enters as
N/A. The report's 81% is the AST-only weighted mean, which is a legitimate and
stated choice, and the ranking is identical in both. Not an error, but anyone
opening the scorer output will see a different number.

---

## 4. **(c) Handover: 12 hand-picked items, two of them ungradeable**

`handover.py:222–226`
```python
per = max(1, a.items // len(levels))
for lvl in levels:
    chosen += by_level.get(lvl, [])[:per]
```
No shuffle. The sample is items 000–003 of each complexity level, in file order.
Against the full 300-item suite:

| level | population schedules (mean) | selected | population prompt chars (median) | selected (median) |
|---|---|---|---|---|
| 0 | 0.00 | 0,0,0,0 | 19,534 | 19,540 |
| 1 | 1.42 | 1,2,1,0 | 25,998 | **21,603** |
| 2 | 3.28 | 4,3,3,3 | 34,895 | **31,344** |

Level 1 is under-represented on schedule count (1.00 vs 1.42) and the selected
prompts are 10–17% shorter than typical at levels 1 and 2. The sample skews easy,
which inflates every accuracy in §05 and §06 by an unknown amount.

Worse, **2 of the 12 items are never solved by anything**:

```
item             none low med high   (correct out of 4 depths)
RA_tax_0_001        0   0   0    0
RA_tax_2_001        0   0   0    0
```

`RA_tax_0_001`: 12 of 16 live chains converge on exactly **$2,911.68** against a
gold of $3,241.68 — a constant $330.00 gap. This is `CLAUDE.md` open item 2, and
it is now resolvable from data already on disk: under the **clean** condition,
where the model is handed the gold `TOTAL_INCOME`/`AGI`, it returns **3,241.68 in
8 of 12 chains**. The gold is corroborated by the model's own arithmetic; the
error is Luna's, upstream of taxable income. Close the open item as "gold is
correct".

`RA_tax_2_001`: gold −7,982.50, live converges on −8,149.08, clean on −8,155.08
with only 1/12 correct. This one is *not* explained and is a plausible bad gold or
a genuinely unsolvable item. It is 8% of the handover sample.

Excluding the two zero-yield items the headline ladder becomes:

| effort | reported | 10 gradeable items |
|---|---|---|
| none | 15% (7/48) | **17.5%** (7/40) |
| low | 58% (28/48) | **70.0%** (28/40) |
| medium | 77% (37/48) | **92.5%** (37/40) |
| high | 79% (38/48) | **95.0%** (38/40) |

The direction and the decision (`medium`) are unchanged, but the headline
"15% → 79%" and the "medium 77%, high 79%, plateau" framing are both artefacts of
including two items nothing can solve. On the gradeable set `medium` and `high`
are 92.5% and 95% — i.e. at ceiling, which is a *stronger* argument for `medium`
than the one made, and a weaker basis for the "+2 pts" phrasing.

**Statistical status of the handover result — this part is solid.** Paired McNemar
on 48 item×depth cells: `none` vs `medium` b01=0/b10=30, **p = 1.9e-9**;
`low` vs `medium` p = 0.012; `medium` vs `high` b01=1/b10=2, **p = 1.0**.
Clustering properly at the item level (sign test over 12 items) it survives:
`none` vs `medium` 0 wins / 10 losses, p = 0.002; `low` vs `medium` 0/7, p = 0.016;
`medium` vs `high` 1/2, p = 1.0. The `none` collapse is real and is **not** a
parsing artifact: the `none` predictions are well-formed wrong numbers
(`RA_tax_2_003` d1 predicts 18.0 against a gold of 20,961.91), `none` emits a
parseable `CARRY` on 70/72 non-final hops and an `ANSWER:` line on 48/48 final
hops, and it hit no token cap (max 2,824 of 4,000). Its carried intermediates are
correct 54% of the time against 89–94% for every other setting. The collapse is
capability.

One over-claim inside it: §05 says *"At `none` it collapses at every depth,
including depth 1 where no handover occurs at all — so the failure is capability,
not drift."* `none` by depth is **4, 1, 0, 2 of 12** — 33% at depth 1 against 8%
at depths 2–4 (Fisher one-sided p = 0.055). There is a marginal depth effect at
`none` that the sentence dismisses. The safe statement is "the collapse is present
at depth 1, so capability is *part* of it".

Also worth flagging against the bold claim *"The work never changes"*: depth 4
re-injects the 19.5k-token rulebook four times, so a depth-4 chain costs 2.3×
(`none`) to 1.5× (`high`) what a depth-1 chain costs and takes 1.4–2.3× the wall
clock. The §06 `$/chain` column pools all four depths; at depth 1 alone the
figures are $0.0037 / $0.0047 / $0.0055 / $0.0102, not $0.0060 / $0.0077 /
$0.0089 / $0.0133.

---

## 5. **(a) `needle_frac` is neither randomised nor uniform — quantified**

`harness/haystack.py:82` creates `rng = random.Random(seed)` fresh on every call
and `ladder.py:116` passes the same `seed=42` for every item and every rung. The
consequence is worse than "deterministic": the draw is *conditioned on the item*.

Recomputed over all 720 diluted rows:

- range **0.33 – 1.00**, mean **0.772**, only **53 distinct values** in 720 rows
- bin counts: first 20% **0**, 20–40% **32**, 40–60% **16**, 60–80% **492**, last 20% **180**

and position is essentially an item label:

```
REG_003  0.750 0.761 0.776 0.779 0.795 0.895      (six rungs)
REG_014  0.330 0.332 0.348 0.364 0.441 0.457
REG_199  0.746 0.779 0.787 0.807 0.833 0.895
```

So `plots.py::needle_position` (both panels) plots accuracy against a variable
that is 1:1 with item identity, with two of its five bins empty or n≤32. Its
caption — *"Position randomised per item under a fixed seed and recorded, so this
is independent of context length"* — is false in both halves: it is not
randomised across items, and it is not independent of item. The figure should be
withdrawn, not re-captioned. The report body does not lean on it heavily, but §04
does assert *"needle position randomised under a fixed seed"* as part of the
construction's credibility.

Mechanically: 90% of positions land in the back half of the context, which is
generally the *easy* region for long-context retrieval. "No knee to 30k" was
measured with the needle almost always late.

---

## 6. **(c) The anti-ambiguity filter mostly does nothing**

`harness/haystack.py:57–62`
```python
terms = set(re.findall(r"\d[\d,]*\.?\d*\s*(?:per\s*cent|percent|%|crore|lakh)?", g))
...
return {t.strip() for t in terms if len(t.strip()) > 2}
```
The regex requires a **digit**. IndiaFinBench golds are frequently written in
words — `"At least twenty per cent."`, `"One hundred and twenty calendar days…"`.
For those the ban-list is empty and **every** distractor passes unchecked.

Measured over the 30 ladder items: mean rejection rate **2.1%** of a 405-passage
pool; for 10 of the first 12 items the ban-list has **zero** entries and zero
distractors are rejected. §04's *"any distractor containing the gold's figures
rejected so no second answer could appear"* is not enforced for the majority of
items.

It has not bitten yet — I checked directly: only 1 of 30 ladder items has its own
context duplicated in the distractor pool (7 contexts repeat across 322 in the
corpus), and for two hand-built 30k haystacks the true context and gold string
each appear exactly once. But at rung 30,000 the prompt holds ~285 of the corpus's
405 passages, i.e. 70% of everything available, so the guarantee is doing almost
no work at exactly the length where it matters most. Treat the construction claim
as unverified rather than false.

---

## 7. **(b) Statistical validity of everything outside handover and `parallel_multiple`**

`runs/flat40/results.jsonl` has `reps: [0]` — **one** repetition, despite
`runner.py:125` defaulting to `--reps 5`. The ladder and both handover runs are
also one rep per cell. No item was ever run twice at the same mode, so the
same-mode noise floor has never been measured anywhere in this project.

Recomputed flat40 (with UC4 taken from `uc4_regraded.jsonl`):

| suite | n | none | low | medium | high |
|---|---|---|---|---|---|
| uc2_spot | 40 | 40 | 40 | 39 | 40 |
| uc3_rules | 40 | 37 | 37 | 37 | 37 |
| uc3_contradiction | 18 | 16 | 17 | 17 | 17 |
| uc4_formula | 40 | 38 | 40 | 39 | 38 |
| **total** | **138** | 94.9% | 97.1% | 95.7% | 95.7% |

Paired tests, all null:

- Luna `none` vs `low`: b01=1/b10=4, p = 0.375
- Luna `none` vs `high`: b01=3/b10=4, p = 1.0
- **Luna `none` vs `gpt-4.1-nano`: b01=7/b10=4, p = 0.5488** — the `p=0.549`
  claim reproduces exactly, to four decimals
- Luna `low` vs `gpt-5-nano low`: p = 0.146; `high` vs `high`: p = 1.0

The "4.3 pp across eight configurations, nothing separates" conclusion is sound
and independently supported. Nothing else in flat40 is.

Judge health check (all 1,995 judge calls across five runs): zero failures in any
run that produced a published number, zero empty verdicts, zero responses hitting
the 256-token cap (max 56), zero judge reasoning tokens. Every verdict in the
final files parses as `CORRECT`/`INCORRECT` except 144 rows that are stale
`grade_numeric` details in `flat40/results.jsonl` (see §9).

---

## 8. **(a)+(b) Cost and call accounting**

`harness/budget.py:52–56`
```python
@property
def cost(self) -> float:
    return self.prompt_tokens * PRICE_IN + self.completion_tokens * PRICE_OUT
```
`PRICE_IN`/`PRICE_OUT` are Luna's. `prices_for()` (`budget.py:29`) is called
nowhere in the repo. The comment at `budget.py:16–17` states the table exists
"so that a weaker-model control run is not silently costed at Luna's rate" —
which is exactly what happens.

Ledger error, per run, recomputed at real per-model prices (target calls at the
target model's rate, judge calls at Luna's):

| run | on disk | correct | error |
|---|---|---|---|
| ctl_5nano | $0.9060 | $0.3339 | **2.71×** |
| ctl_41nano | $0.0662 | $0.0399 | **1.66×** |
| all others | — | — | correct (Luna) |
| **sum of ledgers** | **$7.0317** | **$6.4333** | |

Add BFCL's $0.5585 and the corrected total is **$6.9918** — so the report's
**$6.99 is right**, and its claim that every dollar was "recomputed from per-call
token counts in the run ledgers" is honest. The `cost` field written into the
JSONL on disk is still wrong for both control runs and will mislead the next
reader.

**`9,426 graded API calls` does not hold up.** On-disk ledger rows total 5,426;
5,426 + 4,000 BFCL = 9,426. But of those 5,426:

- 1,995 are **judge** calls, which grade rather than are graded
- 285 are **failed 429s** that returned nothing
- 195 are pass-1 ladder survivors that were **overwritten** by pass 2
- 95 are the aborted `ho_live` (85) and `ho_smoke` (10) runs

Model outputs that actually feed a published number: 552 + 138 + 414 + 480 + 360
+ 912 + 4,000 = **6,856**. The headline overstates by ~37%. It also silently
includes $0.23 of aborted/smoke spend in the $6.99.

Verified correct in §06: `think/hop` 0 / 498 / 856 / 2,311; `sec/hop` 5.7 / 10.5 /
14.1 / 26.3; `$/chain` 0.0060 / 0.0077 / 0.0089 / 0.0133; `none→medium` = 1.48×.
All reproduce to the digit. The 200k TPM account limit and the "6–13 decisions
per minute" derived from it cannot be checked from anything on disk.

---

## 9. **(a) Reproducibility of the numbers that changed the headline**

- **The regrade script does not exist.** `runs/ho_live2/results_regraded.jsonl`
  and `runs/ho_clean/results_regraded.jsonl` were written at 05:59 by something
  that is not in the repo. 67 rows differ from `results.jsonl`; **49 flip
  False→True, 0 flip True→False**; `pred is None` drops from 68 to 1. This is the
  single edit that produced the report's headline, and it cannot be re-run or
  reviewed. The fix now lives in `handover.py:177–186`, but that code has never
  produced these files.
- **The regrade read a 600-character window.** `handover.py:169` stores
  `"text": r.text[-600:]`; 407 of 412 stored hop texts are exactly 600 chars, so
  the full responses are gone. Any answer that was not inside the last 600
  characters is unrecoverable. It happens that `ANSWER:` is in-window for 48/48
  final hops per mode, so nothing is lost *here* — but there is no margin, and the
  faithfulness recomputation is also limited to this window.
- **`runs/flat40/results.jsonl` still carries superseded UC4 verdicts.** 144 rows
  have `grade_numeric` details (`"gold=[...] pred=[...] matched=[...]"`) and 54 of
  them label a row `correct` in a way that contradicts nothing else on disk only
  because there is no marker saying which file wins. Anyone opening the obvious
  file reads UC4 at ~42.5%.
- **`grade_numeric` is dead but retained.** `runner.py:32` sets
  `NUMERIC_SUITES = set()` and `ladder.py:27` imports only `grade_final_value` and
  `grade_llm`, so `judge.py:73–98` and `_gold_head()` (`judge.py:61`) are
  unreachable. Confirmed: every method in every current results file is `llm` or
  `final_value`. Fine to leave, but it is the function that caused two of the nine
  bugs and it is still importable from `runner.py:22`.
- **No version control.** Not a git repo. `handover.py` and `plots.py` have both
  been edited after the runs they describe.

---

## 10. Smaller items

- **(c) `ladder.py:105` claims the wrong provenance.** `random.Random(a.seed).shuffle(items)`
  is a *fresh* RNG per suite; `runner.py:64` advances one shared RNG across suites.
  The comment "same seed/order as the runner" is true only for the first suite.
  Measured overlap with flat40's 40-item samples: uc2_spot 10/10, uc3_rules 7/10,
  uc4_formula 6/10 — and only 1/10 and 3/10 respectively are in the runner's first
  ten. The ladder's docstring claim that its numbers are "directly comparable to
  runs/flat40/" is therefore wrong as stated; it is saved only by the fact that
  the ladder re-measures its own rung-0 baseline.
- **(c) The `rep` field means three different things.** `runner.py` writes
  repetition, `ladder.py:137` writes **rung**, `handover.py:141` writes **depth**.
  `Ledger.done_keys()` and any future resume logic key on it. Any aggregate over
  `rep` across runs is meaningless.
- **(b) The "every bug made the model look worse" asymmetry is a selection
  effect.** The stated working rule is *"a suite scoring uniformly zero is a
  harness bug until proven otherwise"* — a detector that only fires on
  implausibly *low* scores. A bug that flatters the model produces a plausible
  number and is never investigated. §07's inference (*"the risk here is
  understating the model, not flattering it"*) does not follow from the sample of
  bugs the process is capable of finding. Finding 1 is the tenth bug of the same
  shape found by an outside reader in one pass.
- **(b) `QUARANTINE` / `NOT_NUMERIC` (`suites.py:18–45`) remain unreviewed.** 18
  items dropped and 19 relabelled out of 406, on the model's own judgment about
  which golds are wrong. Directionally these raise measured accuracy. The
  `NOT_NUMERIC` move is conservative (it takes easy table-lookups *out* of UC4),
  but nobody has checked the 18 quarantine calls, and 95–100% is the number the
  saturation argument rests on. The controls carry that argument independently, so
  this is a documentation gap rather than a live risk.
- **(c) The judge sees different inputs in different runs.** `runner.py:110`
  passes `u.item.user` (question **plus** passage); `ladder.py:147` passes the bare
  question `q`. Cross-run accuracy comparisons between flat40 and the ladder are
  therefore not strictly like-for-like even where the items coincide.
- **(b) Luna grades Luna and the grader has still never been validated.** No
  human-labelled sample, no second-judge agreement, no inter-rater number. I
  sampled the verdicts and found no gross leniency — the judge correctly accepts
  `8.888…%` against a gold of `"approximately 8.9 per cent"` on NUM_038, and
  correctly rejects incomplete multi-fact answers. But `REG_015` (§2) shows the
  judge grading two near-identical answers differently, and that single item
  accounts for 44% of the ladder's total error count. One 50-item human-labelled
  sample would settle it.

---

## Verdict

Two conclusions are safe to act on:

1. **Reasoning effort transforms chained computation.** `none` → `medium` on the
   RuleArena tax handover is 7/48 → 37/48, McNemar p = 1.9e-9, and it survives
   item-level clustering (0 wins / 10 losses across 12 items, p = 0.002). `medium`
   → `high` is p = 1.0. The `none` collapse is genuine capability failure, not a
   parser artifact — verified against the raw predictions, the CARRY emission rate,
   the token caps, and the carried-intermediate accuracy (54% vs 89–94%). Ship
   `medium` for chained computation. The magnitudes should be restated on the 10
   gradeable items (17.5 / 70 / 92.5 / 95%), not 15/58/77/79.
2. **`none` for tool calling**, on cost. `high` costs 1.34× per item for a
   difference of 0.5 pp at p = 0.675. And `parallel_multiple` genuinely degrades
   under reasoning (p = 0.0009) — the strongest, most under-sold result in the
   report.

Three things should be pulled before this is circulated further:

- The **sufficiency finding and the schema recommendation** (§05, §08). Both are
  produced by a `;` vs `, ` mismatch between the prompt and the parser. Real
  sufficiency is 99.3%.
- The **live-vs-clean "price of a handover" table** (§05). The same bug crippled
  the live arm at depths 2 and 3; at the one uncontaminated depth the ordering
  disappears and every cell is 1–2 items out of 12.
- The **UC2 and UC3 `none` recommendations** (§08). They rest on a null measured
  at 95% ceiling on the three instruments §03 explicitly retracts, with 74% of the
  observed error concentrated in two items, and with the needle in the back half
  of the context in 90% of trials. "No instrument yet" is the honest row.

The headline dichotomy survives, but only half of it is measured. "Reasoning does
nothing for retrieval" is an unfalsifiable null on a saturated benchmark;
"reasoning transforms chained computation" is a strong, well-powered result. The
report presents them as two symmetric findings of equal weight. They are not.
