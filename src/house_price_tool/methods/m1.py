"""Method 1: trend-adjusted median of matched comparables."""
from __future__ import annotations

import statistics

from ..baseline import MarketBaseline
from ..embedding import sub_postcode_of
from ..method_result import MethodEstimate
from ..models import PropertyRecord
from ..rulegate import months_between

TREND_CAP_PCT = 10.0
MIN_COMPS = 5


def method_one(comps: list[PropertyRecord], today: str,
               baseline: MarketBaseline) -> MethodEstimate:
    if len(comps) < MIN_COMPS:
        return MethodEstimate(name="m1", estimate=None, available=False,
                              flags=[f"insufficient comps (<{MIN_COMPS})"])
    adjusted, capped, sources = [], False, []
    for c in comps:
        yoy = baseline.yoy.get(sub_postcode_of(c.postcode), 0.0)
        months = months_between(today, c.deed_date)
        raw = yoy / 100 * months / 12
        clamped = max(-TREND_CAP_PCT / 100, min(TREND_CAP_PCT / 100, raw))
        if clamped != raw:
            capped = True
        adjusted.append(c.sold_price * (1 + clamped))
        sources += c.sources
    flags = ["trend-capped comp"] if capped else []
    return MethodEstimate(name="m1", estimate=round(statistics.median(adjusted)),
                          available=True, weakness=capped, flags=flags,
                          sources=sources)
