import pathlib

from house_price_tool.snapshot import load_snapshot
from house_price_tool.resolve import resolve_candidates, provenance_gate

FIX = pathlib.Path(__file__).parent / "fixtures" / "snap"


def test_resolves_semis_with_epc_and_sources():
    snap = load_snapshot(FIX)
    recs = resolve_candidates(snap, "sl6-maidenhead", "SL6 7", "S")
    assert len(recs) == 1                      # only PP-1 is a semi
    r = recs[0]
    assert r.sold_price == 635000
    assert r.epc is not None and r.epc.floor_area_sqft == round(109.6 * 10.764, 1)
    assert {s.dataset for s in r.sources} == {"sold", "epc"}


def test_provenance_gate_passes_for_real_rows():
    snap = load_snapshot(FIX)
    recs = resolve_candidates(snap, "sl6-maidenhead", "SL6 7", "S")
    rec = provenance_gate(recs, snap, "sl6-maidenhead")
    assert rec.gate_id == "H2" and rec.success and rec.score == 1.0


def test_provenance_gate_fails_on_orphan_row():
    from house_price_tool.records import SourceRef
    snap = load_snapshot(FIX)
    recs = resolve_candidates(snap, "sl6-maidenhead", "SL6 7", "S")
    recs[0].sources.append(SourceRef(dataset="sold", row_id="PP-FAKE", url="http://e"))
    rec = provenance_gate(recs, snap, "sl6-maidenhead")
    assert not rec.success and "PP-FAKE" in rec.reason
