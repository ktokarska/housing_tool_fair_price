"""Fetch and pin real open data for any UK geography: Land Registry sold + EPC floor areas.

Parameterized version of the UB3 fetcher. Stages cache to data/raw/<slug>/ so re-runs
resume cheaply (important: the EPC site rate-limits with HTTP 429; backoff is built in).

  python scripts/fetch_geo.py <stage> --prefix "W13 " --slug w13-west-ealing --date 2026-06-19

stages: sold | epcsearch | certs | assemble | all
Only this script touches the network.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request

SPARQL = "https://landregistry.data.gov.uk/landregistry/query"
EPC = "https://find-energy-certificate.service.gov.uk"
UA = "house-price-tool/0.1 (portfolio project; open-data calibration)"
SINCE = "2024-01-01"
_TYPE = {"detached": "D", "semi-detached": "S", "terraced": "T",
         "flat-maisonette": "F", "other": "O"}


def _get(url: str, accept: str = "text/html", retries: int = 6) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    delay = 2.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def stage_sold(raw, prefix):
    raw.mkdir(parents=True, exist_ok=True)
    query = f"""
PREFIX ppi: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
SELECT ?t ?amount ?date ?ptype ?cat ?paon ?saon ?street ?town ?pc WHERE {{
  ?t ppi:pricePaid ?amount ; ppi:transactionDate ?date ; ppi:propertyType ?ptype ;
     ppi:transactionCategory ?cat ; ppi:propertyAddress ?a .
  ?a lrcommon:postcode ?pc .
  OPTIONAL {{ ?a lrcommon:paon ?paon }}
  OPTIONAL {{ ?a lrcommon:saon ?saon }}
  OPTIONAL {{ ?a lrcommon:street ?street }}
  OPTIONAL {{ ?a lrcommon:town ?town }}
  FILTER(STRSTARTS(?pc, "{prefix}"))
  FILTER(?date >= "{SINCE}"^^<http://www.w3.org/2001/XMLSchema#date>)
}} ORDER BY ?date
"""
    url = SPARQL + "?" + urllib.parse.urlencode({"query": query})
    data = json.loads(_get(url, "application/sparql-results+json"))
    rows = []
    for b in data["results"]["bindings"]:
        def g(k):
            return b.get(k, {}).get("value", "")
        ptype = g("ptype").rstrip("/").split("/")[-1].lower()
        parts = g("t").rstrip("/").split("/")
        uid = parts[-2] if parts[-1] == "current" else parts[-1]
        rows.append({"unique_id": uid, "price_paid": int(float(g("amount"))),
                     "deed_date": g("date")[:10], "postcode": g("pc"),
                     "property_type": _TYPE.get(ptype, "O"), "new_build": "",
                     "estate_type": "F", "paon": g("paon"), "saon": g("saon"),
                     "street": g("street"), "town": g("town"),
                     "transaction_category": "B" if "additional" in g("cat").lower() else "A"})
    (raw / "sold_raw.json").write_text(json.dumps(rows, indent=2))
    pcs = sorted({r["postcode"] for r in rows})
    print(f"stage A: {len(rows)} sold rows, {len(pcs)} postcodes -> {raw/'sold_raw.json'}")


def stage_epcsearch(raw):
    rows = json.loads((raw / "sold_raw.json").read_text())
    pcs = sorted({r["postcode"] for r in rows})
    cache = raw / "epc_search.json"
    found = json.loads(cache.read_text()) if cache.exists() else {}
    rx = re.compile(r'href="/energy-certificate/([0-9-]+)"[^>]*>\s*([^<]+?)\s*</a>')
    for i, pc in enumerate(pcs):
        if pc in found:
            continue
        url = f"{EPC}/find-a-certificate/search-by-postcode?postcode=" + urllib.parse.quote(pc)
        try:
            found[pc] = [{"cert": m.group(1), "addr": m.group(2)} for m in rx.finditer(_get(url))]
        except Exception as e:  # noqa: BLE001
            found[pc] = []
            print(f"  warn {pc}: {e}")
        if i % 25 == 0:
            cache.write_text(json.dumps(found))
            print(f"  epc search {i}/{len(pcs)}")
        time.sleep(0.4)
    cache.write_text(json.dumps(found))
    print(f"stage B: {sum(len(v) for v in found.values())} certs across {len(found)} postcodes")


def _match_cert(sold_row, certs):
    paon = str(sold_row.get("paon", "")).strip().upper()
    street = str(sold_row.get("street", "")).strip().upper()
    if not paon:
        return None
    for c in certs:
        addr = c["addr"].upper()
        first = addr.split(",")[0].strip()
        if first == paon or first.split(" ")[0] == paon:
            if not street or street.split(" ")[0] in addr:
                return c["cert"]
    return None


def stage_certs(raw):
    rows = json.loads((raw / "sold_raw.json").read_text())
    search = json.loads((raw / "epc_search.json").read_text())
    cache = raw / "cert_area.json"
    areas = json.loads(cache.read_text()) if cache.exists() else {}
    rx = re.compile(r"Total floor area</dt>\s*<dd[^>]*>\s*([\d,]+)\s*square met", re.I)
    want = {}
    for r in rows:
        cert = _match_cert(r, search.get(r["postcode"], []))
        if cert:
            want[r["unique_id"]] = cert
    (raw / "uid_to_cert.json").write_text(json.dumps(want))
    todo = [c for c in set(want.values()) if areas.get(c) is None]
    print(f"stage C: matched {len(want)}/{len(rows)} rows; {len(todo)} certs to fetch")
    for i, cert in enumerate(todo):
        try:
            m = rx.search(_get(f"{EPC}/energy-certificate/{cert}"))
            areas[cert] = float(m.group(1).replace(",", "")) if m else None
        except Exception as e:  # noqa: BLE001
            areas[cert] = None
            print(f"  warn {cert}: {e}")
        if i % 50 == 0:
            cache.write_text(json.dumps(areas))
            print(f"  cert {i}/{len(todo)} resolved={sum(1 for v in areas.values() if v)}")
        time.sleep(0.6)
    cache.write_text(json.dumps(areas))
    print(f"stage C: {sum(1 for v in areas.values() if v)} floor areas resolved")


def stage_assemble(raw, slug, date):
    rows = json.loads((raw / "sold_raw.json").read_text())
    uid_cert = json.loads((raw / "uid_to_cert.json").read_text())
    areas = json.loads((raw / "cert_area.json").read_text())
    out = pathlib.Path("data/snapshots") / date / slug
    out.mkdir(parents=True, exist_ok=True)
    sold_cols = ["unique_id", "price_paid", "deed_date", "postcode", "property_type",
                 "new_build", "estate_type", "paon", "street", "transaction_category"]
    with (out / "sold.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sold_cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in sold_cols})
    epc_cols = ["certificate_id", "postcode", "paon", "street", "floor_area_sqm",
                "epc_rating", "build_year", "lodgement_date"]
    seen = set()
    with (out / "epc.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=epc_cols)
        w.writeheader()
        for r in rows:
            cert = uid_cert.get(r["unique_id"])
            area = areas.get(cert) if cert else None
            if not cert or not area or cert in seen:
                continue
            seen.add(cert)
            w.writerow({"certificate_id": cert, "postcode": r["postcode"], "paon": r["paon"],
                        "street": r["street"], "floor_area_sqm": area, "epc_rating": "",
                        "build_year": "", "lodgement_date": ""})
    print(f"stage D: {len(rows)} sold rows, {len(seen)} epc rows -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["sold", "epcsearch", "certs", "assemble", "all"])
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    raw = pathlib.Path("data/raw") / a.slug
    if a.stage in ("all", "sold"):
        stage_sold(raw, a.prefix)
    if a.stage in ("all", "epcsearch"):
        stage_epcsearch(raw)
    if a.stage in ("all", "certs"):
        stage_certs(raw)
    if a.stage in ("all", "assemble"):
        stage_assemble(raw, a.slug, a.date)


if __name__ == "__main__":
    main()
