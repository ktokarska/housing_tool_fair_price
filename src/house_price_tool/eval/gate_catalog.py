"""Release-layer gate catalog (H4 to H7) and the calibration report bundle."""
from __future__ import annotations

from ..records import MetricRecord
from .abstain_metrics import abstain_gate
from .metrics_calc import bias, hit_rate, mae, q80, tier_coverage
from .verdict_rule import calibration_verdict


def release_gates(records) -> list[MetricRecord]:
    m, b = mae(records), bias(records)
    rate, lo, _ = hit_rate(records)
    h4 = MetricRecord(metric="mae", gate_id="H4", score=round(m, 3), threshold=10.0,
                      success=m < 10, reason=f"MAE {m:.2f}% (PASS band <5, wider <10)")
    h5 = MetricRecord(metric="bias", gate_id="H5", score=round(b, 3), threshold=2.0,
                      success=abs(b) <= 2, reason=f"bias {b:+.2f}%")
    h6 = MetricRecord(metric="hit_rate", gate_id="H6", score=round(rate, 3), threshold=0.70,
                      success=rate >= 0.70 and lo >= 0.50,
                      reason=f"hit rate {rate:.2f}, Wilson lower {lo:.2f}")
    h7 = abstain_gate(records)
    return [h4, h5, h6, h7]


def calibration_report(records, counts) -> dict:
    rate, lo, hi = hit_rate(records)
    stats = {"mae": round(mae(records), 3), "q80": round(q80(records), 3),
             "bias": round(bias(records), 3), "hit_rate": round(rate, 3),
             "wilson": [round(lo, 3), round(hi, 3)],
             "high_tier_coverage": round(tier_coverage(records, "High"), 3)}
    verdict = calibration_verdict(
        mae=stats["mae"], bias=stats["bias"], hit_rate=stats["hit_rate"],
        wilson_lo=lo, high_tier_coverage=stats["high_tier_coverage"], q80=stats["q80"])
    return {"counts": counts, "stats": stats, "verdict": verdict,
            "gates": [g.to_dict() for g in release_gates(records)]}
