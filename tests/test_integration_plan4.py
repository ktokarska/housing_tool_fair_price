import pathlib
import pytest

from house_price_tool.eval.calibrate import run_calibration
from house_price_tool.eval.gate_catalog import calibration_report
from house_price_tool.eval.mutation import mutation_check
from house_price_tool.llm import FakeLLMClient

FIX = pathlib.Path(__file__).parent / "fixtures"


@pytest.mark.release
def test_calibration_end_to_end_produces_a_verdict():
    records, counts = run_calibration(
        snapshot_root=FIX / "snap", geo_dir=FIX / "geographies" / "sl6-maidenhead",
        geo_slug="sl6-maidenhead", property_types=["S", "T"], today="2026-06-19",
        llm_client=FakeLLMClient("The available methods support the range."),
        judge_client=FakeLLMClient("Score: 5"))
    report = calibration_report(records, counts)
    assert report["verdict"]["verdict"] in {
        "PASS", "PASS WITH CORRECTION", "PASS WITH WIDER RANGES", "QUARANTINE"}


@pytest.mark.contract
def test_mutation_check_is_discriminative():
    assert mutation_check() == {"fabricated_number": True,
                                "directional_on_low": True,
                                "inflated_estimate": True}
