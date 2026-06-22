"""The 10 skeptical graders: deterministic, evidence-citing persona rubrics.

Each grader is a pure function of a captured run output (plus a small context) and returns a
Cell {grade, failed_checks, evidence}. A+ requires every check of that persona to pass. The
graders encode INTEGRITY: an honest refusal / abstain / quarantine-withhold earns A+; an
overconfident or undisclosed directional verdict fails. Determinism is required (G9 grades it),
so no randomness and no LLM lives here.

Output shapes a grader must handle:
  * valuation : has "verdict"/"estimates"/"metrics" (a HouseResult contract)
  * refusal   : has "gate"/"message"/"metrics" (the geography gate refused)
  * halt      : has "halted"/"error_type" (the pipeline refused to value on bad data)
"""
from __future__ import annotations

import dataclasses
import json
from typing import Callable, Optional

# --- the honest engine-preview disclosure contract (graders + the loop fix agree on this) ---
# A skip_gate (engine-preview) run whose geography gate would NOT proceed must carry:
#   production_disposition = {
#     "withheld": bool, "gate": str, "reason": str,
#     "coverage_unproven": bool, "note": str }
DISPOSITION_KEY = "production_disposition"


@dataclasses.dataclass
class Check:
    id: str
    passed: bool
    hard: bool
    note: str


@dataclasses.dataclass
class Cell:
    grade: str
    failed_checks: list[str]
    evidence: list[str]


def letter(checks: list[Check]) -> str:
    hard = [c for c in checks if not c.passed and c.hard]
    soft = [c for c in checks if not c.passed and not c.hard]
    if not hard and not soft:
        return "A+"
    if hard:
        return "F" if len(hard) >= 2 else "D"
    return {1: "A", 2: "B"}.get(len(soft), "C")


def _cell(checks: list[Check]) -> Cell:
    return Cell(
        grade=letter(checks),
        failed_checks=[c.id for c in checks if not c.passed],
        evidence=[f"{'OK ' if c.passed else 'XX '}{c.id}: {c.note}" for c in checks],
    )


# --------------------------- shape & semantic helpers ---------------------------
def is_halt(o: dict) -> bool:
    return bool(o.get("halted"))


def is_refusal(o: dict) -> bool:
    return "gate" in o


def is_valuation(o: dict) -> bool:
    return "verdict" in o


def metrics(o: dict) -> dict:
    return {m["gate_id"]: m for m in o.get("metrics", [])}


def h1_reason(o: dict) -> str:
    return metrics(o).get("H1", {}).get("reason", "")


def area_quarantined(o: dict) -> bool:
    return "QUARANTINE" in h1_reason(o)


def gate_would_refuse(o: dict) -> bool:
    # In a skip_gate preview the H1 record still states the real routing decision.
    return "NOT_IN_DEMO" in h1_reason(o) or "PROMPT_CALIBRATION" in h1_reason(o)


_NONDIRECTIONAL = {"INDETERMINATE", "NO VERDICT", None}


def has_directional_label(o: dict) -> bool:
    """A directional verdict STRING, regardless of the abstain flag."""
    return is_valuation(o) and o.get("verdict") not in _NONDIRECTIONAL


def is_directional(o: dict) -> bool:
    """A directional verdict that the run actually stands behind (not abstaining)."""
    if o.get("abstain"):
        return False
    return has_directional_label(o)


def disposition(o: dict) -> dict:
    return o.get(DISPOSITION_KEY) or {}


def withheld_disclosed(o: dict) -> bool:
    d = disposition(o)
    return bool(d.get("withheld")) and bool(d.get("reason"))


def coverage_caveated(o: dict) -> bool:
    return bool(disposition(o).get("coverage_unproven"))


# --------------------------------- the graders ---------------------------------
def g1_provenance(o: dict, ctx: dict) -> Cell:
    """Provenance Auditor — every figure must trace to verified source data."""
    if is_halt(o):
        return _cell([Check("g1.halt", True, True, "halted before valuing; nothing fabricated")])
    if is_refusal(o):
        return _cell([Check("g1.refusal", True, True, "refused; no figures to source")])
    m = metrics(o)
    h2 = m.get("H2")
    checks = [Check("g1.h2_present", h2 is not None, True, "H2 provenance metric present")]
    if h2:
        checks.append(Check("g1.h2_success", bool(h2["success"]), True, h2["reason"]))
    geo = o.get("geography")
    verified = geo in ctx.get("verified_geos", set())
    checks.append(Check(
        "g1.checksum_verified", verified, True,
        f"{geo} is checksum-verified in the snapshot manifest" if verified
        else f"{geo} is absent from the snapshot manifest: values rely on UNVERIFIED data"))
    checks.append(Check(
        "g1.estimates_integer",
        all(isinstance(v, int) for v in o.get("estimates", {}).values()), False,
        "every estimate is an integer pound figure"))
    return _cell(checks)


def g2_statistician(o: dict, ctx: dict) -> Cell:
    """Calibration Statistician — no directional claim the residuals cannot support."""
    if is_halt(o) or is_refusal(o):
        return _cell([Check("g2.no_claim", True, True, "no directional claim made")])
    if not is_directional(o):
        return _cell([Check("g2.abstained", True, False,
                            "abstained / non-directional on an unproven area — correct")])
    quar = area_quarantined(o)
    checks = []
    if quar:
        checks.append(Check(
            "g2.directional_disclosed", withheld_disclosed(o), True,
            "directional verdict on a quarantined area is disclosed as production-withheld"
            if withheld_disclosed(o)
            else "directional verdict on a QUARANTINE area, presented without withholding disclosure"))
        conf_ok = (o.get("confidence") != "High") or coverage_caveated(o)
        checks.append(Check(
            "g2.no_unqualified_high_confidence", conf_ok, True,
            "confidence is qualified for an area with unproven coverage" if conf_ok
            else "claims High confidence while the area's calibration is QUARANTINE (coverage ~ chance)"))
    else:
        checks.append(Check("g2.area_proven", True, False, "directional verdict on a proven area"))
    return _cell(checks)


def g3_abstention(o: dict, ctx: dict) -> Cell:
    """Abstention Hawk — abstain exactly when the methods cannot support a direction."""
    if is_halt(o) or is_refusal(o):
        return _cell([Check("g3.na", True, True, "no reconciliation stage reached")])
    abstain = bool(o.get("abstain"))
    label = has_directional_label(o)
    checks = [
        Check("g3.abstain_implies_nondirectional", not (abstain and label), True,
              "abstaining run carries no directional verdict" if not (abstain and label)
              else "abstain=True but a directional verdict label was emitted"),
        Check("g3.nonabstain_has_verdict", bool(o.get("verdict")), True,
              f"verdict present: {o.get('verdict')}"),
    ]
    low_conf = o.get("confidence") in (None, "Low")
    checks.append(Check(
        "g3.no_directional_on_low_confidence", not (low_conf and label and not abstain), True,
        "no standing directional label at low/None confidence"
        if not (low_conf and label and not abstain)
        else "directional verdict at low/None confidence"))
    h8 = metrics(o).get("H8")
    if h8:
        checks.append(Check("g3.h8_single_label", bool(h8["success"]), True, h8["reason"]))
    return _cell(checks)


def g4_retrieval(o: dict, ctx: dict) -> Cell:
    """Retrieval Skeptic — the comp set must be reliably assembled (recall@K)."""
    if is_halt(o) or is_refusal(o):
        return _cell([Check("g4.na", True, True, "retrieval stage not reached")])
    h3 = metrics(o).get("H3")
    if h3 is None:
        return _cell([Check("g4.h3_present", False, True, "no recall@K metric recorded")])
    return _cell([Check("g4.recall_meets_bar", bool(h3["success"]), True, h3["reason"])])


def g5_faithfulness(o: dict, ctx: dict) -> Cell:
    """Faithfulness Inquisitor — the prose may assert nothing the result does not contain."""
    if is_halt(o) or is_refusal(o):
        return _cell([Check("g5.na", True, True, "no explanation produced")])
    checks = []
    h10 = metrics(o).get("H10")
    if h10:
        checks.append(Check("g5.h10_number_guard", bool(h10["success"]), True, h10["reason"]))
    prose = (o.get("explanation") or "").lower()
    no_methods = not o.get("estimates") or o.get("value_range") in (None, [])
    claims_support = "methods support the stated range" in prose
    checks.append(Check(
        "g5.no_unsupported_qualitative_claim", not (no_methods and claims_support), True,
        "prose does not claim method support that the result lacks"
        if not (no_methods and claims_support)
        else "prose claims 'methods support the stated range' but the result has no methods/range"))
    flagged = "no llm call" in prose or "placeholder" in prose
    checks.append(Check("g5.placeholder_flagged", flagged, False,
                        "offline placeholder is honestly labelled"))
    return _cell(checks)


_REFUSAL_EXPECT = {
    "I4": "QUARANTINE", "I5": "no calibration", "I6": "days old", "I7": "methodology",
}


def g6_gate(o: dict, ctx: dict) -> Cell:
    """Gate Lawyer — the geography gate must route and message exactly right."""
    iid = ctx.get("input_id", "")
    if is_halt(o):
        return _cell([Check("g6.halt", True, True, "halted after gate; gate not at fault")])
    if is_refusal(o):
        checks = [
            Check("g6.message_exact", o.get("message") == "Not part of the demo, calibration needed",
                  True, f"message: {o.get('message')!r}"),
            Check("g6.decision_not_in_demo", o.get("gate") == "NOT_IN_DEMO", True,
                  f"decision: {o.get('gate')}"),
        ]
        expect = _REFUSAL_EXPECT.get(iid)
        if expect:
            checks.append(Check(
                "g6.reason_matches_cause", expect.lower() in h1_reason(o).lower(), True,
                f"refusal reason cites the right cause ({expect!r})" if expect.lower() in h1_reason(o).lower()
                else f"refusal reason {h1_reason(o)!r} does not cite expected cause {expect!r}"))
        return _cell(checks)
    # engine-preview valuation: a bypassed refusing gate must be disclosed
    if gate_would_refuse(o):
        return _cell([Check(
            "g6.bypass_disclosed", withheld_disclosed(o), True,
            "engine-preview discloses the gate would refuse in production" if withheld_disclosed(o)
            else "gate would refuse in production, but the preview does not disclose the bypass")])
    return _cell([Check("g6.gate_proceeded", True, True, "gate proceeded legitimately")])


def g7_schema(o: dict, ctx: dict) -> Cell:
    """Schema / Contract Pedant — the output contract must be complete and valid."""
    checks = []
    if is_halt(o):
        checks.append(Check("g7.halt_contract", bool(o.get("error_type")) and bool(o.get("error")),
                            True, "halt carries error_type and message"))
        return _cell(checks)
    if is_refusal(o):
        checks.append(Check("g7.refusal_contract",
                            all(k in o for k in ("gate", "message", "metrics")), True,
                            "refusal carries gate, message, metrics"))
    else:
        required = ("subject_label", "geography", "methodology_version", "snapshot_date",
                    "estimates", "verdict", "detail", "abstain", "explanation", "metrics")
        missing = [k for k in required if k not in o]
        checks.append(Check("g7.house_result_fields", not missing, True,
                            "all HouseResult fields present" if not missing else f"missing: {missing}"))
        checks.append(Check("g7.methodology_pinned", o.get("methodology_version") == "2.1", False,
                            f"methodology_version={o.get('methodology_version')}"))
    fields = ("metric", "gate_id", "score", "threshold", "success", "reason")
    ok = all(all(k in m for k in fields) for m in o.get("metrics", []))
    checks.append(Check("g7.metric_record_shape", ok, True,
                        "every metric record has the standard shape"))
    return _cell(checks)


def g8_adversary(o: dict, ctx: dict) -> Cell:
    """Adversary / Red-teamer — hunt self-contradiction and preview-as-production leakage."""
    if is_halt(o) or is_refusal(o):
        return _cell([Check("g8.clean", True, True, "no result object to contradict itself")])
    checks = []
    # 1) producing a result for a gate-refusing area without disclosing it is a leak
    if gate_would_refuse(o):
        checks.append(Check(
            "g8.no_undisclosed_leak", withheld_disclosed(o), True,
            "result for a refusing-gate area is disclosed as withheld" if withheld_disclosed(o)
            else "result emitted for an area the gate refuses, with no withholding disclosure (leak)"))
    # 2) range must bracket at least one method estimate
    rng, est = o.get("value_range"), list(o.get("estimates", {}).values())
    if rng and est:
        bracketed = any(rng[0] <= v <= rng[1] for v in est)
        checks.append(Check("g8.range_brackets_estimate", bracketed, True,
                            "value range brackets a method estimate" if bracketed
                            else f"range {rng} brackets none of the estimates {est}"))
    return _cell(checks)


def g9_reproducibility(o: dict, ctx: dict) -> Cell:
    """Reproducibility Referee — identical input must yield identical output."""
    rx: Optional[Callable[[], dict]] = ctx.get("reexecute")
    if rx is None:
        return _cell([Check("g9.no_executor", True, False, "executor not supplied; skipped")])
    a, b = rx(), rx()
    key = lambda x: json.dumps(x, sort_keys=True)
    same = key(a) == key(b) == key(o)
    return _cell([Check("g9.deterministic", same, True,
                        "byte-identical across two fresh runs" if same
                        else "output differs across runs — non-reproducible")])


def g10_honesty(o: dict, ctx: dict) -> Cell:
    """Honest-Communication Critic — communicate uncertainty plainly; never overclaim."""
    if is_halt(o):
        return _cell([Check("g10.halt_honest", True, True, "refused to value corrupt data — honest")])
    if is_refusal(o):
        return _cell([Check("g10.refusal_clear", bool(o.get("message")), True,
                            "refusal states a clear reason")])
    if not is_directional(o):
        # abstain: reward a clear statement of the data gaps
        detail = (o.get("detail") or "").lower()
        clear = any(w in detail for w in ("data gap", "indeterminate", "record the listing",
                                          "single method", "before any directional"))
        return _cell([Check("g10.abstain_explains_gaps", clear, False,
                            "abstain explains the data gaps plainly" if clear
                            else "abstain does not plainly explain why")])
    quar = area_quarantined(o)
    checks = [Check(
        "g10.withholding_communicated", withheld_disclosed(o) or not quar, True,
        "a directional read on an unproven area is plainly flagged as withheld"
        if (withheld_disclosed(o) or not quar)
        else "directional read on an unproven area with no plain withholding statement")]
    conf_ok = (o.get("confidence") != "High") or coverage_caveated(o) or not quar
    checks.append(Check("g10.no_false_precision", conf_ok, True,
                        "confidence not overstated" if conf_ok
                        else "High confidence presented as if the area's coverage were proven"))
    return _cell(checks)


@dataclasses.dataclass
class Grader:
    id: str
    persona: str
    fn: Callable[[dict, dict], Cell]


GRADERS: list[Grader] = [
    Grader("G1", "Provenance Auditor", g1_provenance),
    Grader("G2", "Calibration Statistician", g2_statistician),
    Grader("G3", "Abstention Hawk", g3_abstention),
    Grader("G4", "Retrieval Skeptic", g4_retrieval),
    Grader("G5", "Faithfulness Inquisitor", g5_faithfulness),
    Grader("G6", "Gate Lawyer", g6_gate),
    Grader("G7", "Schema/Contract Pedant", g7_schema),
    Grader("G8", "Adversary/Red-teamer", g8_adversary),
    Grader("G9", "Reproducibility Referee", g9_reproducibility),
    Grader("G10", "Honest-Communication Critic", g10_honesty),
]


def grader(gid: str) -> Grader:
    return next(g for g in GRADERS if g.id == gid)
