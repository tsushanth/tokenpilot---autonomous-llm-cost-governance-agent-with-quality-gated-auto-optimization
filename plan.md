# TokenPilot — Local MVP Scaffold Plan

## Goal of this MVP

Prove the one thing that differentiates TokenPilot from dashboards (Langfuse/Helicone)
and routers (LiteLLM/RouteLLM): **an optimization is only kept if it passes a
quality-regression gate against a real eval set.** Everything else (proxying live
traffic, multi-tenant accounts, billing) is packaging around this core loop and is
out of scope for a local demo.

The demo must show, end-to-end, on the command line:
1. Run a prompt against an eval set on the "expensive" baseline model → cost + quality baseline.
2. Auto-generate a cheaper candidate (compressed prompt and/or routed to a cheaper model).
3. Run the candidate against the same eval set → candidate cost + quality.
4. Compare quality against a tolerance threshold.
5. **Gate**: only write/"ship" the candidate config if quality holds; otherwise reject and explain why, showing the cost savings that were forfeited.

## Stack choice

**Python 3, stdlib + a small number of libraries. No framework.**

- Plain CLI via `argparse` (no Click/Typer needed — one tool, ~4 subcommands).
- `anthropic` SDK for real LLM calls (single provider is enough to prove routing
  across a cheap/expensive tier — e.g. Haiku vs Sonnet/Opus).
- A built-in **mock provider** (canned responses + fabricated token counts) so the
  whole pipeline runs deterministically with zero API key and zero network access —
  this is what graders/reviewers will run.
- Storage = flat JSON files on disk. No database, no server.
- Quality scoring = simple deterministic scorers (exact-match / keyword-overlap /
  numeric-tolerance) defined per eval case, plus an optional LLM-judge scorer that
  only activates when a real API key is present. No embeddings service, no vector DB.

Why this stack: the core value is an algorithm (optimize → evaluate → gate), not a
UI or infrastructure. A single Python package with no framework is the fastest way
to make that algorithm inspectable and testable. Node/TS or Go would work equally
well; Python is chosen because eval/scoring glue code and the Anthropic SDK are
most ergonomic there.

## Explicitly out of scope for this MVP

- **No proxy server / HTTP interception** — the real product is "drop-in proxy",
  but proving the optimize+gate loop doesn't require intercepting live traffic. The
  CLI calls the provider directly on a fixed eval set instead.
- **No auth, accounts, or multi-tenancy** — single local user, single machine.
- **No billing/usage metering integration** — cost is computed locally from
  token counts × a hardcoded price table, not pulled from a billing API.
- **No hosting/deploy** — runs only via `python -m tokenpilot` on localhost.
- **No database** — JSON files on disk are sufficient for one user's eval sets and run history.
- **No multi-provider routing (OpenAI/Gemini/etc.)** — one provider (Anthropic)
  with two model tiers is enough to demonstrate auto-routing savings; adding more
  providers is a config change, not a new capability.
- **No continuous/production monitoring loop** — this is a one-shot `run` command,
  not a background agent watching live traffic.
- **No dashboard/web UI** — CLI table output only.

## File / directory layout

```
tokenpilot/
  __init__.py
  cli.py              # argparse entrypoint: run, list-runs, show-run subcommands
  providers.py         # Provider protocol; AnthropicProvider + MockProvider; price table
  optimizer.py         # generate_candidate(): prompt compression + cheaper-model routing
  evaluator.py         # run_eval_set(): executes a prompt+model over eval cases, scores outputs
  scoring.py            # exact_match, keyword_overlap, numeric_tolerance, llm_judge (optional)
  gate.py               # decide(baseline_result, candidate_result, thresholds) -> ship/reject + reason
  models.py             # dataclasses: Task, EvalCase, RunResult, GateDecision
  store.py              # read/write task + run-history JSON under ./runs/

examples/
  support_bot_task.json   # sample task: prompt template + ~10 eval cases w/ expected answers
  refund_bot_task.json     # second example tuned to demonstrate a REJECTED optimization

tests/
  test_optimizer.py    # compression shrinks tokens; routing picks cheaper model
  test_evaluator.py    # scoring functions behave correctly on known cases
  test_gate.py          # threshold math: accepts small quality delta, rejects large one
  test_cli_end_to_end.py # runs `tokenpilot run` with --mock and asserts on output/exit code

pyproject.toml         # deps: anthropic, pytest (dev)
README.md              # quickstart: install, run with --mock, run with a real API key
```

## Verification plan

**Automated (pytest):**
- `test_optimizer.py` — compressed prompt has fewer tokens than original; cheaper
  model is selected when baseline is the expensive tier.
- `test_evaluator.py` — each scorer returns expected pass/fail on hand-crafted cases.
- `test_gate.py` — decision logic: quality drop within tolerance → `ship`; quality
  drop beyond tolerance → `reject`, with the reason and forfeited savings reported.
- `test_cli_end_to_end.py` — invokes the CLI with `--mock`, asserts a shipped run
  and a rejected run both produce correct exit codes and JSON output.

**Manual run-through (no API key required):**
```
python -m tokenpilot run examples/support_bot_task.json --mock
# expect: baseline cost/quality, candidate cost/quality, gate = SHIP, % cost saved

python -m tokenpilot run examples/refund_bot_task.json --mock
# expect: candidate quality drop exceeds threshold, gate = REJECT, savings forfeited, reason printed
```

**Manual run-through (optional, with real API key):**
```
export ANTHROPIC_API_KEY=...
python -m tokenpilot run examples/support_bot_task.json
# same flow against real Haiku/Sonnet calls, confirming the loop holds with live data
```

Success criteria: both example tasks run deterministically under `--mock`, one
demonstrates a shipped optimization and one demonstrates a correctly rejected
one — proving the gate is real, not decorative.
