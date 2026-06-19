"""Blind calibration runner. The held-out sold price is used only after the agent returns."""
from __future__ import annotations

from ..agent import run_agent
from ..embedding import sub_postcode_of
from ..output import HouseResult
from ..snapshot import load_snapshot
from .residual import residual_from_result


def run_calibration(*, snapshot_root, geo_dir, geo_slug, property_types, today,
                    llm_client, judge_client, avm_filename="avm.csv"):
    snap = load_snapshot(snapshot_root)
    sold = snap.sold(geo_slug)
    sample = sold[sold.property_type.isin(property_types)]
    records = []
    n_refused = 0
    for _, row in sample.iterrows():
        subject_id = str(row.unique_id)
        sold_price = int(row.price_paid)            # held out: used only below
        out = run_agent(
            snapshot_root=snapshot_root, geo_dir=geo_dir, geo_slug=geo_slug,
            sub_postcode=sub_postcode_of(row.postcode), property_type=row.property_type,
            asking=None, today=today, run_mode="headless", subject_id=subject_id,
            avm_filename=avm_filename,
            llm_client=llm_client, judge_client=judge_client, skip_gate=True)
        if not isinstance(out, HouseResult):
            n_refused += 1
            continue
        rec = residual_from_result(subject_id, sold_price, out.to_contract())
        if rec is None:
            n_refused += 1
        else:
            records.append(rec)
    counts = {"n_sample": int(len(sample)), "n_scored": len(records),
              "n_refused": n_refused}
    return records, counts
