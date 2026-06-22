"""Task 4 tests: each grader rewards correct behaviour and fails its anti-pattern."""
import copy

from evals_housing_tool.skeptics_10x10.graders import grader

# Reality: the snapshot manifest only checksum-verifies these two (sl6 is absent).
VERIFIED = {"ub3-hayes", "w13-west-ealing"}


def _metric(gid, success=True, reason="ok", score=1.0, threshold=1.0, metric="m"):
    return {"metric": metric, "gate_id": gid, "score": score, "threshold": threshold,
            "success": success, "reason": reason}


def clean_preview():
    """An honest engine-preview: directional, but withholding + coverage are disclosed."""
    return {
        "subject_label": "x", "geography": "ub3-hayes", "methodology_version": "2.1",
        "snapshot_date": "2026-06-19", "estimates": {"m1": 553673, "m2": 508646},
        "confidence": "High", "value_range": [500000, 560000],
        "verdict": "UNDERPRICED", "detail": "UNDERPRICED by 14.8%", "abstain": False,
        "explanation": "Placeholder rationale (offline sample, no LLM call). "
                       "The available methods support the stated range.",
        "production_disposition": {
            "withheld": True, "gate": "NOT_IN_DEMO",
            "reason": "calibration verdict 'QUARANTINE' does not permit verdicts",
            "coverage_unproven": True,
            "note": "Withheld in production; engine-preview numbers shown for evaluation only."},
        "metrics": [
            _metric("H1", reason="ub3-hayes: NOT_IN_DEMO (calibration verdict 'QUARANTINE' does not permit verdicts)"),
            _metric("H2", reason="all figures trace to snapshot rows"),
            _metric("H3", reason="20/20 rule-valid comps retrieved", score=1.0, threshold=0.95),
            _metric("H9"), _metric("H8", reason="verdict 'UNDERPRICED'"),
            _metric("H10", reason="number_match ok; faithfulness 5")],
    }


def clean_refusal(iid_reason="calibration verdict 'QUARANTINE' does not permit verdicts"):
    return {"gate": "NOT_IN_DEMO", "message": "Not part of the demo, calibration needed",
            "metrics": [_metric("H1", reason=f"sl6-maidenhead: NOT_IN_DEMO ({iid_reason})")]}


def clean_halt():
    return {"halted": True, "error_type": "SnapshotIntegrityError", "error": "checksum mismatch"}


def clean_abstain():
    return {
        "subject_label": "x", "geography": "ub3-hayes", "methodology_version": "2.1",
        "snapshot_date": "2026-06-19", "estimates": {}, "confidence": None,
        "value_range": None, "verdict": "NO VERDICT",
        "detail": "0 methods available - record the listing and the data gaps.", "abstain": True,
        "explanation": "Placeholder rationale (offline sample, no LLM call). No method was available.",
        "production_disposition": {"withheld": True, "gate": "NOT_IN_DEMO", "reason": "quarantine",
                                   "coverage_unproven": True, "note": "withheld"},
        "metrics": [_metric("H1", reason="ub3-hayes: NOT_IN_DEMO (... 'QUARANTINE' ...)"),
                    _metric("H2"), _metric("H3", reason="1/1", score=1.0, threshold=0.95),
                    _metric("H9"), _metric("H8"), _metric("H10")],
    }


def ctx(iid="I3", reexecute=None):
    return {"verified_geos": VERIFIED, "input_id": iid, "reexecute": reexecute}


# ------------------------------- G1 -------------------------------
def test_g1_rewards_verified_provenance():
    assert grader("G1").fn(clean_preview(), ctx()).grade == "A+"

def test_g1_fails_unverified_geography():
    o = clean_preview(); o["geography"] = "sl6-maidenhead"  # absent from manifest
    assert grader("G1").fn(o, ctx()).grade != "A+"

def test_g1_fails_orphan_value():
    o = clean_preview()
    o["metrics"][1] = _metric("H2", success=False, reason="orphan comp with no snapshot row")
    assert grader("G1").fn(o, ctx()).grade != "A+"


# ------------------------------- G2 -------------------------------
def test_g2_rewards_disclosed_preview():
    assert grader("G2").fn(clean_preview(), ctx()).grade == "A+"

def test_g2_fails_undisclosed_directional_on_quarantine():
    o = clean_preview(); o.pop("production_disposition")
    assert grader("G2").fn(o, ctx()).grade != "A+"

def test_g2_fails_unqualified_high_confidence():
    o = clean_preview(); o["production_disposition"]["coverage_unproven"] = False
    assert grader("G2").fn(o, ctx()).grade != "A+"


# ------------------------------- G3 -------------------------------
def test_g3_rewards_consistent_abstain():
    assert grader("G3").fn(clean_abstain(), ctx()).grade == "A+"

def test_g3_fails_directional_while_abstaining():
    o = clean_abstain(); o["abstain"] = True; o["verdict"] = "UNDERPRICED"
    assert grader("G3").fn(o, ctx()).grade != "A+"


# ------------------------------- G4 -------------------------------
def test_g4_rewards_recall_met():
    assert grader("G4").fn(clean_preview(), ctx()).grade == "A+"

def test_g4_fails_recall_below_bar():
    o = clean_preview()
    o["metrics"][2] = _metric("H3", success=False, reason="11/19 retrieved", score=0.58, threshold=0.95)
    assert grader("G4").fn(o, ctx()).grade != "A+"


# ------------------------------- G5 -------------------------------
def test_g5_rewards_faithful_prose():
    assert grader("G5").fn(clean_preview(), ctx()).grade == "A+"

def test_g5_fails_unsupported_claim_when_no_methods():
    o = clean_abstain()
    o["explanation"] = "Placeholder (no LLM call). The available methods support the stated range."
    assert grader("G5").fn(o, ctx()).grade != "A+"


# ------------------------------- G6 -------------------------------
def test_g6_rewards_correct_refusal():
    assert grader("G6").fn(clean_refusal(), ctx("I4")).grade == "A+"

def test_g6_fails_wrong_message():
    o = clean_refusal(); o["message"] = "ok proceeding"
    assert grader("G6").fn(o, ctx("I4")).grade != "A+"

def test_g6_fails_undisclosed_bypass():
    o = clean_preview(); o.pop("production_disposition")
    assert grader("G6").fn(o, ctx("I3")).grade != "A+"


# ------------------------------- G7 -------------------------------
def test_g7_rewards_valid_contract():
    assert grader("G7").fn(clean_preview(), ctx()).grade == "A+"

def test_g7_fails_missing_field():
    o = clean_preview(); o.pop("snapshot_date")
    assert grader("G7").fn(o, ctx()).grade != "A+"


# ------------------------------- G8 -------------------------------
def test_g8_rewards_consistent_result():
    assert grader("G8").fn(clean_preview(), ctx()).grade == "A+"

def test_g8_fails_undisclosed_leak():
    o = clean_preview(); o.pop("production_disposition")
    assert grader("G8").fn(o, ctx()).grade != "A+"

def test_g8_fails_range_not_bracketing_estimate():
    o = clean_preview(); o["value_range"] = [1, 2]
    assert grader("G8").fn(o, ctx()).grade != "A+"


# ------------------------------- G9 -------------------------------
def test_g9_rewards_determinism():
    o = clean_preview()
    assert grader("G9").fn(o, ctx(reexecute=lambda: copy.deepcopy(o))).grade == "A+"

def test_g9_fails_nondeterminism():
    o = clean_preview()
    seq = [copy.deepcopy(o), {**copy.deepcopy(o), "verdict": "FAIR"}]
    rx = lambda: seq.pop(0)
    assert grader("G9").fn(o, ctx(reexecute=rx)).grade != "A+"


# ------------------------------- G10 -------------------------------
def test_g10_rewards_honest_communication():
    assert grader("G10").fn(clean_preview(), ctx()).grade == "A+"

def test_g10_fails_false_precision():
    o = clean_preview(); o.pop("production_disposition")
    assert grader("G10").fn(o, ctx()).grade != "A+"
