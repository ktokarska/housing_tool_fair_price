# M3 sensitivity experiment — does a third method move the verdict?

**Question.** All three areas QUARANTINE on the two-method (M1 comps + M2 EPC £/sq ft) core.
Would adding a third method rescue any of them?

**Method.** Real AVM data cannot be captured (no open per-property source; commercial AVMs are
excluded by the project and ToS). So this is a **PROXY** third method — *not a real AVM* — built
only from the open data already in the snapshot, used to bound the effect:

- Model: OLS of `log(price)` on `log(floor_area) + property type + sub-postcode + month trend`.
- Leakage control: exact leave-one-out (PRESS `y - e/(1-h)`), so no property's prediction uses
  its own sold price. Duan smearing corrects the log retransformation.
- Written to `avm_proxy.csv` (never `avm.csv`); every row tagged `PROXY:` in `source_url`.
- Fed through the unchanged reconciliation as M3, re-running each calibration. The canonical
  quarantine records are **not** touched.

Reproduce:
```
python scripts/run_proxy_sensitivity.py --date 2026-06-19
```

## Result: no area changes verdict

| Area | Proxy med-APE | MAE (M1+M2 → +proxy) | Hit rate (→) | Verdict |
|---|---|---|---|---|
| SL6 | 10.8% | 10.33% → 10.64% | 0.33 → 0.33 | QUARANTINE → **QUARANTINE** |
| W13 | 11.7% | 10.86% → 10.34% | 0.33 → 0.30 | QUARANTINE → **QUARANTINE** |
| UB3 | 17.9% | 10.00% → 10.26% | 0.41 → 0.37 | QUARANTINE → **QUARANTINE** |

The proxy is a competitive estimator on the harness's own basis (the harness "MAE" is a
**median**; the proxy's median APE ≈ 10.8% for SL6, on par with M1/M2). Its **mean** APE is much
higher (e.g. 36.8% for SL6) because a simple hedonic cannot price atypical/high-value homes — a
fat right tail the median absorbs.

## Why a third method doesn't help here

1. **Correlation.** Built from the same Land Registry + EPC data, the proxy is correlated with
   M1/M2, so the median-of-three barely shifts the midpoint. MAE moves by fractions of a point —
   slightly better for W13, slightly worse for SL6/UB3. Noise, not signal.
2. **Coverage is a range-width problem, not a method-count problem.** Hit rate is set by the
   ±5% range the engine quotes during calibration against a residual spread of q80 ≈ 23–26%. No
   additional *point* estimate widens the range, so coverage stays ~chance and even dips slightly.
3. **Shared accuracy floor.** All three methods inherit the same ~10% open-data accuracy limit
   (no bedrooms, sub-postcode-not-radius matching), so the ensemble can't break below it.

## What this means

The quarantine is **not** caused by having too few methods. For an *open-data* third method the
effect is essentially nil. A genuinely **independent** commercial AVM (less correlated) might
move MAE more — this proxy is a lower bound — but even a perfect third point-estimate cannot fix
the coverage failure, which is structural to range sizing and the open-data signal. The honest
levers remain: capture real independent AVM data, or add the deferred data (bedroom count,
0.25-mile centroid matching) to cut the residual spread.

*Files:* `proxy_<slug>.json` (per-area before/after), `summary.json` (the table above).
*Note:* `avm_proxy.csv` under each snapshot area is a generated PROXY artifact, never real AVM
data, and never the `avm.csv` the real-capture rails use.
