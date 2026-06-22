"""Task 5 tests: the 100-cell matrix and its report."""
from evals_housing_tool.skeptics_10x10.grade_10x10 import build_matrix


def test_matrix_has_100_cells(tmp_path):
    m = build_matrix(0, tmp_path)
    assert len(m["cells"]) == 100  # 10 graders x 10 inputs
    assert {c["grader"] for c in m["cells"]} == {f"G{i}" for i in range(1, 11)}
    assert {c["input"] for c in m["cells"]} == {f"I{i}" for i in range(1, 11)}


def test_report_written_with_table(tmp_path):
    build_matrix(0, tmp_path)
    report = (tmp_path / "report_round_0.md").read_text()
    assert "**G1**" in report and "I1" in report
    for gid in [f"G{i}" for i in range(1, 11)]:
        assert gid in report


def test_matrix_counts_consistent(tmp_path):
    m = build_matrix(0, tmp_path)
    aplus = sum(1 for c in m["cells"] if c["grade"] == "A+")
    assert m["a_plus"] == aplus
    assert m["total"] == 100
