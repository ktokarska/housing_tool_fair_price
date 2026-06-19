"""Step 8: classify a reconcile result as abstain or directional."""
from __future__ import annotations

_ABSTAIN_VERDICTS = {"INDETERMINATE", "NO VERDICT"}


def is_abstain(result: dict) -> bool:
    return result.get("verdict") in _ABSTAIN_VERDICTS


def abstain_reason(result: dict) -> str:
    return result.get("detail", "") if is_abstain(result) else ""
