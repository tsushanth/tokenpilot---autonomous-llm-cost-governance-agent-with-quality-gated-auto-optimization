"""Plain dataclasses shared across the optimize -> evaluate -> gate pipeline."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EvalCase:
    id: str
    input: str
    scorer: str
    expected: Any
    scorer_args: dict = field(default_factory=dict)
    # Canned outputs used only by MockProvider, keyed by which phase of the
    # pipeline is asking (baseline = expensive tier, candidate = cheap tier).
    mock_baseline: Optional[str] = None
    mock_candidate: Optional[str] = None

    @staticmethod
    def from_dict(d: dict) -> "EvalCase":
        return EvalCase(
            id=d["id"],
            input=d["input"],
            scorer=d["scorer"],
            expected=d.get("expected"),
            scorer_args=d.get("scorer_args", {}),
            mock_baseline=d.get("mock_baseline"),
            mock_candidate=d.get("mock_candidate"),
        )


@dataclass
class Task:
    name: str
    baseline_model: str
    prompt_template: str
    quality_tolerance: float
    eval_cases: list

    @staticmethod
    def from_dict(d: dict) -> "Task":
        return Task(
            name=d["name"],
            baseline_model=d["baseline_model"],
            prompt_template=d["prompt_template"],
            quality_tolerance=d["quality_tolerance"],
            eval_cases=[EvalCase.from_dict(c) for c in d["eval_cases"]],
        )


@dataclass
class CaseResult:
    case_id: str
    output: str
    score: float
    cost: float
    input_tokens: int
    output_tokens: int


@dataclass
class RunResult:
    model: str
    prompt_template: str
    avg_quality: float
    total_cost: float
    case_results: list


@dataclass
class GateDecision:
    ship: bool
    reason: str
    quality_drop: float
    tolerance: float
    baseline_cost: float
    candidate_cost: float
    savings: float
    savings_pct: float
