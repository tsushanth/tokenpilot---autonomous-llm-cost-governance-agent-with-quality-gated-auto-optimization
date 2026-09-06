"""The quality-regression gate: the one thing that makes an optimization
trustworthy instead of just cheap. A candidate is only worth shipping if its
quality drop from baseline stays within the task's declared tolerance."""

from tokenpilot.models import GateDecision


def decide(baseline, candidate, tolerance: float) -> GateDecision:
    quality_drop = baseline.avg_quality - candidate.avg_quality
    savings = baseline.total_cost - candidate.total_cost
    savings_pct = (savings / baseline.total_cost * 100) if baseline.total_cost else 0.0

    if quality_drop <= tolerance:
        ship = True
        reason = (
            f"Quality drop {quality_drop:.3f} is within tolerance {tolerance:.3f} "
            "-- candidate ships."
        )
    else:
        ship = False
        reason = (
            f"Quality drop {quality_drop:.3f} exceeds tolerance {tolerance:.3f} "
            "-- candidate rejected, keeping baseline."
        )

    return GateDecision(
        ship=ship,
        reason=reason,
        quality_drop=quality_drop,
        tolerance=tolerance,
        baseline_cost=baseline.total_cost,
        candidate_cost=candidate.total_cost,
        savings=savings,
        savings_pct=savings_pct,
    )
