"""Cross-cutting record types emitted by every gate."""
from __future__ import annotations

from pydantic import BaseModel, field_validator

_DATASETS = {"sold", "epc"}


class MetricRecord(BaseModel):
    """One gate result. Same shape for deterministic and judged gates."""
    metric: str
    gate_id: str
    score: float
    threshold: float | None
    success: bool
    reason: str

    def to_dict(self) -> dict:
        return self.model_dump()


class SourceRef(BaseModel):
    """A pointer from any figure back to the snapshot row it came from."""
    dataset: str
    row_id: str
    url: str

    @field_validator("dataset")
    @classmethod
    def _known_dataset(cls, v: str) -> str:
        if v not in _DATASETS:
            raise ValueError(f"dataset must be one of {_DATASETS}, got {v!r}")
        return v
