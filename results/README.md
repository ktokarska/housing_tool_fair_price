# Results data (Evals-tab source)

Static JSON the dashboard's **Evals** tab reads. One bundle per calibrated area plus an index.
Regenerated, never hand-edited:

```
python scripts/calibrate_geo.py --slug <slug> --types D,S,T,F --date 2026-06-19   # per area
python scripts/build_results_data.py --date 2026-06-19                            # aggregate
```

`calibrate_geo.py` writes the authoritative numbers (markdown + JSON) under
`geographies/<slug>/calibration/`; `build_results_data.py` merges those with each area's
name/sub-postcodes into the files here. The numbers are computed blind; nothing is tuned to
hit a verdict.

## Files

- `index.json` — one row per area: `slug`, `name`, `verdict`, `date`, `methods_present`.
  Drives the area picker and the at-a-glance verdict.
- `<slug>.json` — the full per-area payload (below).

## `<slug>.json` schema

| Field | Meaning |
|---|---|
| `slug`, `name`, `sub_postcodes` | Area identity, from `area_definition.md`. |
| `calibration.date`, `methodology_version` | When it was calibrated and under which methodology (version-gated). |
| `calibration.types_covered` | Property types in the sample (`D` detached, `S` semi, `T` terraced, `F` flat). |
| `calibration.methods_present` | Which methods reconciled: `M1` comps, `M2` EPC £/sq ft, `M3` AVM. `M3` appears only once a captured `avm.csv` exists (see `data/snapshots/<date>/AVM_CAPTURE.md`). |
| `calibration.verdict.verdict` | `PASS` / `PASS WITH CORRECTION` / `PASS WITH WIDER RANGES` / `QUARANTINE`. |
| `calibration.verdict.H_pct` | Range half-width the verdict sets (`null` when quarantined). |
| `calibration.verdict.bias_correction_pct` | Bias offset applied (0 unless PASS-WITH-CORRECTION). |
| `calibration.stats.mae` | Mean absolute % error vs real sold prices (H4). |
| `calibration.stats.q80` | 80th-percentile absolute residual; drives range width. |
| `calibration.stats.bias` | Median signed % residual — systematic lean (H5). |
| `calibration.stats.hit_rate` + `wilson` | Share of sold prices inside the range, with 95% Wilson interval (H6). |
| `calibration.stats.high_tier_coverage` | Hit rate within the High-confidence tier. |
| `calibration.counts` | `n_sample`, `n_scored`, `n_refused` (refused = no method available). |
| `calibration.gates[]` | Per-gate result: `gate_id`, `metric`, `score`, `threshold`, `success`, `reason`. Currently the residual-driven release gates H4–H7. |

### Note on the gate set

`gates[]` here holds the **calibration-time** gates (H4–H7). The per-run deterministic gates
(H1 geography, H2/H9 provenance, H3 recall@K, H8 single-label, H10 faithfulness) fire inside a
single valuation and belong to the Valuation tab's per-result payload, not this aggregate. See
`evals_housing_tool/evaluation_design.md` for the full H1–H10 catalog.

## Valuation-tab samples: `valuation_<slug>.json`

One worked subject per area, for the **Valuation** tab. Regenerated, never hand-edited:

```
python scripts/build_valuation_example.py --date 2026-06-19
```

Two blocks per file:

| Block | Meaning |
|---|---|
| `production` | What the public page actually returns today: `run_mode`, `gate` (`NOT_IN_DEMO` / `PROCEED` …), `message`, `reason`, `verdict_shown`. All three demo areas are QUARANTINE, so the gate refuses and `verdict_shown` is `false` — render the honest "not part of the demo" state. |
| `engine_preview` | The same subject with the gate bypassed, so the result block has real numbers: `subject_label` (masked), `asking`, `estimates` (per method), `confidence`, `value_range`, `verdict`, `detail`, `abstain`, `explanation`, and `metrics[]` (the per-run gates H1/H2/H3/H8/H9/H10). |

Honesty constraints baked in:
- `engine_preview.disclaimer` states the result is withheld in production (area is quarantined).
- `engine_preview.explanation_is_placeholder` is `true`: the prose is an offline stand-in (no
  LLM call). Every pound figure is the real deterministic engine output.
- `asking` is the property's real sold price, used to demonstrate the verdict path.
- `metrics[]` are real — e.g. a failing H3 recall@K is shown, not hidden.

## Current state (2026-06-19)

All three calibrated areas — SL6, W13, UB3 — **QUARANTINE** on the two-method (M1+M2) open-data
core. The Evals tab should render this honestly: a quarantined area shows no verdicts. Capturing
AVM data (M3) may or may not change this; the verdict is recomputed blind either way.
