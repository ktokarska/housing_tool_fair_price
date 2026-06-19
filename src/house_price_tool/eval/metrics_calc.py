"""Residual aggregate statistics. Definitions match the origin calibration protocol."""
from __future__ import annotations

import math
import statistics

from .residual import ResidualRecord


def mae(records: list[ResidualRecord]) -> float:
    return float(statistics.median([r.abs_residual_pct for r in records]))


def q80(records: list[ResidualRecord]) -> float:
    vals = sorted(r.abs_residual_pct for r in records)
    if not vals:
        return 0.0
    idx = min(len(vals) - 1, int(math.ceil(0.8 * len(vals)) - 1))
    return float(vals[idx])


def bias(records: list[ResidualRecord]) -> float:
    return float(statistics.median([r.residual_pct for r in records]))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    phat = k / n
    denom = 1 + z**2 / n
    centre = phat + z**2 / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return (centre - margin) / denom, (centre + margin) / denom


def _directional(records):
    return [r for r in records if not r.abstained and r.confidence not in (None, "Low")]


def hit_rate(records: list[ResidualRecord]) -> tuple[float, float, float]:
    rows = _directional(records)
    if not rows:
        return 0.0, 0.0, 0.0
    k = sum(1 for r in rows if r.in_range)
    lo, hi = wilson(k, len(rows))
    return k / len(rows), lo, hi


def tier_coverage(records: list[ResidualRecord], tier: str) -> float:
    rows = [r for r in records if r.confidence == tier]
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.in_range) / len(rows)
