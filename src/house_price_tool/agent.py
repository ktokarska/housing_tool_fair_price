"""End-to-end single-run pipeline: Steps 1 to 10."""
from __future__ import annotations

from .abstain import is_abstain
from .baseline import load_baseline
from .gate import GateDecision, geography_gate
from .geography import load_geography
from .judge import explanation_gate
from .explain import generate_explanation
from .methods.m1 import method_one
from .methods.m2 import method_two
from .methods.m3 import load_avm_table, method_three
from .output import assemble_result
from .reconcile import run_reconcile
from .resolve import provenance_gate, resolve_candidates
from .retrieval import retrieve_comps
from .snapshot import load_snapshot


def _pick_subject(records, subject_id):
    if subject_id is None:
        return records[0]
    for r in records:
        if any(s.dataset == "sold" and s.row_id == subject_id for s in r.sources):
            return r
    raise ValueError(f"subject {subject_id} not in resolved set")


def run_agent(*, snapshot_root, geo_dir, geo_slug, sub_postcode, property_type,
              asking, today, llm_client, judge_client, run_mode="headless",
              subject_id=None, skip_gate=False, avm_filename="avm.csv"):
    cfg = load_geography(geo_dir)
    decision, msg, h1 = geography_gate(cfg, property_type, run_mode, today)
    # skip_gate is used by the calibration runner, which is what establishes
    # the calibration the gate checks for (chicken-and-egg bootstrap).
    if not skip_gate and decision is not GateDecision.PROCEED:
        return {"gate": decision, "message": msg, "metrics": [h1]}

    # An engine-preview (skip_gate) run on an area the gate would refuse must say so: the result
    # is withheld in production, and the numbers below are shown for evaluation only.
    disposition = None
    if skip_gate and decision is not GateDecision.PROCEED:
        reason = h1.reason.split(": ", 1)[-1]
        disposition = {
            "withheld": True,
            "gate": decision.value,
            "reason": reason,
            "coverage_unproven": "QUARANTINE" in reason,
            "note": ("Withheld in production: the geography gate refuses this area. "
                     "Engine-preview numbers are shown for evaluation only; their confidence "
                     "reflects method agreement, not proven area-level coverage."),
        }

    snap = load_snapshot(snapshot_root)
    records = resolve_candidates(snap, geo_slug, sub_postcode, property_type)
    h2 = provenance_gate(records, snap, geo_slug)
    subject = _pick_subject(records, subject_id)

    comps, h3 = retrieve_comps(subject, records, today=today)
    baseline = load_baseline(geo_dir / "market_baseline.md")
    m1 = method_one(comps, today=today, baseline=baseline)
    m2, h9 = method_two(subject, baseline)
    m3 = method_three(subject, load_avm_table(snapshot_root, geo_slug, avm_filename))

    result, h8 = run_reconcile([m1, m2, m3], asking=asking, comp_count=len(comps))
    abstain = is_abstain(result)
    explanation = generate_explanation(result, llm_client)
    h10 = explanation_gate(result, explanation, judge_client)

    return assemble_result(
        subject_label=subject.masked_address(), geography=geo_slug,
        snapshot_date=snap.date, reconcile_result=result, abstain=abstain,
        explanation=explanation, metrics=[h1, h2, h3, h9, h8, h10],
        production_disposition=disposition)
