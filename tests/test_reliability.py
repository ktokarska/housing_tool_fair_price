from house_price_tool.eval.reliability import pass_at_k, reliability_record


def test_all_pass_not_flaky():
    out = pass_at_k(lambda: True, k=5)
    assert out["passes"] == 5 and out["rate"] == 1.0 and out["flaky"] is False
    assert reliability_record(lambda: True, k=5).success


def test_mixed_is_flaky_and_fails():
    seq = iter([True, False, True])
    rec = reliability_record(lambda: next(seq), k=3)
    assert not rec.success and "flaky" in rec.reason.lower()
