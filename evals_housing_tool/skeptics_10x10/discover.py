"""Discover REAL input values from the pinned snapshot + geography configs.

Run once to choose concrete, non-fabricated inputs for the 10x10 eval:

    python -m evals_housing_tool.skeptics_10x10.discover
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, "src")

from house_price_tool import METHODOLOGY_VERSION  # noqa: E402
from house_price_tool.geography import load_geography  # noqa: E402
from house_price_tool.resolve import resolve_candidates  # noqa: E402
from house_price_tool.snapshot import load_snapshot  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def snapshot_paths() -> dict:
    snaps = sorted((ROOT / "data" / "snapshots").glob("*"))
    geo = {p.name: p for p in sorted((ROOT / "geographies").glob("*")) if p.is_dir()}
    return {"snapshot_root": snaps[-1], "geo_dirs": geo}


def sample_subjects(snap, slug, sub_postcode, property_type):
    recs = resolve_candidates(snap, slug, sub_postcode, property_type)
    return recs


def main() -> None:
    p = snapshot_paths()
    print(f"methodology_version = {METHODOLOGY_VERSION}")
    print(f"snapshot_root       = {p['snapshot_root']}")
    snap = load_snapshot(p["snapshot_root"])
    for slug, gdir in p["geo_dirs"].items():
        cfg = load_geography(gdir)
        c = cfg.calibration
        print(f"\n== {slug}  ({cfg.name})")
        print(f"   calibration: exists={c.exists} date={c.date} verdict={c.verdict!r} "
              f"ver={c.methodology_version} types={sorted(c.types_covered)}")
        print(f"   sub_postcodes: {cfg.sub_postcodes}")
        for spc in cfg.sub_postcodes:
            for ptype in ["S", "T", "D", "F"]:
                recs = resolve_candidates(snap, slug, spc, ptype)
                if not recs:
                    continue
                with_epc = sum(1 for r in recs if r.epc is not None)
                no_epc = [r for r in recs if r.epc is None]
                print(f"   [{spc} {ptype}] n={len(recs)} with_epc={with_epc} no_epc={len(no_epc)}")
                for r in recs[:3]:
                    sid = next((s.row_id for s in r.sources if s.dataset == "sold"), "?")
                    epc_val = r.epc if r.epc is not None else "NONE"
                    print(f"        subj={sid} type={r.property_type} epc={epc_val} "
                          f"sold={r.sold_price} tenure={r.tenure}")
                if no_epc:
                    r = no_epc[0]
                    sid = next((s.row_id for s in r.sources if s.dataset == "sold"), "?")
                    print(f"        NO-EPC subj={sid} type={r.property_type} sold={r.sold_price}")


if __name__ == "__main__":
    main()
