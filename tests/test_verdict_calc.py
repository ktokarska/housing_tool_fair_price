from house_price_tool.verdict_calc import reconcile, self_test, DIRECTIONAL_SET


def test_origin_self_test_passes():
    self_test()


def test_worked_example_high_confidence():
    r = reconcile({"asking": 650000, "methods": {
        "m1": {"estimate": 635000}, "m2": {"estimate": 655000},
        "m3": {"estimate": 620000}}})
    assert r["confidence"] == "High"
    assert r["range"] == [603250, 666750]
    assert r["verdict"] in DIRECTIONAL_SET
    assert "upper third" in r["detail"]


def test_low_confidence_is_indeterminate():
    r = reconcile({"asking": 545000, "methods": {"m2": {"estimate": 588000}}})
    assert r["verdict"] == "INDETERMINATE"
