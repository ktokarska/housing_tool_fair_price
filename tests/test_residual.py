from house_price_tool.eval.residual import ResidualRecord, residual_from_result


def test_residual_and_in_range():
    r = ResidualRecord(subject_id="PP-1", sold_price=600000, midpoint=630000,
                       range_lo=600000, range_hi=660000, confidence="High",
                       abstained=False)
    assert round(r.residual_pct, 1) == 5.0
    assert r.abs_residual_pct == r.residual_pct
    assert r.in_range


def test_residual_from_contract_handles_no_range():
    contract = {"value_range": None, "confidence": None, "abstain": True}
    assert residual_from_result("PP-9", 500000, contract) is None
