"""Deterministic quality scorers, plus an optional LLM-judge scorer.

Every scorer returns a float in [0.0, 1.0] where 1.0 is a perfect match.
"""

import re


def exact_match(output: str, case) -> float:
    return 1.0 if output.strip().lower() == str(case.expected).strip().lower() else 0.0


def keyword_overlap(output: str, case) -> float:
    keywords = case.expected or []
    if not keywords:
        return 0.0
    text = output.lower()
    found = sum(1 for kw in keywords if str(kw).lower() in text)
    return found / len(keywords)


def numeric_tolerance(output: str, case) -> float:
    tolerance = case.scorer_args.get("tolerance", 0)
    match = re.search(r"-?\d+(\.\d+)?", output)
    if not match:
        return 0.0
    value = float(match.group())
    return 1.0 if abs(value - float(case.expected)) <= tolerance else 0.0


def llm_judge(output: str, case, provider=None) -> float:
    """Scores an output 0.0-1.0 by asking a real model to judge it against the
    expected answer. Only usable with a real (non-mock) provider — raises
    otherwise, since there is nothing deterministic to fall back on."""
    from tokenpilot.providers import MockProvider

    if provider is None or isinstance(provider, MockProvider):
        raise RuntimeError(
            "llm_judge requires a real API key (AnthropicProvider); "
            "it has no meaning under --mock."
        )

    judge_prompt = (
        "You are grading a candidate answer against a reference answer.\n"
        f"Reference answer: {case.expected}\n"
        f"Candidate answer: {output}\n"
        "Rate how well the candidate matches the reference on a 0.0-1.0 scale. "
        "Reply with only the number."
    )
    completion = provider.complete("claude-opus-5", judge_prompt)
    match = re.search(r"\d+(\.\d+)?", completion.text)
    if not match:
        return 0.0
    return max(0.0, min(1.0, float(match.group())))


SCORERS = {
    "exact_match": exact_match,
    "keyword_overlap": keyword_overlap,
    "numeric_tolerance": numeric_tolerance,
    "llm_judge": llm_judge,
}


def score(output: str, case, provider=None) -> float:
    fn = SCORERS.get(case.scorer)
    if fn is None:
        raise ValueError(f"Unknown scorer: {case.scorer!r}")
    if case.scorer == "llm_judge":
        return fn(output, case, provider=provider)
    return fn(output, case)
