"""Generate a blank, pre-keyed AVM capture template for a geography's calibration sample.

Manual-capture rails for Method 3. Reads the pinned snapshot's sold.csv, emits one row per
sold property of the calibrated types, keyed by its HM Land Registry unique_id, with helper
address columns (to locate the property on a public AVM) and blank capture columns to fill
in by hand. No values are invented: blanks stay blank.

Workflow:
    1. python scripts/build_avm_template.py --slug sl6-maidenhead --types D,S,T,F --date 2026-06-19
    2. Fill avm_estimate / source_url / listing_visible (and captured_date) by hand. Partial
       fill is fine: only filled rows get Method 3.
    3. Rename avm.template.csv -> avm.csv in the same folder.
    4. Re-run scripts/calibrate_geo.py for the slug. Method 3 activates automatically.

See data/snapshots/<date>/AVM_CAPTURE.md for the column contract and the contamination rule.
"""
from __future__ import annotations

import argparse
import csv
import pathlib

import pandas as pd

# Helper columns: ignored by Method 3, included so a human can find each property on the AVM.
HELP_COLS = ["postcode", "paon", "street", "property_type", "deed_date", "price_paid"]
# Capture columns: filled by hand. Method 3 reads avm_estimate, source_url, listing_visible.
CAPTURE_COLS = ["avm_estimate", "captured_date", "source_url", "listing_visible"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--types", default="D,S,T,F")
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    types = a.types.split(",")
    snap_dir = pathlib.Path("data/snapshots") / a.date / a.slug
    sold = pd.read_csv(snap_dir / "sold.csv", dtype=str, keep_default_na=False)
    sample = sold[sold.property_type.isin(types)]
    out = snap_dir / "avm.template.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["property_key"] + HELP_COLS + CAPTURE_COLS)
        for _, r in sample.iterrows():
            w.writerow([r.unique_id] + [r[c] for c in HELP_COLS] + [""] * len(CAPTURE_COLS))
    print(f"{a.slug}: wrote {out} ({len(sample)} rows to capture; types {','.join(types)})")


if __name__ == "__main__":
    main()
