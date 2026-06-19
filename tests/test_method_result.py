from house_price_tool.method_result import MethodEstimate


def test_unavailable_returns_none():
    assert MethodEstimate(name="m2", estimate=None, available=False).to_reconcile_dict() is None


def test_m1_dict_shape():
    d = MethodEstimate(name="m1", estimate=635000, available=True, weakness=True).to_reconcile_dict()
    assert d == {"estimate": 635000, "weakness": True}


def test_m3_dict_includes_contamination_flag():
    d = MethodEstimate(name="m3", estimate=620000, available=True,
                       listing_visible_on_avm=True).to_reconcile_dict()
    assert d["listing_visible_on_avm"] is True and d["estimate"] == 620000
