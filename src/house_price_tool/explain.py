"""Step 9 (part 1): generate a grounded explanation and guard its numbers."""
from __future__ import annotations

import re

from .llm import LLMClient
from .records import MetricRecord

ALLOWED_WORD_NUMS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}

_SYSTEM = (
    "You explain a property valuation result to a general reader. "
    "Use only the figures provided in the result. Never introduce a number "
    "that is not in the result. If the verdict is INDETERMINATE, do not use "
    "directional words (overpriced, underpriced, bargain). Plain English, no "
    "em-dashes; do not use the words delve, synergy, robust, streamline, "
    "cutting-edge, or leverage as a verb, or the word bet. Two or three sentences."
)


def extract_numbers(text: str) -> set[int]:
    nums = set()
    for tok in re.findall(r"\d[\d,]*", text):
        nums.add(int(tok.replace(",", "")))
    for word, val in ALLOWED_WORD_NUMS.items():
        if re.search(rf"\b{word}\b", text, flags=re.IGNORECASE):
            nums.add(val)
    return nums


def _allowed(result: dict) -> set[int]:
    allowed = set()
    lo, hi = result.get("range", [None, None])
    for v in (lo, hi, result.get("midpoint"), result.get("asking"),
              result.get("n_methods"), result.get("comp_count")):
        if isinstance(v, (int, float)) and v is not None:
            allowed.add(int(v))
    for v in (result.get("estimates") or {}).values():
        allowed.add(int(v))
    return allowed


def number_match_guard(result: dict, explanation: str) -> MetricRecord:
    allowed = _allowed(result)
    found = extract_numbers(explanation)
    intruders = sorted(n for n in found if n not in allowed)
    success = not intruders
    return MetricRecord(
        metric="number_match", gate_id="H10", score=1.0 if success else 0.0,
        threshold=1.0, success=success,
        reason="all figures in prose match the result" if success
        else f"prose contains numbers not in the result: {intruders}",
    )


def generate_explanation(result: dict, client: LLMClient) -> str:
    prompt = (
        "Result (JSON-like): "
        f"verdict={result.get('verdict')}, confidence={result.get('confidence')}, "
        f"range={result.get('range')}, midpoint={result.get('midpoint')}, "
        f"asking={result.get('asking')}, comp_count={result.get('comp_count')}, "
        f"detail={result.get('detail')!r}. "
        "Write the explanation."
    )
    return client.complete(_SYSTEM, prompt, temperature=0.0)
