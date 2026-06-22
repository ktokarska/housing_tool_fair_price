"""The 10 locked, REAL edge-case inputs and their offline executor.

Every value here was discovered from the pinned snapshot (see discover.py); nothing is invented.
The executor runs the real `run_agent` pipeline fully offline (FakeLLM prose, pinned snapshot).
Fault-injected cases (I5/I6/I7 geography, I9 snapshot) operate on a TEMP COPY; the pinned
originals are never mutated.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
import shutil
import tempfile
from typing import Callable, Optional

from house_price_tool.agent import run_agent
from house_price_tool.gate import GateDecision
from house_price_tool.llm import FakeLLMClient
from house_price_tool.output import HouseResult
from house_price_tool.snapshot import SnapshotIntegrityError

from .discover import snapshot_paths

TODAY = "2026-06-19"  # pinned to the snapshot date; keeps every run reproducible
# Honestly-flagged offline prose. It makes NO substantive claim, so it stays true whether the
# run produced two methods and a range or abstained with none (the old wording asserted method
# support a 0-method result does not have).
PLACEHOLDER = "Placeholder rationale (offline sample, no LLM call)."


@dataclasses.dataclass(frozen=True)
class InputSpec:
    id: str
    title: str
    stresses: str
    expected_behavior: str
    # run_agent kwargs that do not depend on resolved paths:
    geo_slug: str
    sub_postcode: str
    property_type: str
    asking: Optional[int]
    skip_gate: bool
    run_mode: str = "headless"
    subject_id: Optional[str] = None
    geo_fault: Optional[str] = None       # one of: "uncalibrated", "expired", "version"
    snapshot_fault: bool = False          # I9: corrupt a temp snapshot copy


INPUTS: list[InputSpec] = [
    InputSpec(
        id="I1", title="SL6 in-area subject, engine preview",
        stresses="A clean, comp-rich subject with the gate bypassed.",
        expected_behavior="Real estimate/range/verdict; every applicable per-run gate green.",
        geo_slug="sl6-maidenhead", sub_postcode="SL6 2", property_type="S",
        subject_id="1061746D-A9ED-3C34-E063-4804A8C0F9E7", asking=625000, skip_gate=True),
    InputSpec(
        id="I2", title="W13 high-divergence subject",
        stresses="Methods that disagree; the abstain/INDETERMINATE path.",
        expected_behavior="Abstain decision consistent with the computed spread/confidence.",
        geo_slug="w13-west-ealing", sub_postcode="W13 0", property_type="S",
        subject_id="34222872-AC53-4D2B-E063-4704A8C07853", asking=550000, skip_gate=True),
    InputSpec(
        id="I3", title="UB3 coverage-quarantine subject",
        stresses="An area quarantined on coverage; honest low-confidence framing.",
        expected_behavior="Real numbers; confidence/range honest; no overclaim.",
        geo_slug="ub3-hayes", sub_postcode="UB3 1", property_type="S",
        subject_id="1061746E-3905-3C34-E063-4804A8C0F9E7", asking=430000, skip_gate=True),
    InputSpec(
        id="I4", title="SL6 production run (gate ON)",
        stresses="The geography gate on a quarantined area.",
        expected_behavior="Withhold: NOT_IN_DEMO, reason cites the QUARANTINE verdict.",
        geo_slug="sl6-maidenhead", sub_postcode="SL6 2", property_type="S",
        subject_id=None, asking=None, skip_gate=False),
    InputSpec(
        id="I5", title="Uncalibrated area, headless",
        stresses="An area with no calibration on record.",
        expected_behavior="NOT_IN_DEMO with the exact 'Not part of the demo' message.",
        geo_slug="tw8-brentford", sub_postcode="TW8 0", property_type="S",
        subject_id=None, asking=None, skip_gate=False, geo_fault="uncalibrated"),
    InputSpec(
        id="I6", title="Expired (>90d) calibration",
        stresses="A calibration older than the 90-day window.",
        expected_behavior="NOT_IN_DEMO; reason cites the stale-age rule.",
        geo_slug="sl6-maidenhead", sub_postcode="SL6 2", property_type="S",
        subject_id=None, asking=None, skip_gate=False, geo_fault="expired"),
    InputSpec(
        id="I7", title="Methodology version mismatch",
        stresses="A calibration produced under an older methodology version.",
        expected_behavior="NOT_IN_DEMO; reason cites the version gate.",
        geo_slug="sl6-maidenhead", sub_postcode="SL6 2", property_type="S",
        subject_id=None, asking=None, skip_gate=False, geo_fault="version"),
    InputSpec(
        id="I8", title="Subject with no EPC",
        stresses="Method 2 has no square-foot source.",
        expected_behavior="Method 2 unavailable; no fabricated sq ft; H9 green.",
        geo_slug="sl6-maidenhead", sub_postcode="SL6 0", property_type="T",
        subject_id="237B17FD-AB9D-22AC-E063-4804A8C0EA3A", asking=520000, skip_gate=True),
    InputSpec(
        id="I9", title="Malformed snapshot row",
        stresses="A corrupted snapshot (checksum mismatch) in an integrity-verified area.",
        expected_behavior="The run halts on SnapshotIntegrityError; it does not value on corrupt data.",
        geo_slug="ub3-hayes", sub_postcode="UB3 1", property_type="S",
        subject_id="1061746E-3905-3C34-E063-4804A8C0F9E7", asking=430000, skip_gate=True,
        snapshot_fault=True),
    InputSpec(
        id="I10", title="Thin-comp, high-divergence subject (abstain boundary)",
        stresses="A sparse segment near the 20% abstain boundary.",
        expected_behavior="Abstain decision internally consistent with the spread it computed.",
        geo_slug="ub3-hayes", sub_postcode="UB3 3", property_type="D",
        subject_id="1EAE3DF7-6AE5-9EB1-E063-4704A8C09D02", asking=600000, skip_gate=True),
]


# ---------------------------------------------------------------------------
# Fault injection (temp copies only)
# ---------------------------------------------------------------------------
def _front_matter_replace(md_path: pathlib.Path, mutate: Callable[[str], str]) -> None:
    md_path.write_text(mutate(md_path.read_text()))


def _make_temp_geo(real_geo_dir: pathlib.Path, fault: str, stack: list) -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sk10_geo_"))
    stack.append(tmp)
    dst = tmp / real_geo_dir.name
    shutil.copytree(real_geo_dir, dst)
    cal_dir = dst / "calibration"
    cal_files = sorted(cal_dir.glob("*.md")) if cal_dir.exists() else []
    if fault == "uncalibrated":
        if cal_dir.exists():
            shutil.rmtree(cal_dir)  # no calibration on record
    elif fault == "expired":
        for f in cal_files:
            _front_matter_replace(f, lambda t: re.sub(
                r"verdict:.*", "verdict: PASS", re.sub(
                    r"date:.*", "date: 2026-01-01", t, count=1), count=1))
    elif fault == "version":
        for f in cal_files:
            _front_matter_replace(f, lambda t: re.sub(
                r"verdict:.*", "verdict: PASS", re.sub(
                    r'methodology_version:.*', 'methodology_version: "2.0"', t, count=1),
                count=1))
    else:  # pragma: no cover - guarded by the spec set
        raise ValueError(f"unknown geo_fault {fault!r}")
    return dst


def _make_temp_snapshot(real_root: pathlib.Path, geo_slug: str, stack: list) -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sk10_snap_"))
    stack.append(tmp)
    dst = tmp / real_root.name
    shutil.copytree(real_root, dst)
    sold_csv = dst / geo_slug / "sold.csv"           # corrupt a real, pinned file
    sold_csv.write_text(sold_csv.read_text() + "\n# corrupted row injected by I9\n")
    return dst


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------
def _normalize(out) -> dict:
    if isinstance(out, HouseResult):
        return out.to_contract()
    # gate-refusal dict: serialize the enum + metric records
    gate = out["gate"]
    return {
        "gate": gate.value if isinstance(gate, GateDecision) else str(gate),
        "message": out["message"],
        "metrics": [m.model_dump() for m in out["metrics"]],
    }


def execute(spec: InputSpec) -> dict:
    paths = snapshot_paths()
    snapshot_root = paths["snapshot_root"]
    cleanup: list = []
    try:
        if spec.geo_fault:
            # Build a temp geography for the faulted area. Reuse SL6's structure as a base
            # for the synthetic uncalibrated area so the config loads.
            base = paths["geo_dirs"]["sl6-maidenhead"]
            geo_dir = _make_temp_geo(base, spec.geo_fault, cleanup)
            if spec.geo_fault == "uncalibrated":
                # Relabel so it reads as a genuinely out-of-demo area.
                ad = geo_dir / "area_definition.md"
                _front_matter_replace(ad, lambda t: re.sub(
                    r"sub_postcodes:.*", "sub_postcodes: [TW8 0]", re.sub(
                        r"name:.*", 'name: "Brentford (TW8)"', re.sub(
                            r"slug:.*", "slug: tw8-brentford", t, count=1), count=1), count=1))
        else:
            geo_dir = paths["geo_dirs"][spec.geo_slug]

        if spec.snapshot_fault:
            snapshot_root = _make_temp_snapshot(snapshot_root, spec.geo_slug, cleanup)

        try:
            out = run_agent(
                snapshot_root=snapshot_root, geo_dir=geo_dir, geo_slug=spec.geo_slug,
                sub_postcode=spec.sub_postcode, property_type=spec.property_type,
                asking=spec.asking, today=TODAY, run_mode=spec.run_mode,
                subject_id=spec.subject_id, skip_gate=spec.skip_gate,
                llm_client=FakeLLMClient(PLACEHOLDER),
                judge_client=FakeLLMClient("Score: 5"))
        except SnapshotIntegrityError as e:
            # Strip the volatile temp path so the captured output stays deterministic (G9).
            msg = str(e).replace(str(snapshot_root), "<snapshot>")
            return {"halted": True, "error_type": "SnapshotIntegrityError", "error": msg}
        except Exception as e:  # any other halt is still a (different) halt, recorded honestly
            msg = str(e).replace(str(snapshot_root), "<snapshot>")
            return {"halted": True, "error_type": type(e).__name__, "error": msg}
        return _normalize(out)
    finally:
        for d in cleanup:
            shutil.rmtree(d, ignore_errors=True)
