from house_price_tool.judge import judge_faithfulness, explanation_gate
from house_price_tool.llm import FakeLLMClient

RESULT = {"range": [604000, 667000], "midpoint": 635500, "asking": 650000,
          "estimates": {"m1": 635000}, "n_methods": 3, "comp_count": 6,
          "verdict": "FAIR", "detail": "FAIR upper third", "confidence": "High"}
GOOD = "Six sales support £604,000 to £667,000; £650,000 sits in the upper third."
BAD_NUMBERS = "Seven sales support £604,000 to £999,999."


def test_judge_parses_score():
    assert judge_faithfulness(RESULT, GOOD, FakeLLMClient("Score: 5")) == 5


def test_h10_passes_when_grounded_and_high_score():
    rec = explanation_gate(RESULT, GOOD, FakeLLMClient("Score: 5"))
    assert rec.gate_id == "H10" and rec.success and rec.score == 1.0


def test_h10_fails_when_numbers_intrude_even_if_judge_high():
    rec = explanation_gate(RESULT, BAD_NUMBERS, FakeLLMClient("Score: 5"))
    assert not rec.success and "number_match" in rec.reason


def test_h10_fails_when_judge_low():
    rec = explanation_gate(RESULT, GOOD, FakeLLMClient("Score: 2"))
    assert not rec.success and "faithfulness" in rec.reason
