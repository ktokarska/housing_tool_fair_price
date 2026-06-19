"""Method 3: pinned public-AVM snapshot cross-check. Optional and manual-captured."""
from __future__ import annotations

import csv
import pathlib

from ..method_result import MethodEstimate
from ..models import PropertyRecord
from ..records import SourceRef


def load_avm_table(snapshot_root, geo: str, filename: str = "avm.csv") -> dict[str, dict]:
    path = pathlib.Path(snapshot_root) / geo / filename
    if not path.exists():
        return {}
    out = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            # Un-captured rows in a partially-filled capture template have a blank
            # avm_estimate; skip them so the subject loads as 'no AVM' rather than crashing.
            if not str(row.get("avm_estimate", "")).strip():
                continue
            out[row["property_key"]] = row
    return out


def _sold_id(subject: PropertyRecord) -> str:
    for s in subject.sources:
        if s.dataset == "sold":
            return s.row_id
    return ""


def method_three(subject: PropertyRecord, avm_table: dict[str, dict]) -> MethodEstimate:
    row = avm_table.get(_sold_id(subject))
    if not row:
        return MethodEstimate(name="m3", estimate=None, available=False,
                              flags=["no AVM snapshot"])
    visible = str(row.get("listing_visible", "")).strip().lower() == "true"
    return MethodEstimate(
        name="m3", estimate=round(float(row["avm_estimate"])), available=True,
        listing_visible_on_avm=visible,
        sources=[SourceRef(dataset="sold", row_id=_sold_id(subject),
                           url=row.get("source_url", ""))])
