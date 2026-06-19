from house_price_tool.abstain import is_abstain, abstain_reason


def test_indeterminate_is_abstain():
    assert is_abstain({"verdict": "INDETERMINATE", "detail": "methods disagree"})
    assert "disagree" in abstain_reason({"verdict": "INDETERMINATE", "detail": "methods disagree"})


def test_directional_is_not_abstain():
    assert not is_abstain({"verdict": "FAIR", "detail": "x"})
    assert abstain_reason({"verdict": "FAIR", "detail": "x"}) == ""
