"""Runs a prompt template + model over an eval set and scores the outputs."""

from tokenpilot.models import CaseResult, RunResult
from tokenpilot.providers import compute_cost
from tokenpilot.scoring import score as score_output


def run_eval_set(provider, model: str, prompt_template: str, eval_cases) -> RunResult:
    case_results = []
    for case in eval_cases:
        prompt = prompt_template.format(input=case.input)
        completion = provider.complete(model, prompt)
        quality = score_output(completion.text, case, provider=provider)
        cost = compute_cost(model, completion.input_tokens, completion.output_tokens)
        case_results.append(
            CaseResult(
                case_id=case.id,
                output=completion.text,
                score=quality,
                cost=cost,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            )
        )

    avg_quality = sum(r.score for r in case_results) / len(case_results) if case_results else 0.0
    total_cost = sum(r.cost for r in case_results)

    return RunResult(
        model=model,
        prompt_template=prompt_template,
        avg_quality=avg_quality,
        total_cost=total_cost,
        case_results=case_results,
    )
