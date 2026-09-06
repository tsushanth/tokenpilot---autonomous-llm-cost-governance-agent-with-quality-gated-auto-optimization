"""LLM providers: a real Anthropic-backed provider and a deterministic mock.

Both implement the same tiny protocol: complete(model, prompt) -> Completion.
This is what lets optimizer/evaluator/gate stay provider-agnostic.
"""

from dataclasses import dataclass
from typing import Protocol

# Two-tier price table (USD per 1M tokens). Two tiers is enough to prove
# auto-routing savings; adding more providers/tiers is a config change.
PRICE_TABLE = {
    "claude-opus-5": {"tier": "expensive", "input_per_mtok": 15.00, "output_per_mtok": 75.00},
    "claude-sonnet-5": {"tier": "mid", "input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5-20251001": {"tier": "cheap", "input_per_mtok": 0.80, "output_per_mtok": 4.00},
}

CHEAP_MODEL = "claude-haiku-4-5-20251001"


def model_tier(model: str) -> str:
    return PRICE_TABLE.get(model, {}).get("tier", "unknown")


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICE_TABLE[model]
    return (
        (input_tokens / 1_000_000) * prices["input_per_mtok"]
        + (output_tokens / 1_000_000) * prices["output_per_mtok"]
    )


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int


class Provider(Protocol):
    def complete(self, model: str, prompt: str) -> Completion: ...


class MockProvider:
    """Deterministic, zero-network provider used for local demos and tests.

    Matches the eval case whose raw `input` text appears in the prompt, then
    returns its canned mock_baseline/mock_candidate response depending on
    whether `model` is the expensive/mid tier (baseline) or the cheap tier
    (candidate). Token counts are fabricated from word counts so cost math
    still exercises the real pricing logic.
    """

    def __init__(self, eval_cases):
        self._cases = list(eval_cases)

    def complete(self, model: str, prompt: str) -> Completion:
        matched = None
        for case in self._cases:
            if case.input in prompt:
                matched = case
                break

        if matched is None:
            text = ""
        elif model_tier(model) == "cheap":
            text = matched.mock_candidate or ""
        else:
            text = matched.mock_baseline or ""

        input_tokens = max(1, len(prompt.split()))
        output_tokens = max(1, len(text.split()))
        return Completion(text=text, input_tokens=input_tokens, output_tokens=output_tokens)


class AnthropicProvider:
    """Thin wrapper around the real Anthropic SDK. Only imported/used when a
    real API key is supplied; never touched by --mock runs."""

    def __init__(self, api_key=None):
        import anthropic  # imported lazily so --mock never requires the package

        self.client = anthropic.Anthropic(api_key=api_key)

    def complete(self, model: str, prompt: str) -> Completion:
        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return Completion(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
