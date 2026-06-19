"""Abstain precision and recall (gate H7)."""
from __future__ import annotations

from ..records import MetricRecord
from .residual import ResidualRecord


def abstain_precision_recall(records: list[ResidualRecord],
                             miss_threshold_pct: float = 10.0) -> tuple[float, float]:
    abstains = [r for r in records if r.abstained]
    should = [r for r in records if r.abs_residual_pct > miss_threshold_pct]
    warranted = [r for r in abstains if r.abs_residual_pct > miss_threshold_pct]
    precision = 1.0 if not abstains else len(warranted) / len(abstains)
    recall = 1.0 if not should else len(warranted) / len(should)
    return precision, recall


def abstain_gate(records: list[ResidualRecord], threshold: float = 0.80) -> MetricRecord:
    p, r = abstain_precision_recall(records)
    success = p >= threshold and r >= threshold
    return MetricRecord(metric="abstain_quality", gate_id="H7", score=round(min(p, r), 3),
                        threshold=threshold, success=success,
                        reason=f"precision={p:.2f}, recall={r:.2f}")
