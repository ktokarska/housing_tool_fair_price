# Skeptics 10×10: a real integrity eval + improvement loop over the House Price Tool

**Date:** 2026-06-22
**Branch:** `dev_kasia` (copy of production `main`; may merge later if better)
**Owner:** Kasia Tokarska
**Status:** Approved in brainstorm; ready for implementation plan.

## Problem & framing

Run a **real** (not simulated) 10×10 evaluation of the House Price Tool: 10 skeptical grader
personas × 10 real edge-case inputs. Establish a baseline, then loop — fixing real defects — until
every one of the 100 cells is an A+, or until a cell hits a principled wall that integrity forbids
crossing.

The tool is **engineered to refuse**: its own `evals_housing_tool/pass_feasibility.md` proves that
all calibrated areas QUARANTINE on open data and that no legitimate change yields a PASS without
moving a forbidden threshold. Therefore **A+ is defined by integrity, not by confidence**:

> A cell is **A+** when the tool does the *correct* thing for that input — correct gate decision,
> full provenance, honest abstain/quarantine, faithful explanation, valid output contract, and a
> green result for every per-run gate that applies. An honest refusal earns an A+; an
> overconfident verdict fails. Gaming a threshold to force a PASS is *caught and penalized* by the
> Calibration-Statistician and Adversary graders and therefore cannot reach A+.

This makes all-A+ a legitimate, reachable target: "the tool behaves impeccably across its entire
decision surface."

**Allowed loop levers** (user-selected): (1) tool behavior & outputs, (2) eval harness & grader
rubric, (3) methodology thresholds — *permitted but only with documented, skeptic-auditable
justification; never to silently manufacture a PASS*. The 10 inputs are **locked after baseline**
(input-swapping was not selected as a lever) for a clean before/after.

## Where it lives & how it runs

- All code/data execution is in the housing tool repo (only place `run_agent` and the real
  snapshots exist). New work is self-contained under `evals_housing_tool/skeptics_10x10/`.
- **Fully offline & reproducible:** `FakeLLMClient` for prose, pinned checksum-verified snapshots,
  no network, no API key. Reproducibility is itself graded (G9), so determinism is a requirement.
- Engine baseline confirmed: `pytest` = 93/93 green on `dev_kasia`.

## Real interfaces (verified)

`run_agent(*, snapshot_root, geo_dir, geo_slug, sub_postcode, property_type, asking, today,
llm_client, judge_client, run_mode="headless", subject_id=None, skip_gate=False,
avm_filename="avm.csv")` returns **either** a gate-refusal `{"gate": GateDecision, "message": str,
"metrics": [h1]}` **or** a `HouseResult`.

`HouseResult`: `subject_label, geography, methodology_version, snapshot_date, estimates{method→£},
confidence, value_range, verdict, detail, abstain, explanation, metrics[MetricRecord]`.
`MetricRecord`: `metric, gate_id (H1/H2/H3/H8/H9/H10), score, threshold, success, reason`.

`skip_gate=True` = engine-preview (gate bypassed → real numbers even for quarantined areas), the
documented pattern from `scripts/build_valuation_example.py`. Gate decisions: `PROCEED`,
`NOT_IN_DEMO` (headless), `PROMPT_CALIBRATION` (interactive).

## The 10 graders — deterministic, persona-driven scoring functions

Each grader is a **persona** (a documented worldview that fixes which checks matter and how harsh
the bar is) implemented as a pure function `grade(run_output, context) -> {grade, failed_checks[],
evidence[]}`. Deterministic and evidence-citing by design — an LLM judge would be non-reproducible
and fail G9. Letter scale: A+, A, B, C, D, F, derived from explicit pass/fail checks; **A+ = all of
that persona's checks pass with zero caveats**.

| # | Persona | Core obsession (fails the cell when violated) | Anchor |
|---|---|---|---|
| G1 | Provenance Auditor | every £ figure traces to a snapshot row id; zero orphan/estimated values | H2 |
| G2 | Calibration Statistician | a directional PASS the residuals cannot support; *rewards* correct QUARANTINE | H4/H5/H6 |
| G3 | Abstention Hawk | INDETERMINATE exactly when spread>20%/Low; no directional label on Low | H7/H8 |
| G4 | Retrieval Skeptic | recall@K; ≥5 comps or unavailable-flag; trend cap enforced | H3/H4 |
| G5 | Faithfulness Inquisitor | every number in prose == reconcile output; placeholder honestly flagged | H10 |
| G6 | Gate Lawyer | correct route + exact message for uncalibrated/expired/version-mismatch per run mode | H1 |
| G7 | Schema/Contract Pedant | schema-valid output; metric-record shape; headless contract present | output |
| G8 | Adversary / Red-teamer | self-contradiction; engine_preview leaking into a withheld production result | cross-cut |
| G9 | Reproducibility Referee | same input → byte-identical output across repeated runs | pass@k |
| G10 | Honest-Communication Critic | overconfidence / false precision; unclear "we withhold and why" | ethos |

Each persona also gets a short character sheet in `personas.md` (name, background, what makes them
skeptical, what earns an A+ from them, what they refuse to forgive).

## The 10 real inputs (mixed realistic — the gate's whole decision surface)

Concrete subjects/sub-postcodes are **discovered from the real pinned snapshot** at build time, not
invented. Each input spec records: geo, sub_postcode, type, subject_id, run_mode, skip_gate, and
any fault injection (against a *copy* of the snapshot, never the pinned original).

| ID | Stresses | Expected correct behavior (what earns A+) |
|----|----------|-------------------------------------------|
| I1 | SL6 in-area, gate bypassed | real engine-preview numbers, all per-run gates green |
| I2 | W13 high method spread | INDETERMINATE / abstain, honestly explained |
| I3 | UB3 coverage-quarantine subject | engine-preview numbers; honest low-confidence framing |
| I4 | SL6 production run (gate ON) | QUARANTINE withhold, correct refusal message |
| I5 | Uncalibrated area, headless | `NOT_IN_DEMO` "Not part of the demo, calibration needed" |
| I6 | Expired (>90d) calibration | refusal (calibration stale) |
| I7 | Methodology version mismatch | refusal (version-gated) |
| I8 | Subject with no EPC | Method 2 correctly *unavailable* (no fabricated sq ft) |
| I9 | Orphan / malformed snapshot row | fault-injection halt; provenance gate catches it |
| I10 | Exact 20% spread boundary | abstain-boundary behavior correct & consistent |

## Components (built test-first)

1. `inputs.py` — the 10 locked `InputSpec`s + an executor that maps each to a real `run_agent` call
   (gate on/off; for I6/I7/I9 a temporary corrupted snapshot/geography copy in a tmp dir).
2. `run_10x10.py` — executes the real pipeline per input; writes the full output (HouseResult or
   gate-refusal) + run metadata to `runs/<id>.json`. Nothing fabricated.
3. `graders.py` — the 10 persona rubrics + a `LETTER` derivation shared across them.
4. `grade_10x10.py` — builds the 100-cell matrix → `grades/round_<N>.json` and a readable
   `report_round_<N>.md` (10×10 table + per-cell evidence for every sub-A+ cell).
5. `personas.md` — the 10 character sheets.
6. `loop.md` — the round log: baseline matrix → per-round root-cause + fix (lever used) → final.

## The loop (supervised, bounded)

Round 0 = baseline. Each round: read every sub-A+ cell's cited evidence → `systematic-debugging`
to root-cause → smallest **honest** fix via an allowed lever → re-run the full 10×10. Repeat until
all 100 cells are A+ **or** a cell hits a principled wall (only path to A+ is gaming → stop and
report; under integrity grading that is the *correct* terminal state). Soft cap ~8 rounds before
checking in. Each threshold edit, if any, is logged prominently for skeptic audit.

## Testing & verification

- Harness code is built test-first (TDD): grader unit tests (a known-bad output must fail the
  matching grader — mutation-style), input-executor tests, matrix-shape tests.
- `verification-before-completion` before any "all A+" claim: the claim must show the actual
  `report_round_N.md` matrix, not an assertion.
- The existing 93-test suite must stay green after every tool-side fix.

## Out of scope

The HTML dashboard / `ktokarska.github.io` site (a later surface). No live scraping. No network.
No moving a threshold without a written, auditable justification in `loop.md`.
