import pathlib

from house_price_tool.gate import geography_gate, GateDecision
from house_price_tool.geography import load_geography

GEO = pathlib.Path(__file__).parent / "fixtures" / "geographies"


def test_calibrated_area_proceeds():
    cfg = load_geography(GEO / "sl6-maidenhead")
    decision, msg, rec = geography_gate(cfg, "S", "headless", "2026-06-19")
    assert decision is GateDecision.PROCEED
    assert rec.gate_id == "H1" and rec.success


def test_uncalibrated_headless_returns_not_in_demo():
    cfg = load_geography(GEO / "w13-west-ealing")
    decision, msg, rec = geography_gate(cfg, "S", "headless", "2026-06-19")
    assert decision is GateDecision.NOT_IN_DEMO
    assert msg == "Not part of the demo, calibration needed"


def test_uncalibrated_interactive_prompts_calibration():
    cfg = load_geography(GEO / "w13-west-ealing")
    decision, msg, rec = geography_gate(cfg, "S", "interactive", "2026-06-19")
    assert decision is GateDecision.PROMPT_CALIBRATION
    assert "Run calibration now?" in msg
