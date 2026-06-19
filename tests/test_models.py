from house_price_tool.models import EpcRecord, PropertyRecord, PROPERTY_TYPES
from house_price_tool.records import SourceRef


def test_sqm_to_sqft_conversion():
    epc = EpcRecord(certificate_id="EPC-1", postcode="SL6 7AB", paon="12",
                    street="EXAMPLE ROAD", floor_area_sqm=100.0, build_year=1935)
    assert epc.floor_area_sqft == 1076.4


def test_masked_address_hides_house_number():
    p = PropertyRecord(postcode="SL6 7AB", property_type="S", paon="12",
                       street="EXAMPLE ROAD", sold_price=635000,
                       deed_date="2024-09-15", epc=None,
                       sources=[SourceRef(dataset="sold", row_id="PP-1", url="http://e")])
    masked = p.masked_address()
    assert "12" not in masked
    assert "SL6 7AB" in masked and "Semi-detached" in masked


def test_property_types_table():
    assert PROPERTY_TYPES["S"] == "Semi-detached"
