"""Constraint result combinators.

Combines individual ``SingleConstraintResult`` instances into a single
``ValidationResult`` using four combination modes:

- **AND**: all must pass (NOT_APPLICABLE counts as pass).
- **OR**: at least one must pass.
- **weighted**: weighted score of passing constraints meets threshold.
- **priority**: ordered by criticality; first failure stops.

Any ``identity_critical`` failure automatically sets
``requires_human_review`` on the combined result.
"""

from __future__ import annotations

from polytwin.core.types import SingleConstraintResult, ValidationResult
from polytwin.tom.types import ConstraintStatus, Criticality

# Criticality priority for the *priority* mode (lower = higher priority).
_PRIORITY_ORDER: dict[str, int] = {
    "safety_critical": 0,
    "identity_critical": 1,
    "operational": 2,
    "informational": 3,
}

# States that count as "passing" for AND / priority logic.
_PASSING = {ConstraintStatus.PASSED, ConstraintStatus.NOT_APPLICABLE}


def combine(
    results: list[SingleConstraintResult],
    mode: str = "and",
    weights: dict[str, float] | None = None,
    threshold: float = 0.6,
) -> ValidationResult:
    """Combine individual constraint results into a single verdict.

    Args:
        results: Individual evaluation results.
        mode: Combination mode — ``"and"``, ``"or"``, ``"weighted"``,
              or ``"priority"``.
        weights: Map of constraint_id -> weight (for ``"weighted"`` mode).
        threshold: Minimum weighted score to pass (default 0.6).

    Returns:
        A ``ValidationResult`` summarising the combined outcome.
    """
    if weights is None:
        weights = {}

    # Identity-critical failures always require human review.
    requires_human = any(
        r.criticality == Criticality.IDENTITY_CRITICAL
        and r.status == ConstraintStatus.FAILED
        for r in results
    )

    # Safety-critical failures trigger fallback flag.
    safety_fallback = any(
        r.criticality == Criticality.SAFETY_CRITICAL
        and r.status == ConstraintStatus.FAILED
        for r in results
    )

    passed: bool

    if mode == "and":
        passed = all(r.status in _PASSING for r in results)

    elif mode == "or":
        passed = any(r.status == ConstraintStatus.PASSED for r in results)

    elif mode == "weighted":
        score = sum(
            weights.get(r.constraint_id, 0.0)
            for r in results
            if r.status == ConstraintStatus.PASSED
        )
        passed = score >= threshold

    elif mode == "priority":
        sorted_results = sorted(
            results,
            key=lambda r: _PRIORITY_ORDER.get(r.criticality.value, 99),
        )
        passed = all(r.status in _PASSING for r in sorted_results)

    else:
        # Unknown mode — fall back to AND.
        passed = all(r.status in _PASSING for r in results)

    return ValidationResult(
        passed=passed,
        individual_results=results,
        combination_logic=mode,
        requires_human_review=requires_human,
        safety_fallback_triggered=safety_fallback,
        evaluated_count=len(results),
    )
