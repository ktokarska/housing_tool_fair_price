"""Build Valuation-tab sample data: one worked subject per area.

Offline, reproducible (FakeLLM for the prose, so no API key and no network). For each area it
emits results/valuation_<slug>.json with two blocks:

  * production    — what the public page actually returns for this area today. All three demo
                    areas are QUARANTINE, so the geography gate refuses and no verdict shows.
  * engine_preview — the same subject run with the gate bypassed, so the design tool has real
                    numbers for the result block (estimate, range, confidence, verdict, the
                    per-method estimates, the per-run gates H1/H2/H3/H8/H9/H10). Clearly
                    labelled: in production this result is withheld.

Nothing is fabricated. The explanation prose is a flagged offline placeholder (no LLM call);
every pound figure comes from the deterministic engine.

    python scripts/build_valuation_example.py --date 2026-06-19
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, "src")

from house_price_tool.agent import run_agent  # noqa: E402
from house_price_tool.gate import GateDecision  # noqa: E402
from house_price_tool.geography import load_geography  # noqa: E402
from house_price_tool.llm import FakeLLMClient  # noqa: E402
from house_price_tool.output import HouseResult  # noqa: E402
from house_price_tool.resolve import resolve_candidates  # noqa: E402
from house_price_tool.snapshot import load_snapshot  # noqa: E402

PLACEHOLDER = ("Placeholder rationale (offline sample, no LLM call). The available methods "
               "support the stated range.")
TYPE_ORDER = ["S", "T", "D", "F"]


def _sold_id(rec) -> str:
    return next((s.row_id for s in rec.sources if s.dataset == "sold"), "")


def _agent_kwargs(snap_root, geo_dir, slug, sub, ptype, sid, asking, date):
    return dict(snapshot_root=snap_root, geo_dir=geo_dir, geo_slug=slug,
                sub_postcode=sub, property_type=ptype, subject_id=sid, asking=asking,
                today=date, run_mode="headless", skip_gate=True,
                llm_client=FakeLLMClient(PLACEHOLDER), judge_client=FakeLLMClient("Score: 5"))


def pick_subject(snap_root, geo_dir, slug, snap, cfg, date, budget=60):
    """First subject yielding a complete, non-abstaining result (M1 and M2 both present)."""
    tried = 0
    fallback = None
    for sub in cfg.sub_postcodes:
        for ptype in TYPE_ORDER:
            for rec in resolve_candidates(snap, slug, sub, ptype)[:6]:
                if tried >= budget:
                    return fallback
                tried += 1
                sid = _sold_id(rec)
                out = run_agent(**_agent_kwargs(snap_root, geo_dir, slug, sub, ptype, sid,
                                                None, date))
                if not isinstance(out, HouseResult):
                    continue
                fallback = fallback or (sub, ptype, sid)
                est = out.estimates
                if est.get("m1") and est.get("m2") and not out.abstain:
                    return sub, ptype, sid
    return fallback


def build_area(snap_root, geo_dir, slug, date):
    cfg = load_geography(geo_dir)
    snap = load_snapshot(snap_root)

    # Production behaviour: real gate, headless (public-page) mode.
    decision, message, h1 = None, None, None
    prod = run_agent(snapshot_root=snap_root, geo_dir=geo_dir, geo_slug=slug,
                     sub_postcode=cfg.sub_postcodes[0], property_type="S", asking=None,
                     today=date, run_mode="headless", skip_gate=False,
                     llm_client=FakeLLMClient(PLACEHOLDER), judge_client=FakeLLMClient("Score: 5"))
    production = {
        "run_mode": "headless",
        "gate": prod["gate"].value if isinstance(prod, dict) else GateDecision.PROCEED.value,
        "message": prod["message"] if isinstance(prod, dict) else "calibration valid",
        "reason": prod["metrics"][0].reason if isinstance(prod, dict) else "",
        "verdict_shown": not isinstance(prod, dict),
    }

    picked = pick_subject(snap_root, geo_dir, slug, snap, cfg, date)
    if picked is None:
        return {"slug": slug, "name": cfg.name, "production": production,
                "engine_preview": None}
    sub, ptype, sid = picked
    sold_row = snap.sold(slug).set_index("unique_id").loc[sid]
    asking = int(sold_row.price_paid)  # real sold price, used as a demo asking
    result = run_agent(**_agent_kwargs(snap_root, geo_dir, slug, sub, ptype, sid, asking, date))
    preview = result.to_contract()
    preview["asking"] = asking
    preview["explanation_is_placeholder"] = True
    preview["disclaimer"] = (
        f"Gate bypassed for illustration. {slug} is QUARANTINE, so production withholds "
        "this result. Asking shown is the property's real sold price.")
    return {"slug": slug, "name": cfg.name, "production": production, "engine_preview": preview}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-06-19")
    a = ap.parse_args()
    snap_root = pathlib.Path("data/snapshots") / a.date
    out_dir = pathlib.Path("results")
    out_dir.mkdir(exist_ok=True)
    for geo_dir in sorted(p for p in pathlib.Path("geographies").iterdir() if p.is_dir()):
        slug = geo_dir.name
        area = build_area(snap_root, geo_dir, slug, a.date)
        (out_dir / f"valuation_{slug}.json").write_text(json.dumps(area, indent=2, default=str))
        pv = area["engine_preview"]
        tag = f"{pv['verdict']} (range {pv['value_range']})" if pv else "no complete subject"
        print(f"  wrote results/valuation_{slug}.json — gate {area['production']['gate']}; preview {tag}")


if __name__ == "__main__":
    main()
