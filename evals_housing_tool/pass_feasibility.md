# Can any area legitimately reach PASS? — a feasibility audit

**Date:** 2026-06-19. **Question:** all three calibrated areas (SL6, W13, UB3) QUARANTINE. Is
that a real result, or an artifact of how the harness is wired — and is there a legitimate change
that earns a PASS? **Answer: the quarantine is real and correct. There is no legitimate fix.**

## 1. Where the error comes from (per-method decomposition)

`scripts/diagnose_methods.py` runs each calibration sample and records every method's own
estimate vs the held-out sold price (median absolute % error / q80):

| Area | M1 comps | M2 EPC £/sqft | Reconciled | Quarantined by |
|---|---|---|---|---|
| SL6 | 12.2% / 26.0% | 11.2% / 22.5% | 10.3% / 23.0% | MAE > 10% |
| UB3 | 10.5% / 23.3% | 12.3% / 26.6% | 10.0% / 25.1% | coverage only (Wilson 0.36 < 0.50) |
| W13 | 13.4% / 26.8% | 10.5% / 23.9% | 10.9% / 25.9% | MAE > 10% |

Both methods independently sit at a **~10–13% median-error floor**, and which is worse flips by
area. Reconciliation already extracts what is available (~10%, better than either alone). This is
a signal-quality floor in the open data (no bedrooms, sub-postcode-not-radius matching), not one
fixable method. Better comp matching touches only M1 and cannot halve a floor both methods share.

## 2. The coverage-rule investigation

The one place a PASS could plausibly hide: UB3 is quarantined *only* by the coverage rule
(Wilson lower bound < 0.50), and that hit rate is measured on the engine's default **±5%** ranges.
Hypothesis: coverage should be measured at the *widened* range (H = q80 ≈ 23%), in which case UB3
might reach PASS-WITH-CORRECTION.

**The hypothesis is wrong, confirmed against the origin protocol:**

1. **The ported `verdict_calc.py` is byte-identical to the origin** (`diff` on logic lines: no
   differences). Range widths are faithful: High → ±H (5%), Medium → method spread, Low → full
   spread + INDETERMINATE.
2. **The origin `calibration_protocol.md` Step 3** defines hit/miss as "was the actual sold price
   inside *the framework's fair-value range*" — the range produced during the blind run, at the
   default H = 5%. The calibration passes no geography-specific H, so it runs at 5%, exactly as
   specified.
3. **Step 4 rows 4–5 set H = max(5%, q80) for *future sweeps***, not for re-measuring calibration
   coverage. Row 2 (Wilson < 0.50 → QUARANTINE) is evaluated *before* any widening. So the
   widening remedy is not, and is not meant to be, a calibration rescue.

UB3's ±5% range covers the true price ~37% of the time — genuinely indistinguishable from chance
given ~10% median error. The rule is correctly applied; being one rule away does not make the
rule wrong.

## 3. Conclusion

There is **no legitimate code change that produces a PASS** without moving a threshold the
methodology explicitly forbids moving ("calibration is a hold-out test; framework is fixed
beforehand"). An open-data PASS would require a fundamentally better signal — real bedroom counts
and 0.25-mile centroid matching to cut the residual spread, or genuinely independent third-method
data — none of which open data provides today.

The quarantine stands. The system measured itself against ~4,300 real sales, found it cannot meet
its own bars, and refuses to publish directional verdicts. That refusal — audited against the
source protocol and left in place — is the artifact's strongest evidence of accountability.

*Reproduce:* `python scripts/diagnose_methods.py --date 2026-06-19`
