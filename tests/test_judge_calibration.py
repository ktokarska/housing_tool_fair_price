from house_price_tool.eval.judge_calibration import judge_agreement, judge_calibration_gate
from house_price_tool.llm import FakeLLMClient

R = {"range": [1, 2], "midpoint": 1, "asking": 1, "estimates": {}, "n_methods": 1,
     "comp_count": 0, "verdict": "FAIR", "confidence": "High"}


def test_agreement_perfect():
    labelled = [{"result": R, "explanation": "x", "human_pass": True},
                {"result": R, "explanation": "y", "human_pass": True}]
    assert judge_agreement(labelled, FakeLLMClient("Score: 5")) == 1.0
    assert judge_calibration_gate(labelled, FakeLLMClient("Score: 5")).success


def test_agreement_below_threshold_fails():
    labelled = [{"result": R, "explanation": "x", "human_pass": False},
                {"result": R, "explanation": "y", "human_pass": False}]
    rec = judge_calibration_gate(labelled, FakeLLMClient("Score: 5"))
    assert not rec.success
