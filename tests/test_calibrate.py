import pathlib
from house_price_tool.eval.calibrate import run_calibration
from house_price_tool.llm import FakeLLMClient

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_calibration_produces_residuals_blind():
    records, counts = run_calibration(
        snapshot_root=FIX / "snap", geo_dir=FIX / "geographies" / "sl6-maidenhead",
        geo_slug="sl6-maidenhead", property_types=["S", "T"], today="2026-06-19",
        llm_client=FakeLLMClient("The available methods support the range."),
        judge_client=FakeLLMClient("Score: 5"))
    assert counts["n_sample"] >= 1
    for r in records:
        assert r.sold_price > 0 and isinstance(r.residual_pct, float)
