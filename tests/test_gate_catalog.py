from house_price_tool.eval.residual import ResidualRecord
from house_price_tool.eval.gate_catalog import release_gates, calibration_report


def _r(resid, in_range=True, conf="High", abstained=False, sold=600000):
    mid = round(sold * (1 + resid / 100))
    lo, hi = (sold - 1, sold + 1) if in_range else (mid - 1, mid + 1)
    return ResidualRecord(subject_id="x", sold_price=sold, midpoint=mid,
                          range_lo=lo, range_hi=hi, confidence=conf, abstained=abstained)


def test_release_gates_emit_h4_to_h7():
    recs = [_r(2), _r(-3), _r(4), _r(1)]
    gates = {g.gate_id: g for g in release_gates(recs)}
    assert set(gates) == {"H4", "H5", "H6", "H7"}
    assert gates["H4"].success


def test_calibration_report_has_verdict():
    recs = [_r(2), _r(-3), _r(4), _r(1)]
    report = calibration_report(recs, {"n_sample": 4, "n_scored": 4, "n_refused": 0})
    assert report["verdict"]["verdict"] in {
        "PASS", "PASS WITH CORRECTION", "PASS WITH WIDER RANGES", "QUARANTINE"}
    assert "mae" in report["stats"]
