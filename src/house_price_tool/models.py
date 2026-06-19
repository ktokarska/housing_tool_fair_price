"""Typed snapshot rows and the resolved property record."""
from __future__ import annotations

from pydantic import BaseModel

from .records import SourceRef

PROPERTY_TYPES = {"D": "Detached", "S": "Semi-detached", "T": "Terraced",
                  "F": "Flat", "O": "Other"}
SQM_TO_SQFT = 10.764


class EpcRecord(BaseModel):
    certificate_id: str
    postcode: str
    paon: str
    street: str
    floor_area_sqm: float
    build_year: int | None = None

    @property
    def floor_area_sqft(self) -> float:
        return round(self.floor_area_sqm * SQM_TO_SQFT, 1)


class PropertyRecord(BaseModel):
    postcode: str
    property_type: str
    paon: str
    street: str
    sold_price: int | None = None
    deed_date: str | None = None
    epc: EpcRecord | None = None
    tenure: str = "F"
    sources: list[SourceRef] = []

    def masked_address(self) -> str:
        """Postcode + type only. Used to enforce blind production conditions."""
        return f"{PROPERTY_TYPES[self.property_type]} in {self.postcode}"
