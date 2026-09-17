# Indian-law injection-benchmark corpus

Downloaded by [`../download.ipynb`](../download.ipynb). Verify integrity against
`MANIFEST.json` (size + sha256 + row count per file).

Target task shape: **inject a context passage, ask a question, compare the model's answer
to a gold answer.** No retrieval, no ranking. The column that matters most below is
*Context*.

| Dataset | Rows | Context | Gold answers | License |
|---|---|---|---|---|
| [IndiaFinBench](#indiafinbench) | 406 | **inline** | human expert | CC BY 4.0 |
| [BNS / BNSS / BSA](#bns--bnss--bsa) | 6,354 | join on section | template-generated | Apache 2.0 |
| [CourtNav RAG](#courtnav-rag) | 21 | **inline + PDFs** | lawyer-verified | Apache 2.0 |
| [Law entrance exams](#law-entrance-exams) | 6,218 | MCQ (passage inline) | official keys | MIT |
| [IndicLegalQA](#indiclegalqa) | 10,000 | none | GPT-4o generated | CC BY 4.0 |
| [IL-TUR](#il-tur) | 484,316 | n/a — no question field | class labels | **CC BY-NC-SA 4.0** |

---

## IndiaFinBench

`indiafinbench/` · 406 items over 192 SEBI/RBI documents · repo `Rajveer-code/IndiaFinBench`
· arXiv 2604.19298 (under review, FinNLP @ EMNLP 2026 — not yet peer-reviewed).

**The only set here that natively ships `context`.** Answers frequently require work over the
passage rather than extraction from it — e.g. a `numerical_reasoning` item gives three
per-year minimums and asks for the three-year total.

| file | rows | notes |
|---|---|---|
| `indiafinbench_qa.json` | 406 | **use this** |
| `indiafinbench_qa.csv` | 406 | same benchmark, CSV |
| `judge_audit_log.csv` | 874 | LLM-judged predictions, 12 models |

### Two record schemas — a loader assuming one will crash

**A — single context (344 rows)**
```
id, task_type, source, document, [regulation], context, question, answer,
answer_type, difficulty
```
**B — dual context (62 rows, all `contradiction_detection`)**
```
id, task_type, source, document_a, document_b, [regulation_a], [regulation_b],
context_a, context_b, question, answer, answer_type, difficulty, explanation
```
`regulation` is absent on 84 rows. `explanation` exists only on schema B.

### Distributions
- task_type — regulatory_interpretation 174 · numerical_reasoning 92 · temporal_reasoning 78 · contradiction_detection 62
- answer_type — extractive 267 · calculated 77 · yes_no 62
- difficulty — easy 160 · medium 182 · hard 64
- source — SEBI 338 · RBI 68
- context length — min 117 / median 382 / max 988 chars

### `judge_audit_log.csv`
```
id, task_type, auto_score, judge_score, flipped, judge_reason,
question, ref_answer, prediction, model
```
**Every row has `auto_score = 0`** — this is an audit of only what automatic scoring marked
wrong, not a full agreement study. An LLM judge overturned **685 of 874 (78.4%)** to correct,
flat across task types (numerical 78.2%, temporal 76.4%, regulatory 79.8%).

Read both ways: exact/fuzzy match is unusable on free-text regulatory answers, **and** this
judge is permissive. There are no `auto=1 → judge=0` rows, so it cannot tell you the judge's
false-positive rate — the number you would actually need to trust your own judge.

---

## BNS / BNSS / BSA

`bns_bnss_bsa/` · 6,354 QA over the 2023 criminal codes · HF `GSMS-B/Indian-Legal-QA-BNS-BNSS-BSA`.

The **only set here on current law** — BNS, BNSS, and BSA replaced the IPC, CrPC, and Evidence
Act in July 2024.

| file | rows | sections |
|---|---|---|
| `bns_qa.jsonl` | 2,148 | 358 |
| `bnss_qa.jsonl` | 3,186 | 531 |
| `bsa_qa.jsonl` | 1,020 | 170 |
| `bns_bnss_bsa_combined_clean.jsonl` | 6,354 | 1,059 | **repaired — use this** |

Schema: `chunk_id, act, section_number, section_title, question, answer, question_type`

No context field, but `act` + `section_number` resolves deterministically against the published
Act text — no fuzzy matching needed.

**Template-generated**: exactly 6 questions per section, one per type — `definitional_topic`,
`definitional_section`, `scenario`, `elements`, `exceptions`, `consequence`.
1,059 × 6 = 6,354 exactly. Answers carry `[Source: Section X, ACT 2023]`.

### Defects (repaired in the `_clean` file, still present in the raw ones)
1. Row `BNSS_158` uses key **`sectionnumber`** instead of `section_number`. One row in 6,354 —
   and it breaks the HuggingFace dataset viewer for the entire repo (`CastError`).
2. `bsa_qa.jsonl` carries a **UTF-8 BOM**. Read with `encoding="utf-8-sig"`.

---

## CourtNav RAG

`courtnav_rag/` · 21 lawyer-verified rows · HF `adalat-ai/Indian-Legal-Retrieval-Generation`
· arXiv 2601.05255. **Gated** (`gated: "auto"`) — needs `HF_TOKEN`.

Schema: `Query, Context, Document, Gold Answers`

Too small to be an eval set, but **the best record format here**: `Context` holds numbered
spans with page references (`[1] Doc 1 ... – Page 1: ...`) and `Gold Answers` carries inline
citation markers pointing back at them. That lets you score answer correctness and citation
grounding as separate signals — worth copying into your own schema.

`source_docs/` holds the 4 source PDFs: special power of attorney, Indian Contract Act 1872,
DRT application, civil revision petition.

---

## Law entrance exams

`law_entrance_exams/` · 6,218 MCQs from 38 papers, 2008–2025 · HF
`adalat-ai/indian-legal-exam-benchmark` · arXiv 2510.17900. **Gated** — needs `HF_TOKEN`.

Schema: `question_text, options[4], answer, source_paper`

| file | rows | papers |
|---|---|---|
| `clat_ug.parquet` | 3,154 | 18 |
| `djs_dhjs.parquet` | 2,250 | 13 |
| `clat_pg.parquet` | 814 | 7 |

Not an injection benchmark — the answer is a letter, so it is exact-match, not judged. CLAT UG
comprehension items do embed a passage inside `question_text`, which makes them usable as a
cheap closed-book knowledge probe.

---

## IndicLegalQA

`indiclegalqa/` · 10,000 QA from 1,253 Supreme Court judgments · Mendeley DOI
`10.17632/gf8n8cnmvc.2` · **GPT-4o-generated**, manually reviewed.

Schema: `case_name, judgement_date, question, answer`
Question median 15 words; answer median 34 words.

**No context field and no usable pointer to one** — recovering context means joining 1,253 case
names against IndianKanoon.

| file | rows | schema |
|---|---|---|
| `indiclegalqa_revised.json` | 10,000 | clean, 1 keyset — **use this** |
| `indiclegalqa_original.json` | 10,002 | **4** inconsistent keysets |

The two files are **not the same dataset**: 9,100 questions shared, 882 only in revised,
859 only in original. The original also has spelling drift (`judgment_date` vs
`judgement_date`) and 608 rows with a `reference_pdf` field of opaque codes (90 distinct,
e.g. `civ6`) and no shipped mapping.

Because the gold answers are GPT-4o output, judging your model against them with an LLM judge
measures agreement with 2024-era GPT-4o, not correctness. Fine for harness regression testing;
not evidence of quality.

---

## IL-TUR

`il_tur/` · 484,316 rows · 8 configs / 36 splits · 1.6 GB · HF `Exploration-Lab/IL-TUR`
· ACL 2024. **CC BY-NC-SA 4.0 — non-commercial, share-alike.** Gated via `extra_gated_fields`.

**Does not fit an injection benchmark.** There is no question field in any task; every task is
`document → label`. Only `summ` and `lmt` have free-text targets, and those are summarization
and translation. Its `lsi` task is built on 100 **IPC** sections — repealed July 2024.

Stored as `il_tur/<config>/<split>/*.parquet`. Downloaded from the datasets-server
auto-converted parquet branch (`refs/convert/parquet`) because the gate hides the repo file
tree even from an authorised token — `load_dataset` fails, the parquet branch resolves.

| config | rows | splits |
|---|---|---|
| `bail` | 353,656 | train/dev/test × `_all`, `_specific` |
| `cjpe` | 42,465 | expert 56, single_train/dev, multi_train/dev, test |
| `lsi` | 66,050 | train 42,750 · dev 10,181 · test 13,019 · statutes 100 |
| `pcr` | 8,252 | train/dev/test × `_candidates`, `_queries` |
| `summ` | 7,130 | train 7,030 · test 100 |
| `lmt` | 6,516 | acts 4,036 · cci_faq 1,460 · ip 1,020 |
| `rr` | 100 | `CL_`/`IT_` × train 40, dev 5, test 5 |
| `lner` | 105 | fold_1/2/3, 35 each |

Config names differ from the paper's task labels — note `lmt`, not `l_mt`.
