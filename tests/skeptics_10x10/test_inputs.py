"""Task 2 tests: the 10 locked input specs + their offline executor."""
import pytest

from evals_housing_tool.skeptics_10x10.inputs import INPUTS, execute


def test_ten_inputs_with_sequential_ids():
    assert [s.id for s in INPUTS] == [f"I{i}" for i in range(1, 11)]


def test_every_spec_documents_expected_behavior():
    assert all(s.expected_behavior and s.title and s.stresses for s in INPUTS)


def _by_id(i):
    return next(s for s in INPUTS if s.id == i)


def test_uncalibrated_area_routes_to_not_in_demo():
    out = execute(_by_id("I5"))
    assert out["gate"] == "NOT_IN_DEMO"
    assert out["message"] == "Not part of the demo, calibration needed"
    assert "no calibration" in out["metrics"][0]["reason"].lower()


def test_expired_calibration_refuses_on_age():
    out = execute(_by_id("I6"))
    assert out["gate"] == "NOT_IN_DEMO"
    assert "days old" in out["metrics"][0]["reason"]


def test_version_mismatch_refuses_on_methodology():
    out = execute(_by_id("I7"))
    assert out["gate"] == "NOT_IN_DEMO"
    assert "methodology" in out["metrics"][0]["reason"]


def test_production_run_on_quarantined_area_withholds():
    out = execute(_by_id("I4"))
    assert out["gate"] == "NOT_IN_DEMO"
    assert "QUARANTINE" in out["metrics"][0]["reason"]


def test_engine_preview_subject_produces_real_numbers():
    out = execute(_by_id("I1"))
    assert "verdict" in out and out["estimates"]  # a real HouseResult contract


def test_malformed_snapshot_halts():
    out = execute(_by_id("I9"))
    assert out["halted"] is True
    assert "Integrity" in out["error_type"]
