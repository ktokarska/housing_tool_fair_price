"""Build a geography's area_definition.md and market_baseline.md from fetched raw data.

Deterministic, offline. Reads data/raw/<slug>/{sold_raw,uid_to_cert,cert_area}.json,
computes type-segmented £/sq ft (cells with n>=5) and per-sub-postcode YoY, and writes
geographies/<slug>/{area_definition.md, market_baseline.md}.

    python scripts/build_baseline.py --slug w13-west-ealing --name "West Ealing (W13)"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
from collections import defaultdict

SQFT = 10.764
TODAY = dt.date(2026, 6, 19)
TYPES = ["D", "S", "T", "F"]


def sub_of(pc: str) -> str:
    o, _, i = pc.partition(" ")
    return f"{o} {i[0]}" if i else o


def _in(d: str, lo: dt.date, hi: dt.date) -> bool:
    x = dt.date.fromisoformat(d[:10])
    return lo <= x < hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    raw = pathlib.Path("data/raw") / a.slug
    rows = json.loads((raw / "sold_raw.json").read_text())
    uid_cert = json.loads((raw / "uid_to_cert.json").read_text())
    areas = json.loads((raw / "cert_area.json").read_text())

    psqft = defaultdict(list)
    for r in rows:
        cert = uid_cert.get(r["unique_id"])
        area = areas.get(cert) if cert else None
        if not area:
            continue
        psqft[(sub_of(r["postcode"]), r["property_type"])].append(r["price_paid"] / (area * SQFT))

    subs = sorted({sub_of(r["postcode"]) for r in rows})

    def cell(s, t):
        v = psqft.get((s, t), [])
        return str(round(statistics.median(v))) if len(v) >= 5 else "-"

    def yoy(s):
        rec = [r["price_paid"] for r in rows if sub_of(r["postcode"]) == s
               and _in(r["deed_date"], dt.date(2025, 6, 19), TODAY)]
        pri = [r["price_paid"] for r in rows if sub_of(r["postcode"]) == s
               and _in(r["deed_date"], dt.date(2024, 6, 19), dt.date(2025, 6, 19))]
        if len(rec) >= 5 and len(pri) >= 5:
            return round((statistics.median(rec) / statistics.median(pri) - 1) * 100, 1)
        return 0.0

    geo = pathlib.Path("geographies") / a.slug
    (geo / "calibration").mkdir(parents=True, exist_ok=True)
    (geo / "area_definition.md").write_text(
        f"---\nslug: {a.slug}\nname: {a.name}\nsub_postcodes: [{', '.join(subs)}]\n---\n\n"
        f"{a.name}. Built from open data (HM Land Registry Price Paid + EPC register), "
        "2024-01 to 2026.\n")

    lines = [f"# Market Baseline — {a.name}", "",
             f"**Geography slug:** {a.slug}",
             "**Built:** 2026-06-19 from HM Land Registry Price Paid + EPC register (open data).",
             "", "## Sub-postcode YoY rates (nominal)", "",
             "| Sub-PC | YoY % | Source | Date pulled | Notes |",
             "|---|---|---|---|---|"]
    for s in subs:
        lines.append(f"| {s} | {yoy(s)}% | HM Land Registry Price Paid "
                     "(recent-12mo vs prior-12mo median) | 2026-06-19 | computed from open data |")
    lines += ["", "## Type-segmented £/sq ft", "",
              "| Sub-PC | Detached | Semi-Det | Terraced | Flat | Source notes |",
              "|---|---|---|---|---|---|"]
    for s in subs:
        lines.append(f"| {s} | {cell(s, 'D')} | {cell(s, 'S')} | {cell(s, 'T')} | {cell(s, 'F')} | "
                     "Land Registry x EPC matched median £/sq ft; cells with n<5 shown as - |")
    lines += ["", "Cells marked - have fewer than 5 EPC-matched transactions and are treated "
              "as no-segment (Method 2 unavailable there).", ""]
    (geo / "market_baseline.md").write_text("\n".join(lines))
    print(f"wrote geographies/{a.slug}/area_definition.md and market_baseline.md "
          f"({len(subs)} sub-postcodes)")


if __name__ == "__main__":
    main()
