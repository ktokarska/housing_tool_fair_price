"""Step 1: geography gate. Routes by calibration validity and run mode."""
from __future__ import annotations

import enum

from .geography import GeographyConfig, calibration_validity
from .records import MetricRecord


class GateDecision(str, enum.Enum):
    PROCEED = "PROCEED"
    NOT_IN_DEMO = "NOT_IN_DEMO"
    PROMPT_CALIBRATION = "PROMPT_CALIBRATION"


def geography_gate(cfg: GeographyConfig, subject_type: str, run_mode: str,
                   today: str) -> tuple[GateDecision, str, MetricRecord]:
    valid, reason = calibration_validity(cfg, today, subject_type)
    if valid:
        decision, msg = GateDecision.PROCEED, "calibration valid, proceeding"
    elif run_mode == "headless":
        decision = GateDecision.NOT_IN_DEMO
        msg = "Not part of the demo, calibration needed"
    else:
        decision = GateDecision.PROMPT_CALIBRATION
        msg = "This area is not calibrated. Run calibration now? [y/n]"
    rec = MetricRecord(
        metric="geography_gate", gate_id="H1",
        score=1.0, threshold=1.0, success=True,
        reason=f"{cfg.slug}: {decision.value} ({reason})",
    )
    return decision, msg, rec
