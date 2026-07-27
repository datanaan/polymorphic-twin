"""Four-state constraint evaluator with domain_of_validity support.

Evaluates constraint cards from a DomainPack, returning one of four
states: PASSED, UNCERTAIN, FAILED, or NOT_APPLICABLE.

Conservative principles:
- Missing state variables still allow evaluation (not skipped).
- Unknown sensor status still allows evaluation (not skipped).
- No domain_of_validity defined means *always* applicable.
"""

from __future__ import annotations

from polytwin.core.rules.registry import get_validator
from polytwin.core.types import SingleConstraintResult
from polytwin.tom.types import ConstraintStatus, Criticality, Rigidity

# ── Domain of validity ──────────────────────────────────────────────


def evaluate_domain_of_validity(
    conditions: list[dict],
    match_mode: str,
    state_values: dict[str, float],
    identity_confidence: float = 1.0,
    sensor_status: dict[str, str] | None = None,
) -> bool:
    """Determine whether a constraint is applicable given current state.

    Args:
        conditions: List of condition dicts from the domain_of_validity block.
        match_mode: ``"all"`` (AND) or ``"any"`` (OR).
        state_values: Current state variable values.
        identity_confidence: Current identity confidence (0-1).
        sensor_status: Map of sensor_id -> status string.

    Returns:
        True if the constraint is applicable, False otherwise.

    Conservative defaults:
        - No conditions → always applicable (liberal).
        - Missing variable → still applicable.
        - Unknown sensor → still applicable.
    """
    if sensor_status is None:
        sensor_status = {}

    if not conditions:
        return True  # Liberal default: no domain → always applicable

    results: list[bool] = []
    for cond in conditions:
        ctype = cond.get("type", "")

        if ctype == "state_range":
            variable = cond.get("variable", "")
            val = state_values.get(variable)
            if val is None:
                results.append(True)  # Conservative: missing → applicable
                continue
            lo = cond.get("min", float("-inf"))
            hi = cond.get("max", float("inf"))
            inclusive = cond.get("inclusive", True)
            if inclusive:
                results.append(lo <= val <= hi)
            else:
                results.append(lo < val < hi)

        elif ctype == "state_enum":
            # Conservative default: always applicable for enum checks
            results.append(True)

        elif ctype == "sensor_status":
            sensor_id = cond.get("sensor_id", "")
            status = sensor_status.get(sensor_id, "unknown")
            if status == "unknown":
                results.append(True)  # Conservative: unknown → applicable
            else:
                results.append(status == cond.get("required_status", "active"))

        elif ctype == "composite":
            sub = evaluate_domain_of_validity(
                cond.get("sub_conditions", []),
                cond.get("operator", "and"),
                state_values,
                identity_confidence,
                sensor_status,
            )
            results.append(sub)

        elif ctype == "identity_confidence":
            min_conf = cond.get("min_confidence", 0.0)
            results.append(identity_confidence >= min_conf)

        else:
            # Unknown condition type → conservative: applicable
            results.append(True)

    if match_mode == "any":
        return any(results)
    return all(results)


# ── Main evaluator ──────────────────────────────────────────────────


def evaluate_constraint(
    constraint_card: dict,
    state_values: dict[str, float],
    identity_confidence: float = 1.0,
    sensor_status: dict[str, str] | None = None,
) -> SingleConstraintResult:
    """Evaluate a single constraint card.

    Steps:
        1. Check domain_of_validity — if not applicable, return early.
        2. Look up the validation method in the registry.
        3. Run the validator and return the result.

    Args:
        constraint_card: A constraint card dict (from DomainPack).
        state_values: Current state variable values.
        identity_confidence: Current identity confidence (0-1).
        sensor_status: Map of sensor_id -> status string.

    Returns:
        A ``SingleConstraintResult`` with the evaluation outcome.
    """
    if sensor_status is None:
        sensor_status = {}

    constraint_id = constraint_card.get("constraint_id", "unknown")
    rigidity = Rigidity(constraint_card.get("rigidity", "absolute"))
    criticality = Criticality(
        constraint_card.get("scenario_criticality",
                            constraint_card.get("criticality", "operational"))
    )

    # 1. Domain of validity
    dov = constraint_card.get("domain_of_validity", {})
    conditions = dov.get("conditions", []) if isinstance(dov, dict) else []
    match_mode = dov.get("match_mode", "all") if isinstance(dov, dict) else "all"

    applicable = evaluate_domain_of_validity(
        conditions, match_mode, state_values, identity_confidence, sensor_status
    )

    if not applicable:
        return SingleConstraintResult(
            constraint_id=constraint_id,
            status=ConstraintStatus.NOT_APPLICABLE,
            actual_values=state_values,
            rigidity=rigidity,
            criticality=criticality,
            message="Constraint not applicable (domain_of_validity excluded).",
        )

    # 2. Run validation
    validation = constraint_card.get("validation", {})
    method = validation.get("method", "range_check")
    config = validation.get("config", {})

    validator_fn = get_validator(method)
    status = validator_fn(state_values, config)

    return SingleConstraintResult(
        constraint_id=constraint_id,
        status=status,
        actual_values=state_values,
        threshold=config,
        rigidity=rigidity,
        criticality=criticality,
        message=_build_message(constraint_id, status, method),
    )


def _build_message(constraint_id: str, status: ConstraintStatus, method: str) -> str:
    """Return a human-readable message for the evaluation result."""
    if status == ConstraintStatus.PASSED:
        return f"Constraint {constraint_id} passed ({method})."
    if status == ConstraintStatus.FAILED:
        return f"Constraint {constraint_id} failed ({method})."
    if status == ConstraintStatus.UNCERTAIN:
        return f"Constraint {constraint_id} uncertain — insufficient data ({method})."
    return f"Constraint {constraint_id} {status.value}."
