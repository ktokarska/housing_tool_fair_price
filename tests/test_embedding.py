import numpy as np
from house_price_tool.embedding import FeatureEncoder, sub_postcode_of
from house_price_tool.models import PropertyRecord, EpcRecord
from house_price_tool.records import SourceRef


def _rec(uid, ptype, sqm, pc="SL6 7AB", tenure="F"):
    epc = EpcRecord(certificate_id=f"E{uid}", postcode=pc, paon="1",
                    street="X", floor_area_sqm=sqm) if sqm else None
    return PropertyRecord(postcode=pc, property_type=ptype, paon="1", street="X",
                          sold_price=500000, deed_date="2025-01-01", epc=epc,
                          sources=[SourceRef(dataset="sold", row_id=uid, url="u")])


def test_sub_postcode_extraction():
    assert sub_postcode_of("SL6 7AB") == "SL6 7"


def test_same_segment_is_closer_than_different_type():
    enc = FeatureEncoder().fit([_rec("a", "S", 110), _rec("b", "S", 112),
                                _rec("c", "D", 300)])
    va, vb, vc = (enc.transform(_rec(x, t, s)) for x, t, s in
                  [("a", "S", 110), ("b", "S", 112), ("c", "D", 300)])
    assert np.linalg.norm(va - vb) < np.linalg.norm(va - vc)


def test_transform_many_returns_ids():
    enc = FeatureEncoder().fit([_rec("a", "S", 110)])
    m, ids = enc.transform_many([_rec("a", "S", 110)])
    assert ids == ["a"] and m.shape[0] == 1 and m.dtype == np.float32
