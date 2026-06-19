from house_price_tool.retrieval import retrieve_comps
from house_price_tool.models import PropertyRecord, EpcRecord
from house_price_tool.records import SourceRef


def _rec(uid, ptype="S", sqm=110, date="2025-06-01"):
    epc = EpcRecord(certificate_id=f"E{uid}", postcode="SL6 7AB", paon="1",
                    street="X", floor_area_sqm=sqm) if sqm else None
    return PropertyRecord(postcode="SL6 7AB", property_type=ptype, paon="1",
                          street="X", sold_price=500000, deed_date=date, epc=epc,
                          sources=[SourceRef(dataset="sold", row_id=uid, url="u")])


def test_recall_at_k_full_when_all_valid_retrieved():
    subject = _rec("subj")
    cands = [_rec(f"v{i}", sqm=110 + i) for i in range(6)] + [_rec("d", ptype="D", sqm=300)]
    comps, rec = retrieve_comps(subject, cands, today="2026-06-19", k=20)
    assert rec.gate_id == "H3" and rec.metric == "recall@K"
    assert rec.success and rec.score == 1.0
    assert all(c.property_type == "S" for c in comps)


def test_recall_below_threshold_fails():
    subject = _rec("subj")
    cands = [_rec(f"v{i}", sqm=110 + i) for i in range(10)]
    comps, rec = retrieve_comps(subject, cands, today="2026-06-19", k=1)
    assert rec.score < 0.95 and not rec.success
