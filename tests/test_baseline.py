import pathlib
from house_price_tool.baseline import load_baseline, psqft_for

FIX = pathlib.Path(__file__).parent / "fixtures" / "baseline_sample.md"


def test_parses_yoy_and_psqft():
    b = load_baseline(FIX)
    assert b.yoy["SL6 7"] == 10.1
    assert b.psqft[("SL6 7", "S")] == 510.0
    assert b.median_sqft[("SL6 7", "S")] is None


def test_psqft_for_returns_value_and_basis():
    b = load_baseline(FIX)
    val, basis = psqft_for(b, "SL6 7", "S")
    assert val == 510.0 and basis == "type"
    val, basis = psqft_for(b, "SL6 9", "S")
    assert val is None and "no segment" in basis.lower()
