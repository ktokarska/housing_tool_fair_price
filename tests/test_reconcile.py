from house_price_tool.reconcile import build_payload, run_reconcile
from house_price_tool.method_result import MethodEstimate


def _m(name, est, available=True):
    return MethodEstimate(name=name, estimate=est, available=available)


def test_build_payload_drops_unavailable():
    payload = build_payload([_m("m1", 635000), _m("m2", None, available=False),
                             _m("m3", 620000)], asking=650000)
    assert set(payload["methods"]) == {"m1", "m3"}


def test_run_reconcile_directional_passes_h8():
    methods = [_m("m1", 635000), _m("m2", 655000), _m("m3", 620000)]
    result, h8 = run_reconcile(methods, asking=650000, comp_count=6)
    assert result["confidence"] == "High" and result["comp_count"] == 6
    assert h8.gate_id == "H8" and h8.success


def test_run_reconcile_single_method_is_indeterminate_and_passes_h8():
    result, h8 = run_reconcile([_m("m2", 588000)], asking=545000, comp_count=0)
    assert result["verdict"] == "INDETERMINATE" and h8.success
