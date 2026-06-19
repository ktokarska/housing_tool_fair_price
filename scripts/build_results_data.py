"""Aggregate per-area calibration JSON + area metadata into the results-page data bundle.

Cheap, offline, no recompute. Reads each geography's area_definition.md (for name and
sub-postcodes) and its latest calibration/<date>.json (written by calibrate_geo.py), and
emits results/<slug>.json plus results/index.json — the static data the Evals tab reads.

    python scripts/build_results_data.py --date 2026-06-19
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re


def parse_area_definition(path: pathlib.Path) -> dict:
    """Pull slug / name / sub_postcodes from the YAML-style frontmatter."""
    text = path.read_text()
    block = text.split("---")[1] if "---" in text else text
    out = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    subs = re.findall(r"\[(.*?)\]", out.get("sub_postcodes", "[]"))
    out["sub_postcodes"] = [s.strip() for s in subs[0].split(",")] if subs and subs[0] else []
    return out


def build_area(geo_dir: pathlib.Path, date: str) -> dict | None:
    cal_path = geo_dir / "calibration" / f"{date}.json"
    area_path = geo_dir / "area_definition.md"
    if not cal_path.exists():
        return None
    cal = json.loads(cal_path.read_text())
    meta = parse_area_definition(area_path) if area_path.exists() else {}
    return {
        "slug": cal["slug"],
        "name": meta.get("name", cal["slug"]),
        "sub_postcodes": meta.get("sub_postcodes", []),
        "calibration": cal,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    geos = sorted(p for p in pathlib.Path("geographies").iterdir() if p.is_dir())
    out_dir = pathlib.Path("results")
    out_dir.mkdir(exist_ok=True)
    index = []
    for geo_dir in geos:
        area = build_area(geo_dir, a.date)
        if area is None:
            print(f"  skip {geo_dir.name}: no calibration/{a.date}.json")
            continue
        (out_dir / f"{area['slug']}.json").write_text(json.dumps(area, indent=2))
        v = area["calibration"]["verdict"]["verdict"]
        index.append({"slug": area["slug"], "name": area["name"],
                      "verdict": v, "date": a.date,
                      "methods_present": area["calibration"]["methods_present"]})
        print(f"  wrote results/{area['slug']}.json — {v}")
    (out_dir / "index.json").write_text(
        json.dumps({"generated_for": a.date, "areas": index}, indent=2))
    print(f"wrote results/index.json ({len(index)} areas)")


if __name__ == "__main__":
    main()
