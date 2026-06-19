#!/usr/bin/env python3
"""Deterministic reconciliation and verdict calculator.

Implements Section B (Steps A-D) and Step E of framework/methodology.md v2.1.
Every sweep row and dossier reconciliation must cite this script's output;
prose may explain the result but never amend it. See methodology.md
"Mechanical computation".

Usage:
    python3 verdict_calc.py input.json
    python3 verdict_calc.py - < input.json
    python3 verdict_calc.py --test

Input JSON:
{
  "label": "26 Burcot Gardens",            # optional, echoed in output
  "asking": 650000,
  "methods": {
    "m1": {"estimate": 635000, "weakness": false},
    "m2": {"estimate": 655000, "proxy_sqft": false, "proxy_band_pct": null,
            "donor": null, "weakness": false},
    "m3": {"estimate": 620000, "proxy": false, "donor": null,
            "listing_visible_on_avm": false, "weakness": false}
  },
  "H_pct": 5.0,                # high-confidence half-width; floored at 5.0
  "bias_correction_pct": 0.0,  # signed; from PASS-WITH-CORRECTION only
  "dom": 45,                   # days on market (optional)
  "reductions": 0,             # count of price reductions (optional)
  "yoy_pct": 10.1              # sub-postcode YoY (optional)
}

Omit a method entirely (or set it to null) if it is unavailable.
"""

import json
import statistics
import sys

DIRECTIONAL_SET = {
    "FAIR", "FAIR — top of range", "FAIR — bottom of range",
    "OVERPRICED", "MATERIALLY OVERPRICED", "UNDERPRICED — investigate",
    "SUSPICIOUS",
}


def reconcile(payload):
    methods = {k: v for k, v in (payload.get("methods") or {}).items() if v}
    notes = []
    warnings = []

    # --- v2.1 exclusion rules (applied before the spread) -------------------
    m3 = methods.get("m3")
    if m3 and m3.get("listing_visible_on_avm"):
        notes.append(
            "M3 excluded from reconciliation: AVM page displays the subject's "
            "live listing (live-listing contamination rule). AVM value "
            f"£{m3['estimate']:,.0f} is reference-only."
        )
        del methods["m3"]

    m2, m3 = methods.get("m2"), methods.get("m3")
    if m2 and m3 and m2.get("donor") and m2.get("donor") == m3.get("donor"):
        merged = (m2["estimate"] + m3["estimate"]) / 2
        notes.append(
            f"Same-donor rule: M2 and M3 both derive from donor "
            f"'{m2['donor']}' — collapsed to ONE method estimate "
            f"£{merged:,.0f} (mean). One data point may not count twice."
        )
        del methods["m3"]
        methods["m2"] = dict(m2, estimate=merged, weakness=True)

    cap_directional = False
    if methods.get("m2"):
        band = methods["m2"].get("proxy_band_pct")
        if band is not None and band > 10:
            cap_directional = True
            notes.append(
                f"Proxy sq ft band ±{band:.0f}% exceeds ±10%: verdict capped "
                "at non-directional (methodology Method 2, ladder step 8)."
            )

    estimates = {k: float(v["estimate"]) for k, v in methods.items()}
    n = len(estimates)
    if n == 0:
        return {
            "n_methods": 0, "confidence": None, "verdict": "NO VERDICT",
            "detail": "0 methods available — record the listing and the data gaps.",
            "notes": notes, "warnings": warnings,
        }

    # --- bias correction (Section C, PASS-WITH-CORRECTION only) -------------
    corr = float(payload.get("bias_correction_pct") or 0.0)
    if corr:
        estimates = {k: e * (1 + corr / 100) for k, e in estimates.items()}
        notes.append(f"Bias correction {corr:+.1f}% applied to all method estimates.")

    vals = sorted(estimates.values())
    median = statistics.median(vals)

    # --- Step A: spread ------------------------------------------------------
    spread = (vals[-1] - vals[0]) / median * 100 if n > 1 else 0.0

    # --- Step B: confidence and range ----------------------------------------
    H = max(5.0, float(payload.get("H_pct") or 5.0))
    if float(payload.get("H_pct") or 5.0) < 5.0:
        warnings.append(
            f"H_pct={payload.get('H_pct')} below the 5% floor — floored to 5%. "
            "The half-width may widen via q80, never narrow (methodology Section C)."
        )

    if n == 1:
        confidence = "Low"
        centre = vals[0]
        lo, hi = centre * 0.90, centre * 1.10
        notes.append("Single method available: Low confidence by default, range ±10%.")
    elif n == 2:
        centre = sum(vals) / 2
        if spread <= 10:
            confidence, lo, hi = "High", centre * (1 - H / 100), centre * (1 + H / 100)
        elif spread <= 20:
            confidence, lo, hi = "Medium", vals[0], vals[-1]
        else:
            confidence, lo, hi = "Low", vals[0], vals[-1]
    else:  # n == 3
        centre = median
        if spread <= 10:
            confidence, lo, hi = "High", median * (1 - H / 100), median * (1 + H / 100)
        elif spread <= 20:
            confidence = "Medium"
            outlier_key = max(estimates, key=lambda k: abs(estimates[k] - median))
            if methods[outlier_key].get("weakness"):
                rest = sorted(v for k, v in estimates.items() if k != outlier_key)
                lo, hi = rest[0], rest[-1]
                notes.append(
                    f"Outlier {outlier_key.upper()} excluded from range "
                    "(documented weakness)."
                )
            else:
                lo, hi = vals[0], vals[-1]
                notes.append(
                    f"Outlier {outlier_key.upper()} kept in range "
                    "(no documented weakness)."
                )
        else:
            confidence, lo, hi = "Low", vals[0], vals[-1]

    # --- Step D: low-confidence override (absolute) --------------------------
    asking = float(payload["asking"])
    if confidence == "Low" or cap_directional:
        verdict = "INDETERMINATE"
        detail = (
            f"INDETERMINATE — fair-value range £{lo:,.0f}-£{hi:,.0f}, "
            f"{'methods disagree' if n > 1 else 'single method only'}; "
            "recommend resolving data gaps (verified sq ft / full address / "
            "desktop valuation) before any directional read."
        )
    else:
        verdict, detail = step_c_verdict(asking, lo, hi)

    return {
        "label": payload.get("label"),
        "n_methods": n,
        "estimates": {k: round(v) for k, v in estimates.items()},
        "spread_pct": round(spread, 1),
        "confidence": confidence,
        "H_pct": H,
        "range": [round(lo), round(hi)],
        "midpoint": round((lo + hi) / 2),
        "asking": round(asking),
        "verdict": verdict,
        "detail": detail,
        "negotiation_note": negotiation_note(payload),
        "notes": notes,
        "warnings": warnings,
    }


def step_c_verdict(asking, lo, hi):
    width = hi - lo
    if lo <= asking <= hi:
        if asking < lo + width / 3:
            third = "lower third"
        elif asking > hi - width / 3:
            third = "upper third"
        else:
            third = "midpoint"
        return "FAIR", f"FAIR (asking sits at {third} of range)"
    if asking > hi:
        pct = (asking - hi) / hi * 100
        if pct <= 5:
            return ("FAIR — top of range",
                    f"FAIR — top of range (asking {pct:.1f}% above top of range)")
        if pct <= 15:
            return "OVERPRICED", f"OVERPRICED by {pct:.1f}% (above top of range)"
        return ("MATERIALLY OVERPRICED",
                f"MATERIALLY OVERPRICED by {pct:.1f}%")
    pct = (lo - asking) / lo * 100
    if pct <= 5:
        return ("FAIR — bottom of range",
                f"FAIR — bottom of range (asking {pct:.1f}% below bottom of range)")
    if pct <= 15:
        return ("UNDERPRICED — investigate",
                f"UNDERPRICED by {pct:.1f}% — investigate")
    return ("SUSPICIOUS",
            f"SUSPICIOUS — asking {pct:.1f}% below bottom of range "
            "(verify tenure / defect / planning / data error before treating "
            "as an opportunity)")


def negotiation_note(payload):
    parts = []
    dom = payload.get("dom")
    reductions = payload.get("reductions") or 0
    yoy = payload.get("yoy_pct")
    if yoy is not None and yoy < -5:
        parts.append("falling market (YoY < -5%): open at fair-value bottom regardless of DoM")
    elif reductions >= 2:
        parts.append("reduced twice — vendor under pressure: open at fair-value bottom")
    elif reductions == 1:
        parts.append("reduced once — vendor flexibility confirmed: open at fair-value midpoint")
    elif dom is not None and dom > 180:
        parts.append("DoM >180: open ~10% below current asking")
    elif dom is not None and dom > 90:
        parts.append("DoM >90: open ~5% below current asking")
    if yoy is not None and yoy > 5:
        parts.append("rising market (YoY > +5%): offers below fair-value midpoint unlikely to land")
    return "; ".join(parts) if parts else "no DoM/reduction/trend signal — open near fair-value midpoint"


def render(result):
    lines = []
    if result.get("label"):
        lines.append(f"## {result['label']}")
    lines.append(f"Methods available: {result['n_methods']}")
    if result.get("estimates"):
        lines.append("Estimates: " + ", ".join(
            f"{k.upper()} £{v:,.0f}" for k, v in result["estimates"].items()))
    if result.get("confidence"):
        lines.append(f"Spread: {result['spread_pct']}% — Confidence: {result['confidence']}")
        lines.append(f"Fair-value range: £{result['range'][0]:,.0f}-£{result['range'][1]:,.0f} (H=±{result['H_pct']}%)")
        lines.append(f"Asking £{result['asking']:,.0f} → VERDICT: {result['detail']}")
        lines.append(f"Negotiation note: {result['negotiation_note']}")
    else:
        lines.append(result["detail"])
    for n in result.get("notes", []):
        lines.append(f"NOTE: {n}")
    for w in result.get("warnings", []):
        lines.append(f"WARNING: {w}")
    return "\n".join(lines)


def self_test():
    # Worked example, methodology.md Section B: 650k asking, 635/655/620.
    r = reconcile({"asking": 650000, "methods": {
        "m1": {"estimate": 635000}, "m2": {"estimate": 655000},
        "m3": {"estimate": 620000}}, "dom": 45, "reductions": 0, "yoy_pct": 10.1})
    assert r["confidence"] == "High" and r["spread_pct"] == 5.5, r
    assert r["range"] == [603250, 666750], r
    assert "upper third" in r["detail"], r

    # Calibration worked example: 56 Bissley Drive (sold-price comparison aside).
    r = reconcile({"asking": 522000, "methods": {
        "m1": {"estimate": 560000}, "m2": {"estimate": 554930},
        "m3": {"estimate": 589000}}})
    assert r["confidence"] == "High" and r["range"] == [532000, 588000], r
    assert r["verdict"] == "FAIR — bottom of range", r

    # Two-method medium: calibration row 1 (Burcot Gardens).
    r = reconcile({"asking": 650000, "methods": {
        "m2": {"estimate": 738940}, "m3": {"estimate": 658000}}})
    assert r["confidence"] == "Medium" and r["range"] == [658000, 738940], r

    # Step D absolute: single method never directional.
    r = reconcile({"asking": 545000, "methods": {"m2": {"estimate": 588000}}})
    assert r["confidence"] == "Low" and r["verdict"] == "INDETERMINATE", r

    # Same-donor collapse: two methods, one donor → single-method rule.
    r = reconcile({"asking": 675000, "methods": {
        "m2": {"estimate": 632000, "donor": "254A Courthouse Road"},
        "m3": {"estimate": 633000, "donor": "254A Courthouse Road"}}})
    assert r["n_methods"] == 1 and r["verdict"] == "INDETERMINATE", r

    # Live-listing AVM contamination → M3 excluded.
    r = reconcile({"asking": 600000, "methods": {
        "m2": {"estimate": 590000},
        "m3": {"estimate": 605000, "listing_visible_on_avm": True}}})
    assert r["n_methods"] == 1 and r["verdict"] == "INDETERMINATE", r

    # Proxy band cap.
    r = reconcile({"asking": 550000, "methods": {
        "m2": {"estimate": 582000, "proxy_band_pct": 20},
        "m3": {"estimate": 639000}}})
    assert r["verdict"] == "INDETERMINATE", r

    # H floor: requesting 2.7% must floor to 5%.
    r = reconcile({"asking": 650000, "H_pct": 2.7, "methods": {
        "m1": {"estimate": 635000}, "m2": {"estimate": 655000},
        "m3": {"estimate": 620000}}})
    assert r["H_pct"] == 5.0 and r["warnings"], r

    # SUSPICIOUS band.
    r = reconcile({"asking": 400000, "methods": {
        "m1": {"estimate": 500000}, "m2": {"estimate": 505000},
        "m3": {"estimate": 495000}}})
    assert r["verdict"] == "SUSPICIOUS", r

    print("All self-tests passed.")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--test":
        self_test()
        return
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
    result = reconcile(json.loads(raw))
    print(render(result))
    print("\n--- machine-readable ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
