"""Multi-trial reliability for the stochastic surfaces (retrieval, explanation/judge)."""
from __future__ import annotations

from ..records import MetricRecord


def pass_at_k(trial_fn, k: int) -> dict:
    passes = sum(1 for _ in range(k) if trial_fn())
    return {"k": k, "passes": passes, "rate": passes / k if k else 0.0,
            "flaky": 0 < passes < k}


def reliability_record(trial_fn, k: int, threshold: float = 1.0) -> MetricRecord:
    out = pass_at_k(trial_fn, k)
    success = out["rate"] >= threshold and not out["flaky"]
    reason = (f"{out['passes']}/{k} trials passed"
              + (" (flaky)" if out["flaky"] else ""))
    return MetricRecord(metric="pass@k", gate_id="RELIABILITY",
                        score=round(out["rate"], 3), threshold=threshold,
                        success=success, reason=reason)
