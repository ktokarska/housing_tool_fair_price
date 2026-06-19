"""The judge must agree with human labels before its scores count."""
from __future__ import annotations

from ..judge import FAITHFULNESS_MIN, judge_faithfulness
from ..records import MetricRecord


def judge_agreement(labelled: list[dict], judge_client) -> float:
    if not labelled:
        return 0.0
    agree = 0
    for item in labelled:
        score = judge_faithfulness(item["result"], item["explanation"], judge_client)
        judge_pass = score >= FAITHFULNESS_MIN
        if judge_pass == item["human_pass"]:
            agree += 1
    return agree / len(labelled)


def judge_calibration_gate(labelled, judge_client, threshold: float = 0.85) -> MetricRecord:
    a = judge_agreement(labelled, judge_client)
    return MetricRecord(metric="judge_agreement", gate_id="JUDGE_CAL",
                        score=round(a, 3), threshold=threshold, success=a >= threshold,
                        reason=f"judge agrees with {a:.0%} of human labels")
