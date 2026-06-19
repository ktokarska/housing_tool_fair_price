"""The estimate one valuation method produces, plus its reconcile mapping."""
from __future__ import annotations

from pydantic import BaseModel

from .records import SourceRef


class MethodEstimate(BaseModel):
    name: str
    estimate: int | None
    available: bool
    weakness: bool = False
    flags: list[str] = []
    proxy_sqft: bool = False
    proxy_band_pct: float | None = None
    donor: str | None = None
    listing_visible_on_avm: bool = False
    sources: list[SourceRef] = []

    def to_reconcile_dict(self) -> dict | None:
        if not self.available or self.estimate is None:
            return None
        if self.name == "m1":
            return {"estimate": self.estimate, "weakness": self.weakness}
        if self.name == "m2":
            return {"estimate": self.estimate, "proxy_sqft": self.proxy_sqft,
                    "proxy_band_pct": self.proxy_band_pct, "donor": self.donor,
                    "weakness": self.weakness}
        if self.name == "m3":
            return {"estimate": self.estimate, "proxy": self.proxy_sqft,
                    "donor": self.donor,
                    "listing_visible_on_avm": self.listing_visible_on_avm,
                    "weakness": self.weakness}
        raise ValueError(f"unknown method name {self.name!r}")
