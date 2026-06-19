"""Diagnostic: decompose calibration error by method, to see which lever could lift a PASS.

No new data. Runs each area's calibration sample (gate bypassed) and, per held-out property,
records each method's own estimate vs the real sold price. Reports per-method median APE and q80,
plus the reconciled figure, plus how correlated M1 and M2 errors are. If M1 (comps) is the bigger
error source, better comp matching (radius / bedrooms) is the lever; if M2 is, it is not.

    python scripts/diagnose_methods.py --date 2026-06-19
"""
from __future__ import annotations

import argparse
import pathlib
import statistics
import sys

sys.path.insert(0, "src")

from house_price_tool.agent import run_agent  # noqa: E402
from house_price_tool.embedding import sub_postcode_of  # noqa: E402
from house_price_tool.llm import FakeLLMClient  # noqa: E402
from house_price_tool.output import HouseResult  # noqa: E402
from house_price_tool.snapshot import load_snapshot  # noqa: E402

TYPES = ["D", "S", "T", "F"]


def _q80(xs):
    s = sorted(xs)
    return s[min(len(s) - 1, int(0.8 * len(s)))] if s else None


def _summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"n": len(xs), "median_ape": round(statistics.median(xs) * 100, 2),
            "q80_ape": round(_q80(xs) * 100, 2)}


def diagnose(slug, geo_dir, snap_root, date):
    snap = load_snapshot(snap_root)
    sold = snap.sold(slug)
    sample = sold[sold.property_type.isin(TYPES)]
    m1e, m2e, recon = [], [], []
    both = 0
    llm, judge = FakeLLMClient("ok"), FakeLLMClient("Score: 5")
    for _, row in sample.iterrows():
        price = int(row.price_paid)
        out = run_agent(snapshot_root=snap_root, geo_dir=geo_dir, geo_slug=slug,
                        sub_postcode=sub_postcode_of(row.postcode), property_type=row.property_type,
                        asking=None, today=date, run_mode="headless", skip_gate=True,
                        subject_id=str(row.unique_id), llm_client=llm, judge_client=judge)
        if not isinstance(out, HouseResult):
            continue
        est = out.estimates
        a1 = abs(est["m1"] - price) / price if est.get("m1") else None
        a2 = abs(est["m2"] - price) / price if est.get("m2") else None
        if est:
            mid = statistics.median(list(est.values()))
            recon.append(abs(mid - price) / price)
        if a1 is not None:
            m1e.append(a1)
        if a2 is not None:
            m2e.append(a2)
        if a1 is not None and a2 is not None:
            both += 1
    return {"slug": slug, "M1_comps": _summ(m1e), "M2_sqft": _summ(m2e),
            "reconciled": _summ(recon), "both_available": both}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    snap_root = pathlib.Path("data/snapshots") / a.date
    for geo_dir in sorted(p for p in pathlib.Path("geographies").iterdir() if p.is_dir()):
        d = diagnose(geo_dir.name, geo_dir, snap_root, a.date)
        print(f"\n=== {d['slug']} (both methods available on {d['both_available']} props) ===")
        for key in ("M1_comps", "M2_sqft", "reconciled"):
            s = d[key]
            print(f"  {key:12} {s}" if s else f"  {key:12} (none)")


if __name__ == "__main__":
    main()
