"""Execute the REAL pipeline on the 10 locked inputs and capture each output.

    python -m evals_housing_tool.skeptics_10x10.run_10x10 [out_dir]

Output: <out_dir>/runs/<id>.json, one per input. Deterministic by construction (sorted keys,
no timestamps in the payload, pinned snapshot + FakeLLM), because reproducibility is itself
graded (G9).
"""
from __future__ import annotations

import json
import pathlib
import sys

from .inputs import INPUTS, InputSpec, execute


def _run_record(spec: InputSpec) -> dict:
    return {
        "input_id": spec.id,
        "title": spec.title,
        "stresses": spec.stresses,
        "expected_behavior": spec.expected_behavior,
        "spec": {
            "geo_slug": spec.geo_slug, "sub_postcode": spec.sub_postcode,
            "property_type": spec.property_type, "asking": spec.asking,
            "skip_gate": spec.skip_gate, "run_mode": spec.run_mode,
            "subject_id": spec.subject_id, "geo_fault": spec.geo_fault,
            "snapshot_fault": spec.snapshot_fault,
        },
        "output": execute(spec),
    }


def run_all(out_dir: str | pathlib.Path) -> dict[str, dict]:
    out = pathlib.Path(out_dir)
    runs_dir = out / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    for spec in INPUTS:
        rec = _run_record(spec)
        results[spec.id] = rec
        text = json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False)
        (runs_dir / f"{spec.id}.json").write_text(text + "\n")
    return results


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "evals_housing_tool/skeptics_10x10/_out"
    results = run_all(out_dir)
    for i, rec in results.items():
        o = rec["output"]
        summary = (o.get("gate") or ("HALTED:" + o["error_type"] if o.get("halted")
                   else o.get("verdict", "?")))
        print(f"{i:>3}  {rec['title'][:42]:42}  -> {summary}")


if __name__ == "__main__":
    main()
