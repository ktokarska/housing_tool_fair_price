"""Step 9 (part 2): pinned faithfulness judge and the combined H10 gate."""
from __future__ import annotations

import re

from .explain import number_match_guard
from .llm import LLMClient
from .records import MetricRecord

FAITHFULNESS_MIN = 4

_JUDGE_SYSTEM = (
    "You are a careful evaluator. Score the explanation's faithfulness to the "
    "result on a 1 to 5 scale. Steps: (1) list each factual claim in the "
    "explanation; (2) check each against the result; (3) if any claim is "
    "unsupported or any number differs, score 1 or 2; (4) if all claims are "
    "supported, score 5. If you cannot tell, answer 'Unknown'. "
    "End with a line 'Score: N'."
)


def judge_faithfulness(result: dict, explanation: str, client: LLMClient) -> int:
    prompt = f"Result: {result}\n\nExplanation: {explanation}\n\nScore it."
    reply = client.complete(_JUDGE_SYSTEM, prompt, temperature=0.0)
    m = re.search(r"score\s*[:=]\s*([1-5])", reply, flags=re.IGNORECASE)
    if not m:
        raise ValueError(f"no score found in judge reply: {reply!r}")
    return int(m.group(1))


def explanation_gate(result: dict, explanation: str,
                     judge_client: LLMClient) -> MetricRecord:
    guard = number_match_guard(result, explanation)
    score = judge_faithfulness(result, explanation, judge_client)
    success = guard.success and score >= FAITHFULNESS_MIN
    if not guard.success:
        reason = f"number_match failed: {guard.reason}"
    elif score < FAITHFULNESS_MIN:
        reason = f"faithfulness {score} below {FAITHFULNESS_MIN}"
    else:
        reason = f"number_match ok; faithfulness {score}"
    return MetricRecord(metric="explanation_faithfulness", gate_id="H10",
                        score=round(score / 5, 2), threshold=FAITHFULNESS_MIN / 5,
                        success=success, reason=reason)
