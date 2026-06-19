"""Fetch and pin real open data for UB3 (Hayes): Land Registry sold prices + EPC floor areas.

Stages (each cached to data/raw/ub3/, so re-runs resume cheaply):
  A  sold      : SPARQL pull of all UB3 sold transactions (last 24 months)
  B  epcsearch : per-postcode EPC search -> {address: certID}
  C  certs     : per-certID detail page -> floor area sqm
  D  assemble  : write data/snapshots/<date>/ub3-hayes/{sold,epc}.csv

Run a stage:  python scripts/fetch_ub3.py <stage> [--date 2026-06-19]
Run all:      python scripts/fetch_ub3.py all --date 2026-06-19

Only this script touches the network. Politeness delay between EPC requests.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

RAW = pathlib.Path("data/raw/ub3")
SPARQL = "https://landregistry.data.gov.uk/landregistry/query"
EPC = "https://find-energy-certificate.service.gov.uk"
UA = "house-price-tool/0.1 (portfolio project; open-data calibration)"
PREFIX = "UB3 "
SINCE = "2024-01-01"
_TYPE = {"detached": "D", "semi-detached": "S", "terraced": "T",
         "flat-maisonette": "F", "other": "O"}


def _get(url: str, accept: str = "text/html", retries: int = 5) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    delay = 2.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2  # exponential backoff
                continue
            raise


# ---- Stage A: Land Registry sold ----------------------------------------
def stage_sold():
    RAW.mkdir(parents=True, exist_ok=True)
    query = f"""
PREFIX ppi: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
SELECT ?t ?amount ?date ?ptype ?cat ?paon ?saon ?street ?town ?pc WHERE {{
  ?t ppi:pricePaid ?amount ;
     ppi:transactionDate ?date ;
     ppi:propertyType ?ptype ;
     ppi:transactionCategory ?cat ;
     ppi:propertyAddress ?a .
  ?a lrcommon:postcode ?pc .
  OPTIONAL {{ ?a lrcommon:paon ?paon }}
  OPTIONAL {{ ?a lrcommon:saon ?saon }}
  OPTIONAL {{ ?a lrcommon:street ?street }}
  OPTIONAL {{ ?a lrcommon:town ?town }}
  FILTER(STRSTARTS(?pc, "{PREFIX}"))
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
        _parts = g("t").rstrip("/").split("/")
        _uid = _parts[-2] if _parts[-1] == "current" else _parts[-1]
        rows.append({
            "unique_id": _uid,
            "price_paid": int(float(g("amount"))),
            "deed_date": g("date")[:10],
            "postcode": g("pc"),
            "property_type": _TYPE.get(ptype, "O"),
            "new_build": "",
            "estate_type": "F",
            "paon": g("paon"),
            "saon": g("saon"),
            "street": g("street"),
            "town": g("town"),
            "transaction_category": "B" if "additional" in g("cat").lower() else "A",
        })
    (RAW / "sold_raw.json").write_text(json.dumps(rows, indent=2))
    print(f"stage A: {len(rows)} sold rows -> {RAW/'sold_raw.json'}")
    pcs = sorted({r["postcode"] for r in rows})
    print(f"         {len(pcs)} unique postcodes")


# ---- Stage B: EPC search per postcode ------------------------------------
def stage_epcsearch():
    rows = json.loads((RAW / "sold_raw.json").read_text())
    pcs = sorted({r["postcode"] for r in rows})
    cache = RAW / "epc_search.json"
    found = json.loads(cache.read_text()) if cache.exists() else {}
    rx = re.compile(r'href="/energy-certificate/([0-9-]+)"[^>]*>\s*([^<]+?)\s*</a>')
    for i, pc in enumerate(pcs):
        if pc in found:
            continue
        url = f"{EPC}/find-a-certificate/search-by-postcode?postcode=" + urllib.parse.quote(pc)
        try:
            html = _get(url)
            found[pc] = [{"cert": m.group(1), "addr": m.group(2)} for m in rx.finditer(html)]
        except Exception as e:  # noqa: BLE001
            found[pc] = []
            print(f"  warn {pc}: {e}")
        if i % 25 == 0:
            cache.write_text(json.dumps(found))
            print(f"  epc search {i}/{len(pcs)} ({pc}: {len(found[pc])} certs)")
        time.sleep(0.25)
    cache.write_text(json.dumps(found))
    total = sum(len(v) for v in found.values())
    print(f"stage B: {total} certificates across {len(found)} postcodes -> {cache}")


# ---- Stage C: cert detail -> floor area ----------------------------------
def _match_cert(sold_row, certs) -> str | None:
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


def stage_certs():
    rows = json.loads((RAW / "sold_raw.json").read_text())
    search = json.loads((RAW / "epc_search.json").read_text())
    cache = RAW / "cert_area.json"
    areas = json.loads(cache.read_text()) if cache.exists() else {}
    rx = re.compile(r"Total floor area</dt>\s*<dd[^>]*>\s*([\d,]+)\s*square met", re.I)
    want = {}
    for r in rows:
        cert = _match_cert(r, search.get(r["postcode"], []))
        if cert:
            want[r["unique_id"]] = cert
    (RAW / "uid_to_cert.json").write_text(json.dumps(want))
    # Retry certs not yet resolved (missing OR a prior None from a 429).
    todo = [c for c in set(want.values()) if areas.get(c) is None]
    print(f"stage C: matched {len(want)}/{len(rows)} sold rows; {len(todo)} certs to fetch")
    for i, cert in enumerate(todo):
        try:
            html = _get(f"{EPC}/energy-certificate/{cert}")
            m = rx.search(html)
            areas[cert] = float(m.group(1).replace(",", "")) if m else None
        except Exception as e:  # noqa: BLE001
            areas[cert] = None
            print(f"  warn {cert}: {e}")
        if i % 50 == 0:
            cache.write_text(json.dumps(areas))
            print(f"  cert {i}/{len(todo)} resolved-so-far={sum(1 for v in areas.values() if v)}")
        time.sleep(0.6)
    cache.write_text(json.dumps(areas))
    ok = sum(1 for v in areas.values() if v)
    print(f"stage C: {ok} floor areas resolved -> {cache}")


# ---- Stage D: assemble snapshot CSVs -------------------------------------
def stage_assemble(date: str):
    rows = json.loads((RAW / "sold_raw.json").read_text())
    uid_cert = json.loads((RAW / "uid_to_cert.json").read_text())
    areas = json.loads((RAW / "cert_area.json").read_text())
    out = pathlib.Path("data/snapshots") / date / "ub3-hayes"
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
            w.writerow({"certificate_id": cert, "postcode": r["postcode"],
                        "paon": r["paon"], "street": r["street"],
                        "floor_area_sqm": area, "epc_rating": "",
                        "build_year": "", "lodgement_date": ""})
    n_epc = len(seen)
    print(f"stage D: wrote {len(rows)} sold rows, {n_epc} epc rows -> {out}")


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    date = "2026-06-19"
    if "--date" in sys.argv:
        date = sys.argv[sys.argv.index("--date") + 1]
    if stage in ("all", "sold"):
        stage_sold()
    if stage in ("all", "epcsearch"):
        stage_epcsearch()
    if stage in ("all", "certs"):
        stage_certs()
    if stage in ("all", "assemble"):
        stage_assemble(date)


if __name__ == "__main__":
    main()
