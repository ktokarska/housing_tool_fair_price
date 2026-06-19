"""Step 2: resolve a subject's candidate comp set from the snapshot, with provenance."""
from __future__ import annotations

import pandas as pd

from .models import EpcRecord, PropertyRecord
from .records import MetricRecord, SourceRef
from .snapshot import Snapshot

LR_BASE = "https://landregistry.data.gov.uk/landregistry/query"
EPC_BASE = "https://find-energy-certificate.service.gov.uk"


def _clean(v) -> str:
    """Coerce a possibly-missing CSV cell to a clean string. HM Land Registry rows for
    named properties (e.g. 'OLD SCHOOL HOUSE') carry no street, which pandas reads as NaN."""
    return "" if pd.isna(v) else str(v)


def _epc_for(epc_df, postcode, paon, street) -> tuple[EpcRecord | None, str | None]:
    hit = epc_df[(epc_df.postcode == postcode) & (epc_df.paon.astype(str) == str(paon))
                 & (epc_df.street == street)]
    if hit.empty:
        return None, None
    row = hit.iloc[0]
    epc = EpcRecord(certificate_id=row.certificate_id, postcode=row.postcode,
                    paon=str(row.paon), street=_clean(row.street),
                    floor_area_sqm=float(row.floor_area_sqm),
                    build_year=int(row.build_year) if str(row.build_year).isdigit() else None)
    return epc, row.certificate_id


def resolve_candidates(snap: Snapshot, geo: str, sub_postcode: str,
                       property_type: str) -> list[PropertyRecord]:
    sold = snap.sold(geo)
    epc_df = snap.epc(geo)
    mask = (sold.postcode.str.startswith(sub_postcode)) & (sold.property_type == property_type)
    out: list[PropertyRecord] = []
    for _, row in sold[mask].iterrows():
        paon, street = _clean(row.paon), _clean(row.street)
        sources = [SourceRef(dataset="sold", row_id=row.unique_id, url=LR_BASE)]
        epc, cert_id = _epc_for(epc_df, row.postcode, paon, street)
        if epc is not None:
            sources.append(SourceRef(dataset="epc", row_id=cert_id,
                                     url=f"{EPC_BASE}/energy-certificate/{cert_id}"))
        out.append(PropertyRecord(
            postcode=row.postcode, property_type=row.property_type,
            paon=paon, street=street,
            sold_price=int(row.price_paid), deed_date=str(row.deed_date),
            epc=epc, tenure=str(row.estate_type), sources=sources))
    return out


def provenance_gate(records: list[PropertyRecord], snap: Snapshot,
                    geo: str) -> MetricRecord:
    sold_ids = set(snap.sold(geo).unique_id.astype(str))
    epc_ids = set(snap.epc(geo).certificate_id.astype(str))
    orphans = []
    for r in records:
        for s in r.sources:
            known = sold_ids if s.dataset == "sold" else epc_ids
            if s.row_id not in known:
                orphans.append(s.row_id)
    success = not orphans
    return MetricRecord(
        metric="source_provenance", gate_id="H2",
        score=1.0 if success else 0.0, threshold=1.0, success=success,
        reason="all figures trace to snapshot rows" if success
        else f"orphan row ids not in snapshot: {sorted(set(orphans))}",
    )
