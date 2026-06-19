"""Method 2: EPC floor area × stock-segment £/sq ft. No estimation of floor area."""
from __future__ import annotations

from ..baseline import MarketBaseline, psqft_for
from ..embedding import sub_postcode_of
from ..method_result import MethodEstimate
from ..models import PropertyRecord
from ..records import MetricRecord

SIZE_MISMATCH_PCT = 25.0


def method_two(subject: PropertyRecord,
               baseline: MarketBaseline) -> tuple[MethodEstimate, MetricRecord]:
    def h9(success: bool, reason: str) -> MetricRecord:
        return MetricRecord(metric="sqft_provenance", gate_id="H9",
                            score=1.0 if success else 0.0, threshold=1.0,
                            success=success, reason=reason)

    if subject.epc is None:
        return (MethodEstimate(name="m2", estimate=None, available=False,
                               flags=["no EPC floor area"]),
                h9(True, "method correctly unavailable: no EPC floor area"))

    sub = sub_postcode_of(subject.postcode)
    psqft, basis = psqft_for(baseline, sub, subject.property_type)
    if psqft is None:
        return (MethodEstimate(name="m2", estimate=None, available=False,
                               flags=[basis]),
                h9(True, "method correctly unavailable: no segment £/sq ft"))

    sqft = subject.epc.floor_area_sqft
    estimate = round(sqft * psqft)
    weakness, flags = False, []
    median = baseline.median_sqft.get((sub, subject.property_type))
    if median and abs(sqft - median) / median * 100 > SIZE_MISMATCH_PCT:
        weakness = True
        flags.append("size-mismatch vs cell median")

    has_epc_source = any(s.dataset == "epc" for s in subject.sources)
    return (MethodEstimate(name="m2", estimate=estimate, available=True,
                           weakness=weakness, flags=flags, sources=subject.sources),
            h9(has_epc_source, "estimate sourced from EPC floor area" if has_epc_source
               else "estimate produced without an EPC source row"))
