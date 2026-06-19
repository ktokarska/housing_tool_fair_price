from house_price_tool.methods.m2 import method_two
from house_price_tool.baseline import MarketBaseline
from house_price_tool.models import PropertyRecord, EpcRecord
from house_price_tool.records import SourceRef


def _subject(sqm=110.0, with_epc=True):
    epc = EpcRecord(certificate_id="E1", postcode="SL6 7AB", paon="1", street="X",
                    floor_area_sqm=sqm) if with_epc else None
    src = [SourceRef(dataset="epc", row_id="E1", url="u")] if with_epc else []
    return PropertyRecord(postcode="SL6 7AB", property_type="S", paon="1",
                          street="X", epc=epc, sources=src)


def _baseline(median=None):
    return MarketBaseline(yoy={}, psqft={("SL6 7", "S"): 510.0},
                          median_sqft={("SL6 7", "S"): median})


def test_estimate_from_epc_sqft():
    m, h9 = method_two(_subject(sqm=100.0), _baseline())
    assert m.available and m.estimate == round(100.0 * 10.764 * 510.0)
    assert h9.gate_id == "H9" and h9.success


def test_unavailable_without_epc_but_h9_passes():
    m, h9 = method_two(_subject(with_epc=False), _baseline())
    assert not m.available and "no EPC" in m.flags[0]
    assert h9.success


def test_size_mismatch_downgrade():
    m, _ = method_two(_subject(sqm=200.0), _baseline(median=1000.0))
    assert m.weakness and any("size-mismatch" in f for f in m.flags)
