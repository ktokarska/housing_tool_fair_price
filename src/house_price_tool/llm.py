"""LLM client behind a small interface so the pipeline is testable without network."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

JUDGE_MODEL = "claude-sonnet-4-6"


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, system: str, prompt: str, temperature: float = 0.0) -> str: ...


class AnthropicClient:
    def __init__(self, model: str = JUDGE_MODEL):
        self.model = model

    def complete(self, system: str, prompt: str, temperature: float = 0.0) -> str:
        import anthropic  # lazy: keeps the core importable without the SDK
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self.model, max_tokens=1024, temperature=temperature,
            system=system, messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")


class FakeLLMClient:
    def __init__(self, scripted):
        self._scripted = scripted
        self._i = 0
        self.calls: list[dict] = []

    def complete(self, system: str, prompt: str, temperature: float = 0.0) -> str:
        self.calls.append({"system": system, "prompt": prompt, "temperature": temperature})
        if isinstance(self._scripted, str):
            return self._scripted
        out = self._scripted[min(self._i, len(self._scripted) - 1)]
        self._i += 1
        return out
