"""Structured feature vectors for comparable retrieval. Deterministic."""
from __future__ import annotations

import datetime as dt

import numpy as np

from .models import PropertyRecord

CATEGORICAL_WEIGHT = 5.0
RECENCY_MONTHS = 18  # mirrors the rule gate's default recency window


def _months_between(a_iso: str, b_iso: str) -> int:
    a, b = dt.date.fromisoformat(a_iso[:10]), dt.date.fromisoformat(b_iso[:10])
    return (a.year - b.year) * 12 + (a.month - b.month)

# Floor-area bands: the rule gate's discrete area key (bedrooms are absent in open data).
_BANDS = ["lt1000", "1000_1400", "gt1400"]


def area_band(sqft: float | None) -> str | None:
    if sqft is None:
        return None
    if sqft < 1000:
        return "lt1000"
    if sqft <= 1400:
        return "1000_1400"
    return "gt1400"


def sub_postcode_of(postcode: str) -> str:
    outward, _, inward = postcode.strip().partition(" ")
    return f"{outward} {inward[0]}" if inward else outward


def _sold_id(rec: PropertyRecord) -> str:
    for s in rec.sources:
        if s.dataset == "sold":
            return s.row_id
    return ""


class FeatureEncoder:
    def __init__(self, today: str | None = None):
        self._fit = False
        self._today = today

    def fit(self, records: list[PropertyRecord]) -> "FeatureEncoder":
        areas = [r.epc.floor_area_sqft if r.epc else 0.0 for r in records]
        years = [r.epc.build_year if (r.epc and r.epc.build_year) else 0 for r in records]
        self._area_mu, self._area_sd = float(np.mean(areas)), float(np.std(areas) or 1.0)
        self._year_mu, self._year_sd = float(np.mean(years)), float(np.std(years) or 1.0)
        self._types = sorted({r.property_type for r in records})
        self._subs = sorted({sub_postcode_of(r.postcode) for r in records})
        self._tenures = sorted({r.tenure for r in records})
        self._fit = True
        return self

    def _onehot(self, value, vocab) -> list[float]:
        return [CATEGORICAL_WEIGHT if value == v else 0.0 for v in vocab]

    def transform(self, record: PropertyRecord, *, as_query: bool = False) -> np.ndarray:
        assert self._fit, "call fit() first"
        area = (record.epc.floor_area_sqft if record.epc else 0.0)
        year = (record.epc.build_year if (record.epc and record.epc.build_year) else 0)
        vec = [
            (area - self._area_mu) / self._area_sd,
            (year - self._year_mu) / self._year_sd,
        ]
        vec += self._onehot(record.property_type, self._types)
        vec += self._onehot(sub_postcode_of(record.postcode), self._subs)
        # The rule gate's discrete keys, so retrieval surfaces what the gate will keep:
        # candidates sharing the subject's floor-area band and tenure rank as near neighbours
        # instead of being displaced by near-area properties just across a band/tenure line.
        vec += self._onehot(area_band(record.epc.floor_area_sqft if record.epc else None), _BANDS)
        vec += self._onehot(record.tenure, self._tenures)
        # Recency, the gate's time key. The query is valued as-of-today, so it sits in the
        # "recent" region; a candidate sold >18mo ago lands away from it, instead of crowding
        # the top-K just because its floor area is close.
        if self._today is not None:
            recent = as_query or (0 <= _months_between(self._today, record.deed_date)
                                  <= RECENCY_MONTHS)
            vec.append(CATEGORICAL_WEIGHT if recent else 0.0)
        return np.asarray(vec, dtype=np.float32)

    def transform_many(self, records):
        mat = np.vstack([self.transform(r) for r in records]).astype(np.float32)
        return mat, [_sold_id(r) for r in records]
