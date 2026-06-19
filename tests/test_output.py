from house_price_tool.output import assemble_result, HouseResult
from house_price_tool.records import MetricRecord

RR = {"estimates": {"m1": 635000, "m2": 655000, "m3": 620000},
      "confidence": "High", "range": [604000, 667000],
      "verdict": "FAIR", "detail": "FAIR upper third", "comp_count": 6}


def test_assemble_and_contract_shape():
    res = assemble_result(
        subject_label="Semi-detached in SL6 7AB", geography="sl6-maidenhead",
        snapshot_date="2026-06-19", reconcile_result=RR, abstain=False,
        explanation="Six sales support the range.",
        metrics=[MetricRecord(metric="recall@K", gate_id="H3", score=1.0,
                              threshold=0.95, success=True, reason="6/6")])
    assert isinstance(res, HouseResult)
    contract = res.to_contract()
    assert contract["verdict"] == "FAIR" and contract["abstain"] is False
    assert contract["value_range"] == [604000, 667000]
    assert contract["metrics"][0]["gate_id"] == "H3"
    assert contract["methodology_version"] == "2.1"


def test_abstain_contract_has_no_directional_leak():
    rr = {"estimates": {"m2": 588000}, "confidence": "Low", "range": [529200, 646800],
          "verdict": "INDETERMINATE", "detail": "methods disagree", "comp_count": 0}
    res = assemble_result(subject_label="x", geography="g", snapshot_date="2026-06-19",
                          reconcile_result=rr, abstain=True, explanation="The data is too thin.",
                          metrics=[])
    assert res.to_contract()["abstain"] is True
