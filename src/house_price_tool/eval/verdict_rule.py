"""Calibration verdict rule, ported verbatim from calibration_protocol.md Step 4."""
from __future__ import annotations


def calibration_verdict(*, mae, bias, hit_rate, wilson_lo, high_tier_coverage,
                        q80) -> dict:
    H_wide = max(5.0, float(q80))
    if mae > 10:
        return {"verdict": "QUARANTINE", "H_pct": None, "bias_correction_pct": 0.0}
    if wilson_lo < 0.50:
        return {"verdict": "QUARANTINE", "H_pct": None, "bias_correction_pct": 0.0}
    if 5 <= mae <= 10 and abs(bias) > 2:
        return {"verdict": "PASS WITH CORRECTION", "H_pct": 5.0,
                "bias_correction_pct": -bias}
    if 5 <= mae <= 10 and abs(bias) <= 2 and hit_rate < 0.70:
        return {"verdict": "PASS WITH WIDER RANGES", "H_pct": H_wide,
                "bias_correction_pct": 0.0}
    if mae < 5 and abs(bias) <= 2 and hit_rate > 0.70 and high_tier_coverage >= 0.70:
        return {"verdict": "PASS", "H_pct": 5.0, "bias_correction_pct": 0.0}
    return {"verdict": "PASS WITH WIDER RANGES", "H_pct": H_wide,
            "bias_correction_pct": 0.0}
