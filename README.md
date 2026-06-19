# Fair Price: a UK house-price estimator that reports its own confidence

A UK property valuation tool built only on open data, designed around one idea: a model that
knows when it does not know. It produces a fair-value estimate and range from past sales, rates
its own confidence, abstains when its methods disagree, and refuses to publish verdicts for any
area it has not proven itself on. The accountability layer is the point of the project, not an
afterthought.

This is a personal, open-source rebuild of a private valuation framework, repurposed as an
eval-first AI engineering portfolio artifact. It is not a commercial valuation service.

## How it values a property

A deterministic ten-step pipeline. Every pound figure is reproducible; a model is used only for
comparable retrieval and for the natural-language explanation.

1. **Geography gate.** Refuses any area without a valid, recent, version-matched calibration.
2. **Data resolution.** Loads subject and candidate rows from a pinned snapshot (HM Land Registry
   Price Paid + EPC register). Every figure traces to a real snapshot row.
3. **Comp retrieval.** Embeds the subject, retrieves nearest sold properties from a local vector
   store, then applies a deterministic rule gate (type, sub-postcode, EPC floor-area band, 18
   months, tenure). Measured by recall@K.
4. **Method 1: comps.** Trend-adjusted median of surviving comparables.
5. **Method 2: EPC.** Floor area times a stock-segment price per square foot.
6. **Method 3: AVM (optional).** A pinned public-AVM snapshot, leakage-controlled. Absent unless
   captured (see `data/snapshots/<date>/AVM_CAPTURE.md`).
7. **Reconciliation.** Spread to confidence to range to a single verdict.
8. **Abstain gate.** INDETERMINATE when the methods disagree (spread above 20% or low confidence).
9. **Explanation.** A grounded rationale, with a deterministic guard that every number in the
   prose matches the computed output.
10. **Output record.** A result object plus standardized metric records.

## The accountability layer

The valuation is only trusted once an area earns it. Calibration runs the framework blind against
properties that actually sold, computes residuals, and applies a fixed verdict rule:
**PASS / PASS WITH CORRECTION / PASS WITH WIDER RANGES / QUARANTINE**. Thresholds are set in
advance and never moved after seeing results. Ten gates (H1 to H10) cover geography routing,
provenance, retrieval quality, accuracy, bias, range coverage, abstain quality, single-label
discipline, square-foot provenance, and explanation faithfulness. See
[`evals_housing_tool/evaluation_design.md`](evals_housing_tool/evaluation_design.md).

### Current state: all three demo areas are quarantined

SL6 (Maidenhead), W13 (West Ealing), and UB3 (Hayes) all **QUARANTINE** on the two-method open
data core. This is the system working as designed, not a defect. Both methods independently sit
at a roughly 10% median-error floor, and the coverage gate needs about 5%. A feasibility audit
([`evals_housing_tool/pass_feasibility.md`](evals_housing_tool/pass_feasibility.md)) confirms
there is no legitimate change that produces a PASS without moving a threshold the methodology
forbids moving. The honest quarantine is the strongest evidence the accountability layer is real.

## Repository layout

| Path | What it holds |
|---|---|
| `src/house_price_tool/` | The engine: methods, retrieval, reconciliation, explanation, and the `eval/` harness |
| `data/raw/`, `data/snapshots/` | Raw open data and the pinned, checksum-verified snapshot |
| `geographies/` | Per-area config, market baselines, and calibration records (markdown + JSON) |
| `evals_housing_tool/` | The evaluation design and the PASS-feasibility audit |
| `results/` | Static JSON for a dashboard: per-area Evals data, Valuation-tab samples, and the M3 sensitivity experiment |
| `scripts/` | Build, fetch, calibrate, and analysis scripts |
| `tests/` | Contract, component, and release-layer tests |

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Rebuild an area baseline, calibrate it, and regenerate the results data:

```bash
python scripts/build_baseline.py --slug sl6-maidenhead --name "Maidenhead (SL6)"
python scripts/calibrate_geo.py  --slug sl6-maidenhead
python scripts/build_results_data.py
```

The pipeline does no network access at run time. Snapshots are pinned and checksum-verified.

## Data sources and attribution

Built only from UK open government data:

- **HM Land Registry Price Paid Data.** Contains HM Land Registry data (C) Crown copyright and
  database right. Licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- **Energy Performance of Buildings Data (England and Wales).** (C) Crown copyright, under the
  Open Government Licence.

No Rightmove, Zoopla, or other commercial or scraped sources are used. Property input is a manual
postcode plus type.

## Known limitations

- Open data carries no bedroom count, so comparables match on EPC floor-area band.
- Geographic matching is by sub-postcode, not a 0.25-mile radius (centroid distance is deferred).
- The automated core is two methods; the AVM third method is optional and manually captured.

These are documented honestly because they are why the demo areas quarantine.

## License

Code is released under the MIT License (see [`LICENSE`](LICENSE)). Open data remains under its own
licences as noted above.
