from house_price_tool.rulegate import area_band, rule_valid, rule_valid_set
from house_price_tool.models import PropertyRecord, EpcRecord
from house_price_tool.records import SourceRef


def _rec(uid, ptype="S", sqm=110, pc="SL6 7AB", date="2025-06-01", tenure="F"):
    epc = EpcRecord(certificate_id=f"E{uid}", postcode=pc, paon="1", street="X",
                    floor_area_sqm=sqm) if sqm else None
    return PropertyRecord(postcode=pc, property_type=ptype, paon="1", street="X",
                          sold_price=500000, deed_date=date, epc=epc, tenure=tenure,
                          sources=[SourceRef(dataset="sold", row_id=uid, url="u")])


def test_area_band_edges():
    assert area_band(999) == "lt1000"
    assert area_band(1200) == "1000_1400"
    assert area_band(1500) == "gt1400"
    assert area_band(None) is None


def test_rule_valid_same_segment_recent():
    subj = _rec("subj")
    cand = _rec("c1")
    assert rule_valid(subj, cand, today="2026-06-19")


def test_rule_rejects_wrong_type_and_old_sale():
    subj = _rec("subj")
    assert not rule_valid(subj, _rec("c", ptype="D"), today="2026-06-19")
    assert not rule_valid(subj, _rec("c", date="2024-01-01"), today="2026-06-19")


def test_rule_valid_set_counts_only_valid():
    subj = _rec("subj")
    cands = [_rec("good"), _rec("badtype", ptype="T"), _rec("good2")]
    assert rule_valid_set(subj, cands, today="2026-06-19") == {"good", "good2"}
