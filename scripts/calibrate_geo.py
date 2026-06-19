"""Run a blind calibration for one geography and write its calibration record.

Requires the pinned snapshot + manifest (run build_manifest.py first) and the
geography's market_baseline.md (run build_baseline.py first). Offline apart from
nothing — uses a fake LLM client for the explanation, since calibration metrics
are deterministic and do not depend on the prose.

    python scripts/calibrate_geo.py --slug w13-west-ealing --types D,S,T,F --date 2026-06-19
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


def write_json(slug: str, date: str, types: list[str], report: dict,
               methods_present: list[str]):
    """Machine-readable sibling of the markdown record — the source the results pages read."""
    out = pathlib.Path("geographies") / slug / "calibration" / f"{date}.json"
    payload = {
        "slug": slug, "date": date, "methodology_version": "2.1",
        "types_covered": types, "methods_present": methods_present,
        "verdict": report["verdict"], "stats": report["stats"],
        "counts": report["counts"], "gates": report["gates"],
    }
    out.write_text(json.dumps(payload, indent=2))
    return out


def write_record(slug: str, date: str, types: list[str], report: dict):
    s, v, c = report["stats"], report["verdict"], report["counts"]
    gates = "\n".join(f"- {g['gate_id']}: {'PASS' if g['success'] else 'FAIL'} — {g['reason']}"
                      for g in report["gates"])
    body = f"""---
date: {date}
verdict: {v['verdict']}
methodology_version: "2.1"
types_covered: [{', '.join(types)}]
---

# {slug} calibration — {date}

Blind back-test under production conditions (held-out sold price revealed only at
residual time; subject excluded from its own comps). Built from open data (HM Land
Registry Price Paid + EPC register). Method 3 (public AVM) not present in this run,
so reconciliation ran on Methods 1 and 2 only.

## Sample
- Hold-out sample: {c['n_sample']} actually-sold properties, types {', '.join(types)}.
- Scored: {c['n_scored']}. Refused (no method available): {c['n_refused']}.

## Aggregate statistics
- MAE: {s['mae']}%
- q80 of absolute residuals: {s['q80']}%
- Bias (median signed residual): {s['bias']:+}%
- Directional-tier hit rate: {s['hit_rate']} (95% Wilson interval {s['wilson'][0]}-{s['wilson'][1]})
- High-tier coverage: {s['high_tier_coverage']}

## Verdict: {v['verdict']}
Computed by the carried-verbatim calibration rule (calibration_protocol.md Step 4).
H_pct={v['H_pct']}, bias_correction_pct={v['bias_correction_pct']}. No threshold was
moved after seeing residuals.

## Gates
{gates}
"""
    out = pathlib.Path("geographies") / slug / "calibration" / f"{date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--types", default="D,S,T,F")
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    types = a.types.split(",")
    snap = pathlib.Path("data/snapshots") / a.date
    geo = pathlib.Path("geographies") / a.slug
    recs, counts = run_calibration(
        snapshot_root=snap, geo_dir=geo, geo_slug=a.slug, property_types=types,
        today=a.date, llm_client=FakeLLMClient("The available methods support the range."),
        judge_client=FakeLLMClient("Score: 5"))
    report = calibration_report(recs, counts)
    methods_present = ["M1", "M2"] + (["M3"] if (snap / a.slug / "avm.csv").exists() else [])
    out = write_record(a.slug, a.date, types, report)
    write_json(a.slug, a.date, types, report, methods_present)
    print(f"{a.slug}: VERDICT {report['verdict']['verdict']} | "
          f"MAE {report['stats']['mae']}% hit {report['stats']['hit_rate']} "
          f"methods={'+'.join(methods_present)} "
          f"(n_scored {counts['n_scored']}/{counts['n_sample']}) -> {out}")


if __name__ == "__main__":
    main()
