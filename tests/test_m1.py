from house_price_tool.methods.m1 import method_one
from house_price_tool.baseline import MarketBaseline
from house_price_tool.models import PropertyRecord
from house_price_tool.records import SourceRef


def _comp(uid, price, date="2025-12-01", pc="SL6 7AB"):
    return PropertyRecord(postcode=pc, property_type="S", paon="1", street="X",
                          sold_price=price, deed_date=date,
                          sources=[SourceRef(dataset="sold", row_id=uid, url="u")])


def _baseline(yoy=10.0):
    return MarketBaseline(yoy={"SL6 7": yoy}, psqft={}, median_sqft={})


def test_unavailable_when_fewer_than_five():
    m = method_one([_comp("a", 600000)], today="2026-06-19", baseline=_baseline())
    assert not m.available and "insufficient" in m.flags[0]


def test_median_of_trend_adjusted():
    comps = [_comp(str(i), 600000, date="2026-06-01") for i in range(5)]
    m = method_one(comps, today="2026-06-19", baseline=_baseline(yoy=0.0))
    assert m.available and m.estimate == 600000


def test_trend_cap_flags_weakness():
    comps = [_comp(str(i), 600000, date="2024-06-01") for i in range(5)]
    m = method_one(comps, today="2026-06-19", baseline=_baseline(yoy=10.0))
    assert m.weakness and any("trend-capped" in f for f in m.flags)
    assert m.estimate == 660000
