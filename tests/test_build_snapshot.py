import json
import pathlib

from scripts.build_snapshot import parse_lr_rows, parse_epc_rows, write_snapshot

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_parse_lr_rows_maps_fields():
    data = json.loads((FIX / "lr_sparql_sample.json").read_text())
    rows = parse_lr_rows(data)
    assert rows and {"unique_id", "price_paid", "postcode", "property_type"} <= rows[0].keys()
    assert rows[0]["property_type"] == "S"


def test_parse_epc_rows_maps_floor_area():
    data = json.loads((FIX / "epc_search_sample.json").read_text())
    rows = parse_epc_rows(data)
    assert rows and isinstance(rows[0]["floor_area_sqm"], float)


def test_write_snapshot_emits_manifest_with_hash(tmp_path):
    frag = write_snapshot(tmp_path, "2026-06-19", "sl6-maidenhead",
                          [{"unique_id": "PP-1", "price_paid": 635000,
                            "deed_date": "2024-09-15", "postcode": "SL6 7AB",
                            "property_type": "S", "paon": "12",
                            "street": "EXAMPLE ROAD", "transaction_category": "A"}],
                          [{"certificate_id": "EPC-1", "postcode": "SL6 7AB",
                            "paon": "12", "street": "EXAMPLE ROAD",
                            "floor_area_sqm": 109.6, "build_year": 1935,
                            "lodgement_date": "2022-05-01"}])
    assert frag["files"]["sold.csv"]["rows"] == 1
    assert len(frag["files"]["sold.csv"]["sha256"]) == 64
    assert (tmp_path / "sl6-maidenhead" / "sold.csv").exists()
