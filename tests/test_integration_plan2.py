import pathlib
from house_price_tool.snapshot import load_snapshot
from house_price_tool.resolve import resolve_candidates
from house_price_tool.retrieval import retrieve_comps
from house_price_tool.baseline import load_baseline
from house_price_tool.methods.m1 import method_one
from house_price_tool.methods.m2 import method_two
from house_price_tool.methods.m3 import load_avm_table, method_three

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_resolve_to_three_methods_payload():
    snap = load_snapshot(FIX / "snap")
    baseline = load_baseline(FIX / "baseline_sample.md")
    candidates = resolve_candidates(snap, "sl6-maidenhead", "SL6 7", "S")
    assert candidates, "fixture must contain at least one SL6 7 semi"
    subject = candidates[0]

    comps, h3 = retrieve_comps(subject, candidates, today="2026-06-19")
    m1 = method_one(comps, today="2026-06-19", baseline=baseline)
    m2, h9 = method_two(subject, baseline)
    m3 = method_three(subject, load_avm_table(FIX / "snap", "sl6-maidenhead"))

    payload_methods = {}
    for m in (m1, m2, m3):
        d = m.to_reconcile_dict()
        if d is not None:
            payload_methods[m.name] = d
    assert "m3" in payload_methods
    for rec in (h3, h9):
        assert set(rec.to_dict()) == {"metric", "gate_id", "score",
                                      "threshold", "success", "reason"}
