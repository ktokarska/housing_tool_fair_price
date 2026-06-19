# House Price Tool: Evaluation Design

**Date:** 2026-06-19
**Status:** Complete draft. All four sections locked in brainstorm, pending user review.
**Owner:** Kasia Tokarska
**Scope:** The valuation agent and its architecture. The HTML dashboard is a later step and is out of scope here.

This document is the evaluation design for the House Price Tool. It states, for every step of the agent, one headline evaluation metric, its grader type, and a pass bar fixed in advance. It adapts the structure of a separate KYC evaluation framework (used only as a structural reference, not reused) to a UK property valuation pipeline that runs on open data.

This evaluation design and the housing harness live under `evals_housing_tool/`.

---

## Locked design decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Architecture shape | Deterministic valuation core, with ML only at comp retrieval and at the LLM-judged explanation. Every pound figure is deterministic and reproducible. |
| 2 | Method 3 / AVM | Two-method automated core (M1 comps + M2 EPC sq ft). The public AVM is captured manually for the calibration sample, pinned as a snapshot, used as an optional third method when present and as a baseline in the eval report. No live scraping ships. |
| 3 | Vector store role | Augment rather than replace. The vector store retrieves candidate sold properties; the deterministic match rules then gate them. Measured by recall@K. |
| 4 | Calibration thresholds | The origin calibration protocol is carried verbatim (QUARANTINE / PASS-WITH-CORRECTION / PASS-WITH-WIDER-RANGES / PASS, MAE bands, bias rule, hit-rate bar, H = max(5%, q80), Wilson interval, per-tier coverage). The Method 3 leakage test applies to the captured AVM snapshot. |
| 5 | Geographies | Pipeline is config-driven for any area. Demo offers two: SL6 (Maidenhead) and W13 (West Ealing). W5 (Ealing) deferred. W13 and W5 baselines are built from open data. |

**Core principle (carried from the reference framework):** grade what the agent produced, not the path it took, and prefer a deterministic check wherever one is possible. A model judge is used only for prose quality.

**No-fabrication rule (carried from the origin methodology):** every comp, square-foot figure, and AVM value carries a reference to the real snapshot row it came from. A claim with no source row does not survive to the output.

---

## Section 1: Pipeline architecture and module boundaries

The agent is a linear pipeline of ten steps. Each step is a separate module with one job, one input contract, and one output contract, so it can be tested alone.

### Data flow

```
postcode + type
   |
   v
[1] Input & geography gate    is this area calibrated, valid, version-matched?
   |                             headless: "Not part of the demo, calibration needed"
   |                             interactive: "Run calibration now? [y/n]"
   v
[2] Data resolution           pull subject + candidate rows from the PINNED
   |                            snapshot (Land Registry sold prices, EPC sq ft)
   v
[3] Comp retrieval (ML)        embed subject -> vector store top-K nearest sold
   |                            -> deterministic rule gate (type / sub-postcode / floor-area band / 18mo / tenure)
   v
[4] Method 1                   trend-adjusted median of surviving comps
   |
   v
[5] Method 2                   EPC sq ft x stock-segment price/sq ft  (unavailable if no EPC)
   |
   v
[6] Method 3 (optional)        pinned AVM snapshot, leakage-controlled  (calibration/baseline)
   |
   v
[7] Reconciliation             verdict_calc.py: spread -> confidence -> range -> one verdict
   |
   v
[8] Abstain gate               spread >20% or Low confidence -> INDETERMINATE
   |
   v
[9] Explanation (LLM)          natural-language rationale, grounded in the computed numbers
   |
   v
[10] Output record             result object + standardized metric records
```

### Run modes (Step 1 behaviour)

The geography gate behaves differently by run mode, mirroring the reference framework's interactive-versus-headless split:

- **Demo / headless:** an uncalibrated area returns "Not part of the demo, calibration needed" and stops. No verdict is produced.
- **Terminal / interactive:** an uncalibrated area prompts the operator, "This area is not calibrated. Run calibration now? [y/n]", and on yes starts the calibration procedure.

### Modules

| Module | Responsibility | Depends on |
|---|---|---|
| `geography/` | Per-area config: baseline (price/sq ft, YoY, median sq ft per cell), calibration status, area definition | pinned data |
| `data/` | Loads the pinned snapshot; exposes sold rows + EPC rows; no network at run time | snapshot files + seeds |
| `retrieval/` | Builds the structured feature embedding, the vector store, and the rule gate | `data/` |
| `methods/` | Three independent estimators (M1, M2, M3); each returns estimate + flags + source references | `retrieval/`, `data/` |
| `reconcile/` | Ported `verdict_calc.py`: spread, confidence, range, single verdict, abstain | `methods/` |
| `explain/` | LLM rationale, constrained to the numbers reconcile produced | `reconcile/` |
| `eval/` | Offline harness: graders, gate catalog, calibration, reliability (Section 3) | all of the above |

### Embedding choice

The vector at step 3 is a **structured feature vector**: normalised numeric features (postcode-centroid location, floor area, build year) plus encoded categoricals (type, tenure). Similarity is interpretable, recall@K is clean to measure, and it cannot drift on free text. The index is a local FAISS or Chroma store.

**Data constraint on the rule gate (recorded for honesty).** The origin framework matches comparables on bedroom count. HM Land Registry Price Paid and the EPC register do not carry bedroom count, so the public build matches on EPC **floor-area band** instead. This is forced by the open-data sources and aligns the comp criterion with Method 2, which already values on floor area. Precise 0.25-mile radius matching needs postcode-centroid coordinates (the open ONS Postcode Directory); until that is added, the geographic criterion is the same sub-postcode unit, with centroid distance as a later refinement.

---

## Section 2: Per-step control table (one eval metric per step)

Each step states its goal, the control that runs at that step, the grader type, and a pass bar fixed in advance.

| # | Step | Goal | Headline eval / control | Grader | Pass bar (fixed before results) |
|---|---|---|---|---|---|
| 1 | Input & geography gate | Validate postcode+type; confirm calibration exists, is <90 days, version-matched, and covers the subject's type | Geography gate correctness | Deterministic | 100%: zero verdicts on an uncalibrated/expired/version-mismatched area; uncalibrated routes to the not-in-demo message (headless) or the calibration prompt (interactive) |
| 2 | Data resolution | Load subject + candidate rows from the pinned snapshot (Land Registry, EPC) | Source provenance + snapshot integrity | Deterministic | 100%: every figure traces to a real snapshot row; snapshot checksum matches the pinned manifest; zero orphan values |
| 3 | Comp retrieval (ML) | Embed subject, retrieve top-K nearest sold, then rule-gate | recall@K of rule-valid comps | Deterministic (vs rule-defined comp set) | recall@20 >= 0.95 |
| 4 | Method 1 | Trend-adjusted median of surviving comps | Comp-set sufficiency + trend cap | Deterministic | 100%: >=5 comps or method flagged unavailable; +/-10% trend cap enforced. Accuracy itself rolls into calibration MAE |
| 5 | Method 2 | EPC sq ft x stock-segment price/sq ft | Sq ft provenance (no estimation) | Deterministic | 100%: zero M2 estimates on an sq ft without an EPC source row; segment match present or method unavailable |
| 6 | Method 3 (optional) | Pinned AVM snapshot, leakage-controlled | M3 leakage test + live-listing exclusion | Deterministic | Leakage comparison recorded; with/without-M3 ablation reported until two clean calibrations; contaminated AVM excluded from spread |
| 7 | Reconciliation | `verdict_calc.py`: spread -> confidence -> range -> one verdict | Single-label determinism | Deterministic | 100%: exactly one label from the closed set; zero directional labels on Low-confidence rows |
| 8 | Abstain gate | INDETERMINATE when spread >20% or Low confidence | Abstain precision & recall (confusion matrix) | Deterministic (calibration-time) | precision >= 0.80, recall >= 0.80 |
| 9 | Explanation (LLM) | Natural-language rationale grounded in the computed numbers | LLM-as-judge faithfulness + number-match guard | Model judge (calibrated) + deterministic | Faithfulness mean >= 4/5, none <3; every number in the prose matches the reconcile output exactly (100%) |
| 10 | Output record | Emit result object + standardized metric records | Output schema/contract | Deterministic | 100% schema-valid; headless result contract present |

### Thresholds the origin framework did not specify

The origin protocol sets MAE, bias, and hit-rate bars but does not specify numeric bars for **recall@K** (the vector step is new) or for **abstain precision/recall** (the spec lists them as metrics but fixes no number). The values below are fixed in advance for this build:

- recall@20 >= 0.95
- abstain precision >= 0.80, abstain recall >= 0.80

These are locked before any results are produced and do not move after seeing residuals.

---

## Worked examples, step by step

Examples use the SL6 worked subject from the origin methodology (a 3-bed semi at SL6 7AB, 1,180 sq ft EPC-verified, asking 650,000) and plausible W13 figures. All numbers are illustrative.

### Step 1: Input & geography gate

- **Pass:** input "SL6 7AB, semi-detached". A calibration file dated within 90 days, methodology version v2.1, with semi-detached represented in the sample, exists. Gate passes, run proceeds.
- **Block (headless):** input "TW8 0XX, flat" (Brentford, not in the demo). Returns "Not part of the demo, calibration needed" and stops.
- **Block (interactive):** same input in the terminal prints "Area TW8 not calibrated. Run calibration now? [y/n]".
- **Metric in action:** of N test inputs spanning calibrated, uncalibrated, expired, and version-mismatched areas, 100% are routed correctly. Any single verdict produced for an uncalibrated area is a fail.

### Step 2: Data resolution

- **Pass:** subject resolves to comp row `PP-2024-00831` (Land Registry: 635,000, sold 2024-09) and EPC row `EPC-SL6-1180` (1,180 sq ft). Each loaded value carries its snapshot row id. The snapshot manifest checksum matches the pinned value.
- **Failure caught:** a candidate comp with no matching snapshot row id is flagged as an orphan and the run halts rather than valuing on an unsourced figure.
- **Metric in action:** 100% of loaded figures trace to a snapshot row, and the checksum matches. One orphan value is a fail.

### Step 3: Comp retrieval (recall@K)

- **Setup:** for the SL6 semi (about 1,180 sq ft), the rule-valid comp set (computed deterministically over the full snapshot: same type, same sub-postcode, EPC floor-area band match, sold within 18 months, freehold) contains 18 sold properties.
- **Pass:** the vector store's top-20 nearest contains all 18 rule-valid comps (plus 2 near-misses the rule gate then drops). recall@20 = 18/18 = 1.00 >= 0.95.
- **Fail:** the top-20 contains only 16 of the 18. recall@20 = 0.89 < 0.95. Retrieval needs tuning before the build proceeds; the valuation is not trusted on a comp set the retriever cannot reliably assemble.

### Step 4: Method 1

- **Pass:** 6 comps survive the rule gate; trend-adjusted median is 635,000; comp count 6 >= 5 so the sufficiency check passes. One comp's raw trend adjustment computes to +12% and is capped at +10%, adding the weakness flag "trend-capped comp".
- **Unavailable path:** after widening (next floor-area band, then adjacent sub-postcode, then window 24 months) only 4 comps remain. Method 1 is flagged unavailable and the run proceeds on Methods 2 and 3.
- **Metric in action:** the deterministic bar (>=5 comps or unavailable-flag set; trend cap enforced) passes per run. The point accuracy of 635,000 against the actual sold price is measured at calibration and rolls into MAE.

### Step 5: Method 2

- **Pass:** EPC row `EPC-SL6-1180` gives 1,180 sq ft. The SL6 7 semi-specific median is 555 per sq ft. 1,180 x 555 = 655,000. The provenance check confirms the sq ft came from an EPC row.
- **Unavailable path:** the subject postcode has no EPC certificate. Method 2 is unavailable. No floor area is estimated; confidence downgrades and abstain may trigger. The provenance check passes because the method correctly refused.
- **Failure caught:** any code path that produced a floor area such as "typical 3-bed = 1,150 sq ft" without an EPC source row fails the provenance check, which must show zero such occurrences.

### Step 6: Method 3 (optional)

- **Pass:** the pinned AVM snapshot for the SL6 7AB proxy UPRN is 620,000, captured 2026-06-01. The leakage test compares AVM accuracy on recent sales (MAE 4.1%) against sales from 12+ months ago (MAE 4.4%); no sharp improvement, so no leakage signature is recorded. The AVM page did not display the subject's asking price, so M3 enters the spread.
- **Exclusion path:** the AVM page displays the subject's live listing. M3 is recorded as a displayed reference and excluded from the spread, confidence, and range. Reconciliation runs on two methods.

### Step 7: Reconciliation

- **Pass:** M1 = 635,000, M2 = 655,000, M3 = 620,000. Spread = (655,000 - 620,000) / 635,000 = 5.5%, which gives High confidence and a range of 604,000 to 667,000 (median +/- 5%). The 650,000 asking sits inside the range, in the upper third, so the verdict is exactly one label: "FAIR (asking sits at upper third of range)".
- **Failure caught:** if confidence were Low and any prose carried a directional word (OVERPRICED, UNDERPRICED, or a "strict:" variant), it fails the absolute Step D rule. The count of such breaches must be zero.

### Step 8: Abstain gate

- **Pass (warranted abstain):** a W13 subject has M1 = 480,000 and M2 = 590,000, a spread of about 22% (> 20%), so the verdict is INDETERMINATE. At calibration the actual sold price was 585,000, and a directional verdict would have been a miss greater than 10%. Abstaining was warranted, so this counts as a true positive for the abstain decision.
- **Metric in action:** across the calibration sample, abstain precision = warranted abstains / all abstains, and abstain recall = warranted abstains caught / all cases that should have abstained. Both must reach 0.80. The confusion matrix is the answer-versus-abstain evidence artifact.

### Step 9: Explanation (LLM judge)

- **Pass:** reconcile output is range 604,000 to 667,000, High confidence, FAIR upper third, comps n=6. The LLM writes: "Six recent sales of comparable semis support a fair value of roughly 604,000 to 667,000. The 650,000 asking sits in the upper third of that range, so it is fair but toward the top." The judge scores faithfulness 5/5 (every claim supported, no invented comp). The deterministic number-match guard extracts 604,000, 667,000, 650,000, and n=6 from the prose and confirms each matches the reconcile output.
- **Failure caught:** the LLM writes "seven comparable sales" when n=6, or calls a FAIR verdict "a bargain". The number-match guard fails (7 does not equal 6) and blocks the output deterministically; the judge also scores faithfulness below 3.
- **Judge setup (carried from the reference framework):** the judge is pinned (claude-sonnet-4-6, temperature 0), given explicit ordered evaluation steps, one isolated call per dimension, and must reach at least 85% agreement with human labels on a calibration set before its scores count. It may return Unknown rather than guess.

### Step 10: Output record

- **Standardized metric record** (one shape for every gate, deterministic or judged):

```json
{ "metric": "recall@K", "gate_id": "H3", "score": 1.0,
  "threshold": 0.95, "success": true,
  "reason": "18/18 rule-valid comps retrieved in top-20" }
```

- `score` is normalised 0.0 to 1.0; deterministic gates emit 1.0 or 0.0; `reason` always states the concrete result.
- **Metric in action:** the result object validates against the schema and the headless result contract is present. 100% schema-valid is the bar.

---

## Section 3: Offline eval layer

Sections 1 and 2 protect a single run. This layer protects the agent over time: it answers "did this change make the agent worse?" before the change ships. It is adapted from the reference framework's offline harness.

### The three-layer test pyramid

| Layer | When | Cost | What it checks |
|---|---|---|---|
| Layer 1: contract | Every change | Zero tokens, no network, under a minute | Output-format schema, the standardized metric record shape, the headless result contract, and fault injection (a malformed snapshot row must halt, an orphan comp must be caught) |
| Layer 2: component | On demand | Small | Each module against fixtures: the rule gate, `verdict_calc.py` reconciliation cases, the abstain boundary at exactly 20% spread, recall@K on a frozen mini-index |
| Layer 3: release | Before any release or methodology change | Larger | The full gate catalog against the frozen calibration set for each geography |

### The gate catalog (H1-H10)

The housing analog of the reference C1-C9. These run at Layer 3 against the held-out sold properties.

| Gate | Meaning | Method | Bar |
|---|---|---|---|
| H1 | Geography-gate correctness | deterministic routing test | 100% |
| H2 | Source provenance / no fabrication | every figure traces to a snapshot row | 100% |
| H3 | Comp retrieval quality | recall@20 vs rule-valid set | >= 0.95 |
| H4 | Valuation accuracy | MAE of midpoint vs actual sold | Within the area's calibration band (PASS < 5%, PASS-WITH-WIDER-RANGES < 10%); regression past the band fails the gate and forces recalibration |
| H5 | Bias | median signed residual | within +/-2% |
| H6 | Range coverage / hit rate | actual sold inside predicted range, Wilson interval | >= 70% directional tier, High-tier >= 70% |
| H7 | Abstain quality | precision and recall of the abstain decision | >= 0.80 each |
| H8 | Single-label / Step D | one verdict from the closed set; no directional label on Low | 100% |
| H9 | Sq ft provenance | no Method 2 estimate without an EPC row | 100% |
| H10 | Explanation faithfulness | calibrated LLM judge + number-match guard | mean >= 4, none < 3; numbers match 100% |

The mapping is one gate per pipeline step, which keeps the audit trail one-to-one with Section 2.

### Grader validation (mutation testing)

A grader that passes everything is worthless. `mutation_check` seeds known-bad changes into a golden run (a fabricated comp, a number-drifted explanation, an sq ft with no EPC source, a verdict that should have abstained) and every one must fail the matching gate. This proves the harness is discriminative and cannot be bypassed.

### Multi-trial reliability (pass@k)

The deterministic core is reproducible by construction, so reliability testing targets the two stochastic surfaces only: the embedding/retrieval step and the LLM explanation. Repeated runs against the same subject report, per field, the per-trial success rate and a flaky flag. A field that passes one run and fails the next is a defect.

### Continuous execution

Layer 1 runs on every change (zero token, no network). Layer 3 runs before any release or any change to the methodology or `verdict_calc.py`, matching the version-gating rule.

---

## Section 4: Calibration (the hard gate, carried verbatim per geography)

Calibration is what earns an area the right to show verdicts. It is the origin protocol ported unchanged, run once per geography, blind, before any directional output. Each of SL6 and W13 must pass on its own.

### Procedure (per geography)

1. **Build the hold-out sample.** Pull N>=25 (hard floor 10) properties that actually sold in the area in the past 6 months, from Land Registry. Stratify across property types and at least 3 sub-postcodes, spread across the full 6-month window. Do not filter on method availability: data-thin properties count as the refusals they are in production.
2. **Run blind, under production conditions.** Blind to the sold price (revealed only at residual time) and blind to the full address (masked, so Method 2 uses only the EPC path the public build actually has). This makes the measured accuracy the deployed system's accuracy.
3. **Method 3 leakage test on the AVM snapshot.** Compare AVM accuracy on recent sales against sales from 12+ months ago. A sharp improvement on recent sales is leakage evidence. Until two consecutive clean calibrations, report results both with and without M3, treating the with-M3 figures as a lower bound on error.
4. **Compute residuals,** reported overall and per confidence tier: MAE, q80 (drives range width), bias (median signed residual), and hit rate with a 95% Wilson interval. Low/INDETERMINATE rows are scored as refusal correctness and excluded from the headline hit rate.
5. **Apply the verdict rule** (first matching row wins):

| Order | MAE | Bias | Hit rate | Verdict |
|---|---|---|---|---|
| 1 | >10% | any | any | **QUARANTINE**: no verdicts for this area |
| 2 | any | any | Wilson lower bound <50% | **QUARANTINE**: coverage indistinguishable from chance |
| 3 | 5-10% | >+/-2% | any | **PASS WITH CORRECTION**: apply the documented bias offset |
| 4 | 5-10% | within +/-2% | <70% | **PASS WITH WIDER RANGES**: H = max(5%, q80) |
| 5 | <5% | within +/-2% | >70% and High-tier >=70% | **PASS**: valid, H = 5% |
| Fallback | any other | | | **PASS WITH WIDER RANGES** (H can only widen, never narrow) |

6. **Document failure modes.** Any miss over 10% gets a short post-mortem (which method was furthest off, what data was missing) accumulating as institutional memory.

### Hard structural rules (carried verbatim)

- No listings output for an area without a valid calibration file dated within 90 days, under the matching methodology version.
- Calibration is version-gated: a methodology or `verdict_calc.py` change invalidates every area's calibration until re-run.
- A QUARANTINE is shown honestly. In the demo, a quarantined area is not offered; in the terminal, it reports the quarantine and refuses verdicts.

This is the centrepiece. It is the reason the artifact reads as "I run AI under accountability" rather than "I made a model".
