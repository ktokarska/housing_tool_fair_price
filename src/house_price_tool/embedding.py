"""Structured feature vectors for comparable retrieval. Deterministic."""
from __future__ import annotations

import numpy as np

from .models import PropertyRecord

CATEGORICAL_WEIGHT = 5.0


def sub_postcode_of(postcode: str) -> str:
    outward, _, inward = postcode.strip().partition(" ")
    return f"{outward} {inward[0]}" if inward else outward


def _sold_id(rec: PropertyRecord) -> str:
    for s in rec.sources:
        if s.dataset == "sold":
            return s.row_id
    return ""


class FeatureEncoder:
    def __init__(self):
        self._fit = False

    def fit(self, records: list[PropertyRecord]) -> "FeatureEncoder":
        areas = [r.epc.floor_area_sqft if r.epc else 0.0 for r in records]
        years = [r.epc.build_year if (r.epc and r.epc.build_year) else 0 for r in records]
        self._area_mu, self._area_sd = float(np.mean(areas)), float(np.std(areas) or 1.0)
        self._year_mu, self._year_sd = float(np.mean(years)), float(np.std(years) or 1.0)
        self._types = sorted({r.property_type for r in records})
        self._subs = sorted({sub_postcode_of(r.postcode) for r in records})
        self._fit = True
        return self

    def _onehot(self, value, vocab) -> list[float]:
        return [CATEGORICAL_WEIGHT if value == v else 0.0 for v in vocab]

    def transform(self, record: PropertyRecord) -> np.ndarray:
        assert self._fit, "call fit() first"
        area = (record.epc.floor_area_sqft if record.epc else 0.0)
        year = (record.epc.build_year if (record.epc and record.epc.build_year) else 0)
        vec = [
            (area - self._area_mu) / self._area_sd,
            (year - self._year_mu) / self._year_sd,
        ]
        vec += self._onehot(record.property_type, self._types)
        vec += self._onehot(sub_postcode_of(record.postcode), self._subs)
        return np.asarray(vec, dtype=np.float32)

    def transform_many(self, records):
        mat = np.vstack([self.transform(r) for r in records]).astype(np.float32)
        return mat, [_sold_id(r) for r in records]
