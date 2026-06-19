import pathlib
from house_price_tool.agent import run_agent
from house_price_tool.output import HouseResult
from house_price_tool.llm import FakeLLMClient

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_uncalibrated_area_blocks_headless():
    out = run_agent(
        snapshot_root=FIX / "snap", geo_dir=FIX / "geographies" / "w13-west-ealing",
        geo_slug="w13-west-ealing", sub_postcode="W13 0", property_type="S",
        asking=500000, today="2026-06-19", run_mode="headless",
        llm_client=FakeLLMClient("x"), judge_client=FakeLLMClient("Score: 5"))
    assert isinstance(out, dict) and out["gate"].value == "NOT_IN_DEMO"


def test_calibrated_area_runs_end_to_end():
    out = run_agent(
        snapshot_root=FIX / "snap", geo_dir=FIX / "geographies" / "sl6-maidenhead",
        geo_slug="sl6-maidenhead", sub_postcode="SL6 7", property_type="S",
        asking=650000, today="2026-06-19", run_mode="headless",
        llm_client=FakeLLMClient("The available methods support the range shown."),
        judge_client=FakeLLMClient("Score: 5"))
    assert isinstance(out, HouseResult)
    gate_ids = {m.gate_id for m in out.metrics}
    assert {"H1", "H2", "H3", "H8"} <= gate_ids
    assert out.verdict
