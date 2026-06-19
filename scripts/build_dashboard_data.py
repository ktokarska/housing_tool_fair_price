#!/usr/bin/env python3
"""Compute real per-area/per-type figures for the public HTML dashboard.

Reads the pinned snapshot CSVs (HM Land Registry Price Paid + EPC register) and
emits a JSON blob the dashboard's inline DATA object is built from. Every number
here traces to a real snapshot row: median sold price (M1), EPC-matched floor
area and price-per-sqft (M2), and a short list of real recent comparables. No
fabricated values; methods with thin data (n<5 matches) are reported unavailable.
"""
import csv, json, statistics, sys
from collections import defaultdict

SNAP = "data/snapshots/2026-06-19"
SQM_TO_SQFT = 10.7639
TYPE_MAP = {"D": "detached", "S": "semi", "T": "terraced", "F": "flat"}
RECENT_FROM = "2025-04-24"  # ~12 months before the latest deed in the snapshot
MIN_N = 5

def load_sold(geo):
    rows = []
    with open(f"{SNAP}/{geo}/sold.csv", newline="") as f:
        for r in csv.DictReader(f):
            t = TYPE_MAP.get(r["property_type"])
            if not t:
                continue
            try:
                r["_price"] = int(r["price_paid"])
            except ValueError:
                continue
            r["_type"] = t
            r["_key"] = (r["postcode"].strip().upper(), r["paon"].strip().upper(), r["street"].strip().upper())
            rows.append(r)
    return rows

def load_epc(geo):
    area = {}
    with open(f"{SNAP}/{geo}/epc.csv", newline="") as f:
        for r in csv.DictReader(f):
            try:
                sqm = float(r["floor_area_sqm"])
            except (ValueError, KeyError):
                continue
            if sqm <= 0:
                continue
            key = (r["postcode"].strip().upper(), r["paon"].strip().upper(), r["street"].strip().upper())
            # keep the first/most-plausible floor area per address
            area.setdefault(key, sqm)
    return area

def load_avm(geo):
    """Pre-computed Method 3 (public AVM proxy), keyed by Land Registry uid."""
    avm = {}
    try:
        f = open(f"{SNAP}/{geo}/avm_proxy.csv", newline="")
    except FileNotFoundError:
        return avm
    with f:
        for r in csv.DictReader(f):
            try:
                avm[r["property_key"]] = float(r["avm_estimate"])
            except (ValueError, KeyError):
                continue
    return avm

def med(xs):
    return statistics.median(xs) if xs else None

def round_to(n, step):
    return int(round(n / step) * step)

def build_geo(geo, label_meta):
    sold = load_sold(geo)
    epc = load_epc(geo)
    avm = load_avm(geo)
    by_type = defaultdict(list)
    for r in sold:
        by_type[r["_type"]].append(r)

    base = {}
    for t, rows in by_type.items():
        recent = [r for r in rows if r["deed_date"] >= RECENT_FROM]
        use = recent if len(recent) >= MIN_N else rows
        m1 = med([r["_price"] for r in use])

        # EPC-matched rows for this type: real floor area + implied £/sqft
        matched = []
        for r in rows:
            sqm = epc.get(r["_key"])
            if sqm:
                sqft = sqm * SQM_TO_SQFT
                matched.append((sqft, r["_price"] / sqft))
        sqft_typ = med([m[0] for m in matched]) if len(matched) >= MIN_N else None
        ppsqft = med([m[1] for m in matched]) if len(matched) >= MIN_N else None

        # M3: pre-computed public-AVM proxy, median over this type's matched rows
        avm_vals = [avm[r["unique_id"]] for r in rows if r["unique_id"] in avm]
        m3 = med(avm_vals) if len(avm_vals) >= MIN_N else None

        # real comps: most recent sales of this type
        comps = sorted(rows, key=lambda r: r["deed_date"], reverse=True)[:5]
        comp_out = [{
            "price": r["_price"],
            "date": r["deed_date"],
            "pc": r["postcode"],
            "id": r["unique_id"],
        } for r in comps]

        base[t] = {
            "m1": round_to(m1, 1000) if m1 else None,
            "m3": round_to(m3, 1000) if m3 else None,
            "m3n": len(avm_vals),
            "n": len(rows),
            "nRecent": len(recent),
            "sqft": round(sqft_typ) if sqft_typ else None,
            "ppsqft": round(ppsqft) if ppsqft else None,
            "epcMatches": len(matched),
            "comps": comp_out,
        }

    out = dict(label_meta)
    out["matchRate"] = round(100 * len(epc) / max(1, len({r["_key"] for r in sold})))
    out["m3Avail"] = round(100 * sum(1 for r in sold if r["unique_id"] in avm) / max(1, len(sold)))
    out["base"] = base
    out["soldRows"] = len(sold)
    out["epcRows"] = len(epc)
    return out

GEOS = {
    "w13-west-ealing": {"region": "London", "area": "W13 · West Ealing",
                        "label": "W13 · West Ealing", "subPostcodes": "W13 0 / 8 / 9"},
    "ub3-hayes": {"region": "London", "area": "UB3 · Hayes",
                  "label": "UB3 · Hayes (Hillingdon)", "subPostcodes": "UB3 1–5"},
    "sl6-maidenhead": {"region": "Berkshire", "area": "SL6 · Maidenhead",
                       "label": "SL6 · Maidenhead", "subPostcodes": "SL6 0–9"},
}

# Calibration results, transcribed from each geographies/<slug>/calibration/2026-06-19.md
# back-test report. All three areas returned QUARANTINE. m3Avail is filled from the
# computed AVM-proxy coverage so the eval panel matches the live valuation engine.
EVALS = {
    "w13-west-ealing": dict(verdict="QUARANTINE", calDate="2026-06-19", ageDays=0, version="2.1",
        sample=895, scored=671, refused=224, N=671,
        mae=10.9, bias=1.7, q80=25.9, hitRate=33.3, hitCI=[29.1, 37.9], highTier=28.9,
        abstain=dict(precision=0.64, recall=0.42)),
    "ub3-hayes": dict(verdict="QUARANTINE", calDate="2026-06-19", ageDays=0, version="2.1",
        sample=926, scored=764, refused=162, N=764,
        mae=10.0, bias=4.9, q80=25.0, hitRate=40.6, hitCI=[35.9, 45.6], highTier=39.9,
        abstain=dict(precision=0.57, recall=0.58)),
    "sl6-maidenhead": dict(verdict="QUARANTINE", calDate="2026-06-19", ageDays=0, version="2.1",
        sample=2605, scored=2069, refused=536, N=2069,
        mae=10.3, bias=0.0, q80=23.0, hitRate=33.2, hitCI=[30.7, 35.8], highTier=28.8,
        abstain=dict(precision=0.59, recall=0.42)),
}
BEDS = {"detached": 4, "semi": 3, "terraced": 3, "flat": 2}
TYPE_ORDER = ["detached", "semi", "terraced", "flat"]

def emit_js(result):
    """Print the inline `var DATA = {...}` block for the dashboard."""
    def num(x):
        return "null" if x is None else str(x)
    out = ["var DATA = {"]
    for geo, o in result.items():
        m = GEOS[geo]
        out.append(f'  "{geo}": {{')
        out.append(f'    region:"{m["region"]}", area:"{m["area"]}", label:"{m["label"]}", subPostcodes:"{m["subPostcodes"]}",')
        out.append('    state:"quarantine", certified:false,')
        out.append('    base:{')
        for t in TYPE_ORDER:
            b = o["base"].get(t)
            if not b:
                continue
            out.append(f'      {t}:{{m1:{num(b["m1"])},m3:{num(b["m3"])},sqft:{num(b["sqft"])},ppsqft:{num(b["ppsqft"])},beds:{BEDS[t]},n:{b["n"]},nRecent:{b["nRecent"]},epcMatches:{b["epcMatches"]},m3n:{b["m3n"]},comps:[')
            for c in b["comps"]:
                out.append(f'        {{price:{c["price"]},date:"{c["date"]}",pc:"{c["pc"]}",id:"{c["id"]}"}},')
            out.append('      ]},')
        out.append('    },')
        e = EVALS[geo]
        out.append('    evals:{')
        out.append(f'      verdict:"{e["verdict"]}", calDate:"{e["calDate"]}", ageDays:{e["ageDays"]}, version:"{e["version"]}",')
        out.append(f'      sample:{e["sample"]}, scored:{e["scored"]}, refused:{e["refused"]}, N:{e["N"]},')
        out.append(f'      mae:{e["mae"]}, bias:{e["bias"]}, q80:{e["q80"]}, hitRate:{e["hitRate"]}, hitCI:[{e["hitCI"][0]},{e["hitCI"][1]}], highTier:{e["highTier"]},')
        out.append(f'      abstain:{{precision:{e["abstain"]["precision"]},recall:{e["abstain"]["recall"]}}}, matchRate:{o["matchRate"]}, m3Avail:{o["m3Avail"]}')
        out.append('    }')
        out.append('  },')
    out.append('};')
    out.append('var AREA_ORDER = ' + json.dumps(list(result.keys())) + ';')
    print("\n".join(out))

result = {geo: build_geo(geo, meta) for geo, meta in GEOS.items()}
if "--js" in sys.argv:
    emit_js(result)
else:
    json.dump(result, sys.stdout, indent=2)
    print()
