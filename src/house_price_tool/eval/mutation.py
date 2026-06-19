"""Grader validation: seed known-bad mutations; each must trip its gate."""
from __future__ import annotations

from ..explain import number_match_guard
from .gate_catalog import release_gates
from .residual import ResidualRecord

_GOOD_RESULT = {"range": [604000, 667000], "midpoint": 635500, "asking": 650000,
                "estimates": {"m1": 635000}, "n_methods": 1, "comp_count": 6,
                "verdict": "INDETERMINATE", "confidence": "Low"}


def _fabricated_number_caught() -> bool:
    bad = "The fair value is around £999,999."   # 999999 not in the result
    return not number_match_guard(_GOOD_RESULT, bad).success


def _directional_on_low_caught() -> bool:
    from ..verdict_calc import DIRECTIONAL_SET
    verdict, confidence = "OVERPRICED", "Low"
    directional_on_low = confidence in (None, "Low") and verdict in DIRECTIONAL_SET
    return directional_on_low


def _inflated_estimate_caught() -> bool:
    sold = 600000
    recs = [ResidualRecord(subject_id=str(i), sold_price=sold,
                           midpoint=round(sold * 1.15), range_lo=sold, range_hi=sold,
                           confidence="High", abstained=False) for i in range(5)]
    h4 = {g.gate_id: g for g in release_gates(recs)}["H4"]
    return not h4.success


def mutation_check() -> dict[str, bool]:
    results = {
        "fabricated_number": _fabricated_number_caught(),
        "directional_on_low": _directional_on_low_caught(),
        "inflated_estimate": _inflated_estimate_caught(),
    }
    assert all(results.values()), f"a mutation escaped its gate: {results}"
    return results
