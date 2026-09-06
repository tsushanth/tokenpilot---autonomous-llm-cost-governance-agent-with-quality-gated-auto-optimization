# TokenPilot (local MVP)

TokenPilot is a cost-governance agent for teams paying real money for LLM
calls. Dashboards like Langfuse/Helicone tell you what you spent. Routers
like LiteLLM/RouteLLM let you manually point traffic at a cheaper model.
Neither one closes the loop: nothing stops a cost cut from quietly making
your product worse.

This MVP proves the one thing that's actually hard to build safely:

> **An optimization (compressed prompt, cheaper model) only ships if it
> passes a quality-regression gate against your own eval set.**

It's a local CLI, not a proxy. It runs a task's eval set on your expensive
baseline model, auto-generates a cheaper candidate, re-runs the same eval
set on the candidate, and only writes the candidate off as "shipped" if
quality holds within your declared tolerance. If quality drops too much, it
rejects the candidate and tells you exactly how much savings it forfeited to
protect quality.

Everything else a real product would need — a proxy that intercepts live
traffic, multi-tenant accounts, billing integration, a dashboard — is
explicitly out of scope here. See `plan.md` for the full reasoning.

## How it works

```
tokenpilot run <task.json>
  1. run_eval_set(baseline_model, prompt_template)   -> baseline cost + quality
  2. optimizer.generate_candidate(task)              -> compressed prompt + cheap model
  3. run_eval_set(candidate_model, compressed_prompt) -> candidate cost + quality
  4. gate.decide(baseline, candidate, tolerance)      -> SHIP or REJECT + reason
```

A **task** is a JSON file: a prompt template, a baseline model, a quality
tolerance, and a list of eval cases (input + expected answer + scorer).
Scoring is deterministic (`exact_match`, `keyword_overlap`,
`numeric_tolerance`) so the gate's decision is reproducible — no LLM judging
its own homework unless you opt into `llm_judge` with a real API key.

## Quickstart (no API key required)

```bash
pip install -e ".[dev]"   # or just run with stdlib + no anthropic install for --mock

python -m tokenpilot run examples/support_bot_task.json --mock
# -> baseline vs candidate cost/quality table, Gate: SHIP, cost saved

python -m tokenpilot run examples/refund_bot_task.json --mock
# -> Gate: REJECT, with the forfeited savings and why quality didn't hold
```

`--mock` uses a deterministic, zero-network provider with canned responses
baked into the example task files (`mock_baseline` / `mock_candidate` per
eval case), so the whole pipeline runs offline and produces the same result
every time. This is the mode graders/reviewers should use.

### List and inspect run history

```bash
python -m tokenpilot list-runs                # all saved runs
python -m tokenpilot list-runs support_bot     # filter by task
python -m tokenpilot show-run <run_id>         # full JSON detail for one run
```

Every `run` writes a JSON record under `./runs/<task_name>/<run_id>.json` —
no database, just flat files.

### Running against real models

```bash
export ANTHROPIC_API_KEY=...
python -m tokenpilot run examples/support_bot_task.json
```

This calls the real Anthropic API (baseline: `claude-opus-5`, candidate
routed to `claude-haiku-4-5-20251001`) and gates on real completions instead
of canned mock text. Requires the `anthropic` package (`pip install -e .`).

## Writing your own task

```json
{
  "name": "my_bot",
  "baseline_model": "claude-opus-5",
  "prompt_template": "You are ... Answer: {input}",
  "quality_tolerance": 0.1,
  "eval_cases": [
    {
      "id": "case1",
      "input": "some question",
      "scorer": "keyword_overlap",
      "expected": ["keyword1", "keyword2"],
      "mock_baseline": "canned answer for --mock baseline runs",
      "mock_candidate": "canned answer for --mock candidate runs"
    }
  ]
}
```

`mock_baseline` / `mock_candidate` are only used under `--mock`; they're
ignored (and unnecessary) when running against a real API key.

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

`tests/test_cli_end_to_end.py` runs both bundled example tasks through the
full CLI in `--mock` mode and asserts one ships and one is correctly
rejected — proving the gate is real, not decorative.
