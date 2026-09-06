import pytest

from tokenpilot.gate import decide
from tokenpilot.models import RunResult


def _run(avg_quality, total_cost):
    return RunResult(model="m", prompt_template="p", avg_quality=avg_quality, total_cost=total_cost, case_results=[])


def test_ships_when_quality_drop_within_tolerance():
    baseline = _run(0.90, 1.00)
    candidate = _run(0.85, 0.20)

    decision = decide(baseline, candidate, tolerance=0.1)

    assert decision.ship is True
    assert "ships" in decision.reason
    assert decision.savings == 0.80
    assert decision.savings_pct == 80.0


def test_rejects_when_quality_drop_exceeds_tolerance():
    baseline = _run(0.90, 1.00)
    candidate = _run(0.40, 0.20)

    decision = decide(baseline, candidate, tolerance=0.1)

    assert decision.ship is False
    assert "rejected" in decision.reason
    # forfeited savings are still reported even though we don't ship
    assert decision.savings == 0.80
    assert decision.savings_pct == 80.0


def test_quality_drop_exactly_at_tolerance_ships():
    baseline = _run(0.90, 1.00)
    candidate = _run(0.80, 0.50)

    decision = decide(baseline, candidate, tolerance=0.1)

    assert decision.ship is True
    assert decision.quality_drop == pytest.approx(0.1)
