"""Per-subject residual record for calibration."""
from __future__ import annotations

from pydantic import BaseModel


class ResidualRecord(BaseModel):
    subject_id: str
    sold_price: int
    midpoint: int
    range_lo: int
    range_hi: int
    confidence: str | None
    abstained: bool

    @property
    def residual_pct(self) -> float:
        return (self.midpoint - self.sold_price) / self.sold_price * 100

    @property
    def abs_residual_pct(self) -> float:
        return abs(self.residual_pct)

    @property
    def in_range(self) -> bool:
        return self.range_lo <= self.sold_price <= self.range_hi


def residual_from_result(subject_id, sold_price, contract) -> ResidualRecord | None:
    rng = contract.get("value_range")
    if not rng:
        return None
    lo, hi = rng
    return ResidualRecord(
        subject_id=subject_id, sold_price=sold_price,
        midpoint=round((lo + hi) / 2), range_lo=lo, range_hi=hi,
        confidence=contract.get("confidence"),
        abstained=bool(contract.get("abstain")),
    )
