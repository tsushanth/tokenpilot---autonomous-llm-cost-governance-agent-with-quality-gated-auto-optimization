"""argparse entrypoint: run, list-runs, show-run."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from tokenpilot import gate, optimizer, store
from tokenpilot.evaluator import run_eval_set
from tokenpilot.providers import AnthropicProvider, MockProvider


def cmd_run(args) -> int:
    task = store.load_task(args.task_file)
    provider = MockProvider(task.eval_cases) if args.mock else AnthropicProvider(api_key=args.api_key)

    baseline = run_eval_set(provider, task.baseline_model, task.prompt_template, task.eval_cases)
    candidate_spec = optimizer.generate_candidate(task)
    candidate = run_eval_set(
        provider, candidate_spec["model"], candidate_spec["prompt_template"], task.eval_cases
    )
    decision = gate.decide(baseline, candidate, task.quality_tolerance)

    _print_report(task, baseline, candidate, decision)

    run_id, path = store.save_run(
        task.name,
        {
            "baseline": asdict(baseline),
            "candidate": asdict(candidate),
            "decision": asdict(decision),
        },
        runs_dir=args.runs_dir,
    )
    print(f"\nSaved run {run_id} -> {path}")

    return 0 if decision.ship else 1


def _print_report(task, baseline, candidate, decision) -> None:
    print(f"Task: {task.name}")
    print(f"{'':12}{'model':<28}{'quality':>10}{'cost ($)':>12}")
    print(f"{'baseline':12}{baseline.model:<28}{baseline.avg_quality:>10.3f}{baseline.total_cost:>12.6f}")
    print(f"{'candidate':12}{candidate.model:<28}{candidate.avg_quality:>10.3f}{candidate.total_cost:>12.6f}")
    print()
    verdict = "SHIP" if decision.ship else "REJECT"
    print(f"Gate: {verdict}")
    print(f"Reason: {decision.reason}")
    if decision.ship:
        print(f"Cost saved: ${decision.savings:.6f} ({decision.savings_pct:.1f}%)")
    else:
        print(f"Savings forfeited: ${decision.savings:.6f} ({decision.savings_pct:.1f}%) -- not worth the quality risk")


def cmd_list_runs(args) -> int:
    records = store.list_runs(task_name=args.task_name, runs_dir=args.runs_dir)
    if not records:
        print("No runs found.")
        return 0

    print(f"{'run_id':<45}{'task':<16}{'gate':<8}{'savings %':>10}")
    for record in records:
        decision = record["decision"]
        verdict = "SHIP" if decision["ship"] else "REJECT"
        print(
            f"{record['run_id']:<45}{record['task_name']:<16}{verdict:<8}{decision['savings_pct']:>9.1f}%"
        )
    return 0


def cmd_show_run(args) -> int:
    try:
        record = store.load_run(args.run_id, runs_dir=args.runs_dir)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(json.dumps(record, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenpilot")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a task through optimize -> evaluate -> gate")
    run_p.add_argument("task_file", help="Path to a task JSON file")
    run_p.add_argument("--mock", action="store_true", help="Use the deterministic mock provider (no API key)")
    run_p.add_argument("--api-key", default=None, help="Anthropic API key (else ANTHROPIC_API_KEY env var)")
    run_p.add_argument("--runs-dir", type=Path, default=store.DEFAULT_RUNS_DIR)
    run_p.set_defaults(func=cmd_run)

    list_p = sub.add_parser("list-runs", help="List saved run history")
    list_p.add_argument("task_name", nargs="?", default=None)
    list_p.add_argument("--runs-dir", type=Path, default=store.DEFAULT_RUNS_DIR)
    list_p.set_defaults(func=cmd_list_runs)

    show_p = sub.add_parser("show-run", help="Show full JSON detail for one run")
    show_p.add_argument("run_id")
    show_p.add_argument("--runs-dir", type=Path, default=store.DEFAULT_RUNS_DIR)
    show_p.set_defaults(func=cmd_show_run)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
