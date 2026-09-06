import pytest

from tokenpilot.models import EvalCase
from tokenpilot.providers import MockProvider
from tokenpilot.evaluator import run_eval_set
from tokenpilot.scoring import exact_match, keyword_overlap, numeric_tolerance, llm_judge


def test_exact_match():
    case = EvalCase(id="c1", input="x", scorer="exact_match", expected="Paris")
    assert exact_match("Paris", case) == 1.0
    assert exact_match("paris ", case) == 1.0  # case/whitespace insensitive
    assert exact_match("London", case) == 0.0


def test_keyword_overlap():
    case = EvalCase(id="c1", input="x", scorer="keyword_overlap", expected=["reset", "email", "link"])
    assert keyword_overlap("Reset your password via the emailed link.", case) == 1.0
    assert keyword_overlap("Reset your password.", case) == pytest.approx(1 / 3)
    assert keyword_overlap("No idea.", case) == 0.0


def test_numeric_tolerance():
    case = EvalCase(id="c1", input="x", scorer="numeric_tolerance", expected=42, scorer_args={"tolerance": 1})
    assert numeric_tolerance("The answer is 42.5", case) == 1.0
    assert numeric_tolerance("The answer is 50", case) == 0.0
    assert numeric_tolerance("no number here", case) == 0.0


def test_llm_judge_rejects_mock_provider():
    case = EvalCase(id="c1", input="x", scorer="llm_judge", expected="Paris")
    with pytest.raises(RuntimeError):
        llm_judge("Paris", case, provider=MockProvider([]))


def test_run_eval_set_aggregates_score_and_cost():
    cases = [
        EvalCase(
            id="c1",
            input="What city is the capital of France?",
            scorer="keyword_overlap",
            expected=["paris"],
            mock_baseline="Paris is the capital.",
            mock_candidate="Paris.",
        ),
        EvalCase(
            id="c2",
            input="What city is the capital of Japan?",
            scorer="keyword_overlap",
            expected=["tokyo"],
            mock_baseline="Tokyo is the capital.",
            mock_candidate="I'm not sure.",
        ),
    ]
    provider = MockProvider(cases)

    baseline = run_eval_set(provider, "claude-opus-5", "{input}", cases)
    candidate = run_eval_set(provider, "claude-haiku-4-5-20251001", "{input}", cases)

    assert baseline.avg_quality == 1.0
    assert candidate.avg_quality == 0.5
    assert baseline.total_cost > 0
    assert candidate.total_cost > 0
    # cheap tier must actually be cheaper for the same workload
    assert candidate.total_cost < baseline.total_cost
