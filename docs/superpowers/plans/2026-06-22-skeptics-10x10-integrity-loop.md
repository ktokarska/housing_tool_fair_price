# Skeptics 10×10 Integrity Loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real (not simulated) 10-grader × 10-input evaluation harness over the House Price Tool, capture a baseline, then loop honest fixes until every cell is A+ or hits a documented integrity wall.

**Architecture:** A self-contained package under `evals_housing_tool/skeptics_10x10/` that (a) executes the real `run_agent` pipeline on 10 locked edge-case inputs offline, (b) grades each real output with 10 deterministic persona rubrics, (c) emits a 100-cell matrix + report. The loop then root-causes sub-A+ cells and applies the smallest honest fix.

**Tech Stack:** Python 3.10 (venv at `.venv`), pytest, the existing `house_price_tool` package, `FakeLLMClient` (offline prose). No network, no API key.

## Global Constraints

- Branch: `dev_kasia` only. Existing 93-test suite must stay green after every tool-side fix.
- Fully offline: `FakeLLMClient` for prose, pinned snapshots, no network/API key. Determinism is graded (G9).
- A+ = integrity: correct gate/abstain/quarantine/provenance/faithfulness + applicable per-run gates green. Honest refusal earns A+; overconfidence fails.
- Never mutate the pinned snapshot; fault-injection (I6/I7/I9) operates on a temp copy.
- Any methodology-threshold edit requires a written, auditable justification in `loop.md`. No silent PASS-gaming.
- Inputs lock after baseline (Round 0).

---

### Task 1: Scaffold + real-data discovery

**Files:**
- Create: `evals_housing_tool/skeptics_10x10/__init__.py`
- Create: `evals_housing_tool/skeptics_10x10/discover.py`
- Create: `tests/skeptics_10x10/__init__.py`

**Interfaces:**
- Produces: `discover.snapshot_paths() -> dict` returning `{snapshot_root, geo_dirs{slug: Path}}`; `discover.sample_subjects(slug, sub_postcode, property_type) -> list[str]` (real sold row_ids).

- [ ] **Step 1: Write the discovery script** that locates the pinned snapshot + geography dirs and prints, per area, the available sub-postcodes, property types, calibration date/version, and a few real subject `row_id`s (via `resolve_candidates`). This is a script run once to choose real input values.

```python
# discover.py
import pathlib, sys
sys.path.insert(0, "src")
from house_price_tool.snapshot import load_snapshot
from house_price_tool.resolve import resolve_candidates
from house_price_tool.geography import load_geography

ROOT = pathlib.Path(__file__).resolve().parents[2]

def snapshot_paths():
    snaps = sorted((ROOT / "data" / "snapshots").glob("*"))
    geo = {p.name: p for p in (ROOT / "geographies").glob("*") if p.is_dir()}
    return {"snapshot_root": snaps[-1], "geo_dirs": geo}

def main():
    p = snapshot_paths()
    snap = load_snapshot(p["snapshot_root"])
    for slug, gdir in p["geo_dirs"].items():
        cfg = load_geography(gdir)
        print(f"== {slug} cal={getattr(cfg,'calibration_date',None)} ver={getattr(cfg,'version',None)}")
        # print real sub-postcodes/types/subjects for each area
```

- [ ] **Step 2: Run it** — `cd housing repo && source .venv/bin/activate && python -m evals_housing_tool.skeptics_10x10.discover` — and record the real values (areas, sub-postcodes, subject ids, calibration date, version) into a scratch note used by Task 2. Expected: prints real rows, no exceptions.
- [ ] **Step 3: Commit** — `git add evals_housing_tool/skeptics_10x10 tests/skeptics_10x10 && git commit -m "scaffold skeptics_10x10 + data discovery"`.

---

### Task 2: Locked input specs + executor

**Files:**
- Create: `evals_housing_tool/skeptics_10x10/inputs.py`
- Test: `tests/skeptics_10x10/test_inputs.py`

**Interfaces:**
- Consumes: `discover.snapshot_paths`, `house_price_tool.agent.run_agent`.
- Produces: `INPUTS: list[InputSpec]` (exactly 10, ids I1..I10); `InputSpec` is a dataclass with `id, title, stresses, expected_behavior, kwargs(dict for run_agent), fault(callable|None)`; `execute(spec) -> dict` returning the raw run output (HouseResult.to_contract() or the gate-refusal dict) plus `_meta`.
- `execute` applies `fault` to a **temp copy** of snapshot/geography when present (I6 stale calibration, I7 version bump, I9 corrupted row), never the original.

- [ ] **Step 1: Write failing test** asserting `len(INPUTS) == 10`, ids are `I1..I10`, every spec has a non-empty `expected_behavior`, and `execute(I5_uncalibrated)` returns `gate == NOT_IN_DEMO` with the exact demo message.

```python
def test_ten_inputs_well_formed():
    from evals_housing_tool.skeptics_10x10.inputs import INPUTS
    assert [s.id for s in INPUTS] == [f"I{i}" for i in range(1, 11)]
    assert all(s.expected_behavior for s in INPUTS)

def test_uncalibrated_routes_to_not_in_demo():
    from evals_housing_tool.skeptics_10x10.inputs import INPUTS, execute
    out = execute(next(s for s in INPUTS if s.id == "I5"))
    assert out["gate"] == "NOT_IN_DEMO"
    assert out["message"] == "Not part of the demo, calibration needed"
```

- [ ] **Step 2: Run** `pytest tests/skeptics_10x10/test_inputs.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement `inputs.py`** with the 10 specs from the spec table, wiring real discovered values; `execute` builds `run_agent` kwargs (`llm_client=FakeLLMClient()`, a judge client, `today` pinned), applies faults to temp copies via `tempfile`/`shutil.copytree`.
- [ ] **Step 4: Run** `pytest tests/skeptics_10x10/test_inputs.py -v` → PASS.
- [ ] **Step 5: Commit** — `git commit -am "skeptics_10x10: 10 locked input specs + offline executor"`.

---

### Task 3: Runner — capture 10 real outputs

**Files:**
- Create: `evals_housing_tool/skeptics_10x10/run_10x10.py`
- Test: `tests/skeptics_10x10/test_runner.py`

**Interfaces:**
- Consumes: `inputs.INPUTS`, `inputs.execute`.
- Produces: `run_all(out_dir) -> dict[id, output]`; writes `runs/<id>.json` (output + `_meta`); deterministic.

- [ ] **Step 1: Write failing test** that `run_all` produces 10 files and that re-running yields byte-identical JSON (determinism, the thing G9 will grade).

```python
def test_runner_deterministic(tmp_path):
    from evals_housing_tool.skeptics_10x10.run_10x10 import run_all
    a = run_all(tmp_path / "a"); b = run_all(tmp_path / "b")
    for i in [f"I{n}" for n in range(1, 11)]:
        assert (tmp_path/"a"/f"runs/{i}.json").read_text() == (tmp_path/"b"/f"runs/{i}.json").read_text()
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `run_all` (sorted keys, no timestamps in payload to preserve determinism; pinned `today`).
- [ ] **Step 4: Run** → PASS. Then run the real capture: `python -m evals_housing_tool.skeptics_10x10.run_10x10` and eyeball the 10 `runs/*.json` (these are the real material the graders score).
- [ ] **Step 5: Commit** — `git commit -am "skeptics_10x10: deterministic runner capturing 10 real outputs"`.

---

### Task 4: The 10 persona graders (TDD against real captured output)

**Files:**
- Create: `evals_housing_tool/skeptics_10x10/graders.py`
- Test: `tests/skeptics_10x10/test_graders.py`

**Interfaces:**
- Consumes: a run output dict (HouseResult contract or gate-refusal).
- Produces: `GRADERS: list[Grader]` (10). Each `Grader` has `id (G1..G10), persona_name, grade(output, ctx) -> Cell`. `Cell = {grade: str, failed_checks: list[str], evidence: list[str]}`. `LETTER(passed, total, hard_fail) -> str` shared: A+ only when `hard_fail is False and passed == total`.

- [ ] **Step 1: Write failing tests** — one "rewards correct behavior" + one "mutation" test per grader (a known-bad output must drop below A+ on the matching grader). Example for G1 Provenance Auditor:

```python
def test_g1_passes_clean_provenance(clean_output):
    cell = grader("G1").grade(clean_output, {})
    assert cell["grade"] == "A+"

def test_g1_fails_orphan_value():
    bad = {"estimates": {"M1": 635000}, "metrics": [{"gate_id": "H2", "success": False,
            "reason": "orphan comp PP-X has no snapshot row"}], "verdict": "FAIR", ...}
    cell = grader("G1").grade(bad, {})
    assert cell["grade"] != "A+" and any("orphan" in e for e in cell["evidence"])
```

- [ ] **Step 2: Run** `pytest tests/skeptics_10x10/test_graders.py -v` → FAIL.
- [ ] **Step 3: Implement all 10 graders** against the real output shape (`metrics[].gate_id/success/reason`, `verdict`, `confidence`, `abstain`, `value_range`, `estimates`, `explanation`, gate-refusal `gate`/`message`). Each persona keys on its anchor gate(s) + persona-specific checks (e.g. G2 rewards QUARANTINE/abstain and *fails* a directional verdict whose residual support is absent; G6 checks exact gate message+route per run_mode; G9 consumes two runs and compares).
- [ ] **Step 4: Run** → PASS (all reward + all mutation tests).
- [ ] **Step 5: Commit** — `git commit -am "skeptics_10x10: 10 deterministic persona graders + mutation tests"`.

---

### Task 5: Matrix + report

**Files:**
- Create: `evals_housing_tool/skeptics_10x10/grade_10x10.py`
- Test: `tests/skeptics_10x10/test_matrix.py`

**Interfaces:**
- Consumes: `run_10x10.run_all`, `graders.GRADERS`.
- Produces: `build_matrix(round_n, out_dir) -> Matrix` (100 cells), writes `grades/round_<N>.json` + `report_round_<N>.md` (10×10 table; for every sub-A+ cell, the persona, failed checks, and evidence).

- [ ] **Step 1: Write failing test** — matrix has exactly 100 cells (10 graders × 10 inputs) and the report file contains a 10×10 table with all grader and input ids.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `build_matrix` + markdown renderer (rows = graders, cols = inputs, cell = letter; A+ rendered plainly, sub-A+ flagged).
- [ ] **Step 4: Run** → PASS. Then build the **baseline**: `python -m evals_housing_tool.skeptics_10x10.grade_10x10 --round 0` → `report_round_0.md`.
- [ ] **Step 5: Commit** — `git commit -am "skeptics_10x10: 100-cell matrix + round report; baseline round_0"`.

---

### Task 6: Persona character sheets

**Files:**
- Create: `evals_housing_tool/skeptics_10x10/personas.md`

- [ ] **Step 1: Write** the 10 character sheets (name, background, source of skepticism, what earns an A+, what they never forgive), each tied to its grader id and anchor gate. Keep each to a tight paragraph.
- [ ] **Step 2: Commit** — `git commit -am "skeptics_10x10: 10 skeptical grader personas"`.

---

### Task 7: The integrity loop (execution, not fixed code)

**Files:**
- Create: `evals_housing_tool/skeptics_10x10/loop.md`

This task is the supervised loop. It produces no new abstractions — it consumes Tasks 1-6.

- [ ] **Step 1:** Record the baseline matrix (round_0) into `loop.md`: count of A+ vs sub-A+ cells, and the list of sub-A+ (grader, input, reason).
- [ ] **Step 2:** For each sub-A+ cell, invoke `superpowers:systematic-debugging` to find the *real* root cause (a tool defect, an over-strict/unfair rubric, or — rarely — a genuinely mis-set threshold).
- [ ] **Step 3:** Apply the smallest honest fix via an allowed lever. If tool-side, keep the 93-test suite green. If rubric-side, justify why the original check was a nitpick a skeptic would reject. If threshold-side, write the auditable justification in `loop.md`.
- [ ] **Step 4:** Re-run `grade_10x10 --round N`; append the new matrix + the diff (which cells improved, why) to `loop.md`. Commit each round.
- [ ] **Step 5:** Stop when all 100 cells are A+ **or** a cell hits a principled wall (only path is gaming) — document the wall as the correct terminal state. Soft cap ~8 rounds, then check in with the user.
- [ ] **Step 6:** Final verification (`superpowers:verification-before-completion`): paste the actual final `report_round_N.md` matrix as evidence; confirm `pytest` still 93+ green.
