"""Task 3 tests: the runner captures 10 real outputs deterministically."""
import json

from evals_housing_tool.skeptics_10x10.run_10x10 import run_all

IDS = [f"I{i}" for i in range(1, 11)]


def test_runner_writes_ten_outputs(tmp_path):
    run_all(tmp_path)
    stems = {f.stem for f in (tmp_path / "runs").glob("*.json")}
    assert stems == set(IDS)


def test_runner_is_byte_deterministic(tmp_path):
    run_all(tmp_path / "a")
    run_all(tmp_path / "b")
    for i in IDS:
        a = (tmp_path / "a" / "runs" / f"{i}.json").read_text()
        b = (tmp_path / "b" / "runs" / f"{i}.json").read_text()
        assert a == b, f"{i} not deterministic"


def test_each_run_payload_records_input_id(tmp_path):
    run_all(tmp_path)
    for i in IDS:
        payload = json.loads((tmp_path / "runs" / f"{i}.json").read_text())
        assert payload["input_id"] == i
        assert "output" in payload
