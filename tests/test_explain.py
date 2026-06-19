from house_price_tool.explain import generate_explanation, number_match_guard, extract_numbers
from house_price_tool.llm import FakeLLMClient

RESULT = {"range": [604000, 667000], "midpoint": 635500, "asking": 650000,
          "estimates": {"m1": 635000, "m2": 655000, "m3": 620000},
          "n_methods": 3, "comp_count": 6, "verdict": "FAIR",
          "detail": "FAIR (asking sits at upper third of range)",
          "confidence": "High"}


def test_extract_numbers_handles_currency_and_words():
    nums = extract_numbers("Six sales support £604,000 to £667,000")
    assert 6 in nums and 604000 in nums and 667000 in nums


def test_guard_passes_for_grounded_prose():
    text = ("Six recent sales support a fair value of £604,000 to £667,000. "
            "The £650,000 asking sits in the upper third.")
    rec = number_match_guard(RESULT, text)
    assert rec.success and rec.metric == "number_match"


def test_guard_fails_on_invented_comp_count():
    text = "Seven recent sales support £604,000 to £667,000."
    rec = number_match_guard(RESULT, text)
    assert not rec.success and "7" in rec.reason


def test_generate_explanation_uses_client():
    client = FakeLLMClient("Six sales support £604,000 to £667,000.")
    out = generate_explanation(RESULT, client)
    assert "£604,000" in out and client.calls
