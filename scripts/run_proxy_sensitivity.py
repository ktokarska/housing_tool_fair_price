"""M3 sensitivity experiment: does adding a PROXY third method move the verdict?

Builds the open-data proxy estimator (build_proxy_avm.py), re-runs each area's calibration with
the proxy as Method 3, and compares against the canonical two-method (M1+M2) result. Writes
results/sensitivity/proxy_<slug>.json and a summary. Does NOT touch the canonical calibration
records — this is a clearly-labelled what-if, not a re-calibration.

    python scripts/run_proxy_sensitivity.py --date 2026-06-19
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, "src")

from house_price_tool.eval.calibrate import run_calibration  # noqa: E402
from house_price_tool.eval.gate_catalog import calibration_report  # noqa: E402
from house_price_tool.llm import FakeLLMClient  # noqa: E402

sys.path.insert(0, "scripts")
from build_proxy_avm import build_proxy  # noqa: E402

TYPES = ["D", "S", "T", "F"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    snap = pathlib.Path("data/snapshots") / a.date
    out_dir = pathlib.Path("results") / "sensitivity"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []

    for geo_dir in sorted(p for p in pathlib.Path("geographies").iterdir() if p.is_dir()):
        slug = geo_dir.name
        proxy = build_proxy(slug, a.date)
        baseline = json.loads((geo_dir / "calibration" / f"{a.date}.json").read_text())

        recs, counts = run_calibration(
            snapshot_root=snap, geo_dir=geo_dir, geo_slug=slug, property_types=TYPES,
            today=a.date, avm_filename="avm_proxy.csv",
            llm_client=FakeLLMClient("The available methods support the range."),
            judge_client=FakeLLMClient("Score: 5"))
        rep = calibration_report(recs, counts)

        record = {
            "slug": slug,
            "proxy_model": {k: proxy[k] for k in
                            ("n_model", "standalone_mae_pct", "standalone_meanape_pct")},
            "baseline_M1_M2": {"verdict": baseline["verdict"]["verdict"],
                               "stats": baseline["stats"]},
            "with_proxy_M1_M2_M3": {"verdict": rep["verdict"]["verdict"],
                                    "stats": rep["stats"]},
            "verdict_changed": baseline["verdict"]["verdict"] != rep["verdict"]["verdict"],
            "note": ("PROXY third method (open-data hedonic OLS), NOT a real AVM. Built from the "
                     "same Land Registry + EPC data as M1/M2, so correlated; treat as a lower "
                     "bound on what an independent commercial AVM might contribute."),
        }
        (out_dir / f"proxy_{slug}.json").write_text(json.dumps(record, indent=2))
        b, w = record["baseline_M1_M2"], record["with_proxy_M1_M2_M3"]
        summary.append({"slug": slug, "proxy_standalone_mae": proxy["standalone_mae_pct"],
                        "mae_before": b["stats"]["mae"], "mae_after": w["stats"]["mae"],
                        "hit_before": b["stats"]["hit_rate"], "hit_after": w["stats"]["hit_rate"],
                        "verdict_before": b["verdict"], "verdict_after": w["verdict"]})
        print(f"  {slug}: proxy_MAE {proxy['standalone_mae_pct']}% | "
              f"MAE {b['stats']['mae']}->{w['stats']['mae']} "
              f"hit {b['stats']['hit_rate']}->{w['stats']['hit_rate']} | "
              f"{b['verdict']} -> {w['verdict']}")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"wrote results/sensitivity/ ({len(summary)} areas)")


if __name__ == "__main__":
    main()
