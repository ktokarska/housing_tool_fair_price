"""Deterministic comparable match rules. Floor-area band replaces bedrooms."""
from __future__ import annotations

import datetime as dt

from .embedding import sub_postcode_of
from .models import PropertyRecord

_BANDS = ["lt1000", "1000_1400", "gt1400"]


def area_band(sqft: float | None) -> str | None:
    if sqft is None:
        return None
    if sqft < 1000:
        return "lt1000"
    if sqft <= 1400:
        return "1000_1400"
    return "gt1400"


def months_between(a_iso: str, b_iso: str) -> int:
    a, b = dt.date.fromisoformat(a_iso[:10]), dt.date.fromisoformat(b_iso[:10])
    return (a.year - b.year) * 12 + (a.month - b.month)


def _adjacent_subs(sub: str) -> set[str]:
    outward, _, digit = sub.partition(" ")
    if not digit.isdigit():
        return {sub}
    d = int(digit)
    return {f"{outward} {n}" for n in (d - 1, d, d + 1) if 0 <= n <= 9}


def rule_valid(subject: PropertyRecord, candidate: PropertyRecord, today: str,
               *, widen: int = 0) -> bool:
    if candidate.property_type != subject.property_type:
        return False
    if candidate.tenure != subject.tenure:
        return False
    recency = 24 if widen >= 3 else 18
    if not (0 <= months_between(today, candidate.deed_date) <= recency):
        return False
    subj_sub = sub_postcode_of(subject.postcode)
    cand_sub = sub_postcode_of(candidate.postcode)
    allowed_subs = _adjacent_subs(subj_sub) if widen >= 2 else {subj_sub}
    if cand_sub not in allowed_subs:
        return False
    subj_band = area_band(subject.epc.floor_area_sqft) if subject.epc else None
    if subj_band is not None:
        cand_band = area_band(candidate.epc.floor_area_sqft) if candidate.epc else None
        if cand_band is None:
            return False
        if widen >= 1:
            si = _BANDS.index(subj_band)
            if abs(_BANDS.index(cand_band) - si) > 1:
                return False
        elif cand_band != subj_band:
            return False
    return True


def rule_valid_set(subject, candidates, today, widen: int = 0) -> set[str]:
    out = set()
    for c in candidates:
        if c is subject:
            continue
        if rule_valid(subject, c, today, widen=widen):
            for s in c.sources:
                if s.dataset == "sold":
                    out.add(s.row_id)
    return out
