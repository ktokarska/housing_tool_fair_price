"""One-time builder for the pinned open-data snapshot. Run by hand, not at agent time.

Run:
    python -m scripts.build_snapshot --date 2026-06-19

Fetches HM Land Registry Price Paid (SPARQL) and the EPC register for each
configured geography, writes data/snapshots/<date>/<geo>/{sold,epc}.csv plus
manifest.json. Only this script touches the network.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib

# Sub-postcode prefixes per demo geography. W13 baseline is built from this run.
GEOGRAPHIES = {
    "sl6-maidenhead": ["SL6 "],
    "w13-west-ealing": ["W13 "],
    "ub3-hayes": ["UB3 "],
}
_TYPE = {"detached": "D", "semi-detached": "S", "terraced": "T",
         "flat-maisonette": "F", "other": "O"}


def parse_lr_rows(sparql_json: dict) -> list[dict]:
    rows = []
    for b in sparql_json["results"]["bindings"]:
        def g(k):
            return b.get(k, {}).get("value")
        ptype = (g("propertyType") or "").rstrip("/").split("/")[-1].lower()
        rows.append({
            "unique_id": g("transactionId"),
            "price_paid": int(float(g("pricePaid"))),
            "deed_date": (g("transactionDate") or "")[:10],
            "postcode": g("postcode"),
            "property_type": _TYPE.get(ptype, "O"),
            "paon": g("paon"),
            "street": g("street"),
            "transaction_category": (g("transactionCategory") or "").split("/")[-1] or "A",
        })
    return rows


def parse_epc_rows(search_json: dict) -> list[dict]:
    rows = []
    for r in search_json["rows"]:
        rows.append({
            "certificate_id": r.get("lmk-key") or r.get("certificateHash"),
            "postcode": r.get("postcode"),
            "paon": str(r.get("paon") or r.get("address1", "").split(" ")[0]),
            "street": r.get("street") or " ".join(r.get("address1", "").split(" ")[1:]),
            "floor_area_sqm": float(r["total-floor-area"]),
            "build_year": _age_to_year(r.get("construction-age-band") or r.get("build_year")),
            "lodgement_date": r.get("lodgement-date"),
        })
    return rows


def _age_to_year(band) -> int | None:
    if band is None:
        return None
    digits = "".join(c for c in str(band) if c.isdigit())
    return int(digits[:4]) if len(digits) >= 4 else None


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_snapshot(out_dir, date, geo, sold_rows, epc_rows) -> dict:
    geo_dir = pathlib.Path(out_dir) / geo
    geo_dir.mkdir(parents=True, exist_ok=True)
    frag = {"files": {}}
    for fname, rows, cols in [
        ("sold.csv", sold_rows, ["unique_id", "price_paid", "deed_date", "postcode",
                                 "property_type", "paon", "street", "transaction_category"]),
        ("epc.csv", epc_rows, ["certificate_id", "postcode", "paon", "street",
                               "floor_area_sqm", "build_year", "lodgement_date"]),
    ]:
        fpath = geo_dir / fname
        with fpath.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})
        frag["files"][fname] = {"sha256": _sha256(fpath), "rows": len(rows)}
    return frag


def main():  # pragma: no cover - network and CLI glue
    import argparse
    import requests  # local import keeps the agent package free of requests

    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    out = pathlib.Path("data/snapshots") / args.date
    manifest = {"snapshot_date": args.date, "methodology_version": "2.1",
                "sources": {"land_registry": "https://landregistry.data.gov.uk/landregistry/query",
                            "epc": "https://find-energy-certificate.service.gov.uk"},
                "geographies": {}}
    for geo, prefixes in GEOGRAPHIES.items():
        sold_rows, epc_rows = _fetch_geo(requests, prefixes)  # implement per data_sources.md
        manifest["geographies"][geo] = write_snapshot(out, args.date, geo, sold_rows, epc_rows)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
