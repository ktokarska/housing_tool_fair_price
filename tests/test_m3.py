import pathlib
from house_price_tool.methods.m3 import load_avm_table, method_three
from house_price_tool.models import PropertyRecord
from house_price_tool.records import SourceRef

FIX = pathlib.Path(__file__).parent / "fixtures" / "snap"


def _subject(uid="PP-1"):
    return PropertyRecord(postcode="SL6 7AB", property_type="S", paon="12",
                          street="EXAMPLE ROAD",
                          sources=[SourceRef(dataset="sold", row_id=uid, url="u")])


def test_loads_avm_and_builds_estimate():
    table = load_avm_table(FIX, "sl6-maidenhead")
    m = method_three(_subject("PP-1"), table)
    assert m.available and m.estimate == 620000 and m.listing_visible_on_avm is False


def test_unavailable_when_no_avm_row():
    table = load_avm_table(FIX, "sl6-maidenhead")
    m = method_three(_subject("PP-NONE"), table)
    assert not m.available and "no AVM" in m.flags[0]


def test_blank_avm_estimate_rows_are_skipped(tmp_path):
    geo = tmp_path / "sl6-maidenhead"
    geo.mkdir()
    (geo / "avm.csv").write_text(
        "property_key,avm_estimate,listing_visible\n"
        "PP-1,620000,false\n"   # captured
        "PP-2,,\n")             # un-captured template row
    table = load_avm_table(tmp_path, "sl6-maidenhead")
    assert "PP-1" in table and "PP-2" not in table
    assert not method_three(_subject("PP-2"), table).available
