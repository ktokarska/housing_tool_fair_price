from house_price_tool.eval.residual import ResidualRecord
from house_price_tool.eval.abstain_metrics import abstain_precision_recall, abstain_gate


def _r(resid, abstained):
    sold = 600000
    mid = round(sold * (1 + resid / 100))
    return ResidualRecord(subject_id="x", sold_price=sold, midpoint=mid,
                          range_lo=mid - 1, range_hi=mid + 1,
                          confidence="Low" if abstained else "High", abstained=abstained)


def test_perfect_abstain():
    recs = [_r(15, True), _r(20, True), _r(3, False)]
    p, r = abstain_precision_recall(recs)
    assert p == 1.0 and r == 1.0
    assert abstain_gate(recs).success


def test_unwarranted_abstain_drops_precision():
    recs = [_r(2, True), _r(15, True)]
    p, r = abstain_precision_recall(recs)
    assert p == 0.5
    assert not abstain_gate(recs).success
