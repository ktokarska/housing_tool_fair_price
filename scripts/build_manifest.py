"""Build one pinned manifest.json covering every geography present in a snapshot dir.

Scans data/snapshots/<date>/*/ for sold.csv + epc.csv and records sha256 + row counts.
Safe to re-run; it always rewrites the full manifest from what is on disk.

    python scripts/build_manifest.py --date 2026-06-19
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rows(p: pathlib.Path) -> int:
    return sum(1 for _ in p.open()) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    root = pathlib.Path("data/snapshots") / a.date
    manifest = {"snapshot_date": a.date, "methodology_version": "2.1",
                "sources": {"land_registry": "https://landregistry.data.gov.uk/landregistry/query",
                            "epc": "https://find-energy-certificate.service.gov.uk"},
                "geographies": {}}
    for geo_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        sold, epc = geo_dir / "sold.csv", geo_dir / "epc.csv"
        if not (sold.exists() and epc.exists()):
            continue
        manifest["geographies"][geo_dir.name] = {"files": {
            "sold.csv": {"sha256": _sha(sold), "rows": _rows(sold)},
            "epc.csv": {"sha256": _sha(epc), "rows": _rows(epc)}}}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2))
    geos = ", ".join(manifest["geographies"])
    print(f"manifest covers: {geos}")


if __name__ == "__main__":
    main()
