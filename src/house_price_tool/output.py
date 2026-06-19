"""Step 10: assemble the HouseResult and the headless result contract."""
from __future__ import annotations

from pydantic import BaseModel

from . import METHODOLOGY_VERSION
from .records import MetricRecord


class HouseResult(BaseModel):
    subject_label: str
    geography: str
    methodology_version: str
    snapshot_date: str
    estimates: dict[str, int]
    confidence: str | None
    value_range: list[int] | None
    verdict: str
    detail: str
    abstain: bool
    explanation: str
    metrics: list[MetricRecord]

    def to_contract(self) -> dict:
        return self.model_dump()


def assemble_result(*, subject_label, geography, snapshot_date, reconcile_result,
                    abstain, explanation, metrics) -> HouseResult:
    return HouseResult(
        subject_label=subject_label, geography=geography,
        methodology_version=METHODOLOGY_VERSION, snapshot_date=snapshot_date,
        estimates=reconcile_result.get("estimates", {}),
        confidence=reconcile_result.get("confidence"),
        value_range=reconcile_result.get("range"),
        verdict=reconcile_result["verdict"], detail=reconcile_result.get("detail", ""),
        abstain=abstain, explanation=explanation, metrics=list(metrics),
    )
