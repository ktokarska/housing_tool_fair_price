"""Step 7: build the verdict_calc payload from methods and run the single-label gate."""
from __future__ import annotations

from .method_result import MethodEstimate
from .records import MetricRecord
from .verdict_calc import DIRECTIONAL_SET, reconcile


def build_payload(methods: list[MethodEstimate], asking: int | None, *,
                  h_pct: float = 5.0, bias_correction_pct: float = 0.0,
                  dom=None, reductions=0, yoy_pct=None) -> dict:
    method_dicts = {}
    for m in methods:
        d = m.to_reconcile_dict()
        if d is not None:
            method_dicts[m.name] = d
    return {
        "asking": asking if asking is not None else 0,
        "methods": method_dicts,
        "H_pct": h_pct,
        "bias_correction_pct": bias_correction_pct,
        "dom": dom, "reductions": reductions, "yoy_pct": yoy_pct,
    }


def run_reconcile(methods: list[MethodEstimate], asking: int | None,
                  comp_count: int, **kw) -> tuple[dict, MetricRecord]:
    payload = build_payload(methods, asking, **kw)
    result = reconcile(payload)
    result["comp_count"] = comp_count

    verdict = result["verdict"]
    label_ok = verdict in DIRECTIONAL_SET or verdict in {"INDETERMINATE", "NO VERDICT"}
    directional_on_low = (result.get("confidence") in (None, "Low")
                          and verdict in DIRECTIONAL_SET)
    success = label_ok and not directional_on_low
    h8 = MetricRecord(
        metric="single_label", gate_id="H8", score=1.0 if success else 0.0,
        threshold=1.0, success=success,
        reason=f"verdict {verdict!r} at {result.get('confidence')} confidence",
    )
    return result, h8
