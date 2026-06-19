import pathlib

from house_price_tool.snapshot import load_snapshot
from house_price_tool.geography import load_geography
from house_price_tool.gate import geography_gate, GateDecision
from house_price_tool.resolve import resolve_candidates, provenance_gate

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_step1_then_step2_chain():
    cfg = load_geography(FIX / "geographies" / "sl6-maidenhead")
    decision, _, h1 = geography_gate(cfg, "S", "headless", "2026-06-19")
    assert decision is GateDecision.PROCEED and h1.success

    snap = load_snapshot(FIX / "snap")
    recs = resolve_candidates(snap, "sl6-maidenhead", "SL6 7", "S")
    h2 = provenance_gate(recs, snap, "sl6-maidenhead")
    assert h2.success
    for rec in (h1, h2):
        assert set(rec.to_dict()) == {"metric", "gate_id", "score",
                                      "threshold", "success", "reason"}
