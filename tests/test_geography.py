import pathlib

from house_price_tool.geography import load_geography, calibration_validity

GEO = pathlib.Path(__file__).parent / "fixtures" / "geographies"


def test_loads_config_and_calibration():
    cfg = load_geography(GEO / "sl6-maidenhead")
    assert cfg.slug == "sl6-maidenhead"
    assert "SL6 7" in cfg.sub_postcodes
    assert cfg.calibration.exists and cfg.calibration.verdict == "PASS"


def test_valid_within_90_days_matching_version_and_type():
    cfg = load_geography(GEO / "sl6-maidenhead")
    ok, reason = calibration_validity(cfg, today="2026-06-19", subject_type="S")
    assert ok, reason


def test_expired_calibration_is_invalid():
    cfg = load_geography(GEO / "sl6-maidenhead")
    ok, reason = calibration_validity(cfg, today="2026-12-01", subject_type="S")
    assert not ok and "90 days" in reason


def test_uncalibrated_geography_is_invalid():
    cfg = load_geography(GEO / "w13-west-ealing")
    ok, reason = calibration_validity(cfg, today="2026-06-19", subject_type="S")
    assert not ok and "no calibration" in reason.lower()
