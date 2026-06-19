from house_price_tool.eval.verdict_rule import calibration_verdict


def test_high_mae_quarantines():
    v = calibration_verdict(mae=12, bias=0, hit_rate=0.9, wilson_lo=0.7,
                            high_tier_coverage=0.9, q80=8)
    assert v["verdict"] == "QUARANTINE"


def test_low_coverage_quarantines():
    v = calibration_verdict(mae=4, bias=0, hit_rate=0.6, wilson_lo=0.4,
                            high_tier_coverage=0.6, q80=8)
    assert v["verdict"] == "QUARANTINE"


def test_pass_with_correction_sets_offset():
    v = calibration_verdict(mae=7, bias=3, hit_rate=0.8, wilson_lo=0.6,
                            high_tier_coverage=0.8, q80=9)
    assert v["verdict"] == "PASS WITH CORRECTION" and v["bias_correction_pct"] == -3


def test_clean_pass():
    v = calibration_verdict(mae=4, bias=1, hit_rate=0.75, wilson_lo=0.6,
                            high_tier_coverage=0.75, q80=4)
    assert v["verdict"] == "PASS" and v["H_pct"] == 5


def test_fallback_widens():
    v = calibration_verdict(mae=4, bias=1, hit_rate=0.75, wilson_lo=0.6,
                            high_tier_coverage=0.5, q80=8)
    assert v["verdict"] == "PASS WITH WIDER RANGES" and v["H_pct"] == 8
