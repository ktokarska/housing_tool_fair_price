from house_price_tool.eval.residual import ResidualRecord
from house_price_tool.eval.metrics_calc import mae, q80, bias, wilson, hit_rate


def _r(resid_pct, sold=600000, in_range=True, conf="High", abstained=False):
    mid = round(sold * (1 + resid_pct / 100))
    lo, hi = (sold - 1, sold + 1) if in_range else (mid - 1, mid + 1)
    return ResidualRecord(subject_id="x", sold_price=sold, midpoint=mid,
                          range_lo=lo, range_hi=hi, confidence=conf, abstained=abstained)


def test_mae_is_median_absolute():
    recs = [_r(2), _r(-4), _r(6)]
    assert mae(recs) == 4.0


def test_bias_is_median_signed():
    assert bias([_r(2), _r(-4), _r(6)]) == 2.0


def test_wilson_bounds_order():
    lo, hi = wilson(7, 10)
    assert 0 <= lo < hi <= 1


def test_hit_rate_excludes_abstained_and_low():
    recs = [_r(2, in_range=True), _r(3, in_range=False),
            _r(0, conf="Low", abstained=True, in_range=True)]
    rate, lo, hi = hit_rate(recs)
    assert rate == 0.5
