"""Build a PROXY third estimator for the M3 sensitivity experiment. NOT a real AVM.

This is an open-data, leakage-controlled stand-in built only from HM Land Registry + EPC (the
same sources as M1/M2), used solely to test whether ANY third method would move the calibration
verdict. Because it is built from the same data it is expected to be correlated with M1/M2 — so
this is a lower bound on what an independent commercial AVM might add, not a substitute for one.

It is written to avm_proxy.csv (never avm.csv) and every row's source_url is marked PROXY, so
it can never be mistaken for, or overwrite, manually captured real AVM data.

Model: OLS of log(price) on log(floor_area) + property type + sub-postcode + a linear month
trend. Per-row predictions are exact leave-one-out (PRESS: y - e/(1-h)), so no property's
prediction uses its own sold price. Duan smearing corrects the log-retransformation.

    python scripts/build_proxy_avm.py --slug sl6-maidenhead --date 2026-06-19
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from house_price_tool.snapshot import load_snapshot  # noqa: E402

PROXY_TAG = "PROXY:open-data-hedonic-OLS"


def _sub_of(pc: str) -> str:
    o, _, i = pc.partition(" ")
    return f"{o} {i[0]}" if i else o


def build_proxy(slug: str, date: str) -> dict:
    snap_root = pathlib.Path("data/snapshots") / date
    snap = load_snapshot(snap_root)
    sold = snap.sold(slug).copy()
    epc = snap.epc(slug)[["postcode", "paon", "street", "floor_area_sqm"]].copy()
    for df in (sold, epc):
        for c in ("paon", "street"):
            df[c] = df[c].astype(str)
    epc = epc.dropna(subset=["floor_area_sqm"]).drop_duplicates(["postcode", "paon", "street"])

    df = sold.merge(epc, on=["postcode", "paon", "street"], how="inner")
    df = df[(df.price_paid > 0) & (df.floor_area_sqm > 0)].copy()
    dd = pd.to_datetime(df.deed_date, errors="coerce")
    df["months"] = dd.dt.year * 12 + dd.dt.month
    df = df.dropna(subset=["months"]).reset_index(drop=True)
    if len(df) < 30:
        return {"slug": slug, "n_model": int(len(df)), "standalone_mae_pct": None,
                "note": "too few EPC-matched rows to fit a proxy"}

    df["log_area"] = np.log(df.floor_area_sqm.astype(float))
    df["months"] = df["months"] - df["months"].min()
    df["sub"] = df.postcode.map(_sub_of)

    feats = pd.concat([
        df[["log_area", "months"]].astype(float),
        pd.get_dummies(df["property_type"], prefix="t", drop_first=True).astype(float),
        pd.get_dummies(df["sub"], prefix="s", drop_first=True).astype(float),
    ], axis=1)
    X = np.column_stack([np.ones(len(df)), feats.values])
    y = np.log(df.price_paid.astype(float).values)

    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    M = np.linalg.pinv(X.T @ X)
    h = np.einsum("ij,jk,ik->i", X, M, X)        # leverage, no n*n matrix
    keep = (1 - h) > 1e-6
    smear = float(np.mean(np.exp(e[keep])))      # Duan retransformation correction
    loo_logpred = y - e / (1 - h)
    price_pred = np.exp(loo_logpred) * smear

    ape = np.abs(price_pred[keep] - df.price_paid.values[keep]) / df.price_paid.values[keep]
    out = pd.DataFrame({
        "property_key": df.unique_id.values[keep],
        "avm_estimate": np.round(price_pred[keep]).astype(int),
        "captured_date": date,
        "source_url": PROXY_TAG,
        "listing_visible": "false",
    })
    dest = snap_root / slug / "avm_proxy.csv"
    out.to_csv(dest, index=False)
    # Report median APE (the harness's own "MAE" is a median); mean is kept for transparency
    # since the hedonic has a fat tail on atypical/high-value homes it cannot price.
    return {"slug": slug, "n_model": int(keep.sum()),
            "standalone_mae_pct": round(float(np.median(ape)) * 100, 3),
            "standalone_meanape_pct": round(float(np.mean(ape)) * 100, 3),
            "path": str(dest)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    d = build_proxy(a.slug, a.date)
    print(f"{d['slug']}: proxy rows={d['n_model']} "
          f"standalone medAPE={d['standalone_mae_pct']}% (meanAPE={d.get('standalone_meanape_pct')}%) "
          f"-> {d.get('path', d.get('note'))}")


if __name__ == "__main__":
    main()
