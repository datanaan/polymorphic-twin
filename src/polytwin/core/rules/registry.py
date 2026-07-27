"""Built-in validation function registry.

Provides standard validators that can be referenced by ``method`` in a
constraint card's ``validation`` block.  Custom validators can be
registered at runtime via ``register_validator()``.
"""

from __future__ import annotations

from collections.abc import Callable

from polytwin.tom.types import ConstraintStatus

# Type alias for validator callables.
ValidatorFn = Callable[[dict[str, float], dict], ConstraintStatus]


# ── Registry store ──────────────────────────────────────────────────

_VALIDATORS: dict[str, ValidatorFn] = {}


# ── Public API ──────────────────────────────────────────────────────


def register_validator(name: str, fn: ValidatorFn) -> None:
    """Register a validation function under *name*."""
    _VALIDATORS[name] = fn


def get_validator(name: str) -> ValidatorFn:
    """Return the validator for *name*, falling back to the default."""
    return _VALIDATORS.get(name, default_validator)


# ── Built-in validators ────────────────────────────────────────────


def range_check(state_values: dict[str, float], config: dict) -> ConstraintStatus:
    """Check that a variable falls within [min, max].

    Config keys:
        variable (str): State variable name.
        min (float): Lower bound (optional).
        max (float): Upper bound (optional).
        inclusive (bool): Whether bounds are inclusive (default True).
    """
    var = config.get("variable", "")
    val = state_values.get(var)
    if val is None:
        return ConstraintStatus.UNCERTAIN

    max_val = config.get("max")
    min_val = config.get("min")
    inclusive = config.get("inclusive", True)

    if max_val is not None:
        if inclusive and val > max_val:
            return ConstraintStatus.FAILED
        if not inclusive and val >= max_val:
            return ConstraintStatus.FAILED

    if min_val is not None:
        if inclusive and val < min_val:
            return ConstraintStatus.FAILED
        if not inclusive and val <= min_val:
            return ConstraintStatus.FAILED

    return ConstraintStatus.PASSED


def threshold_exceeded(state_values: dict[str, float], config: dict) -> ConstraintStatus:
    """Check that a variable meets or exceeds a minimum threshold.

    Config keys:
        variable (str): State variable name.
        threshold / min (float): Minimum acceptable value.
    """
    var = config.get("variable", "")
    val = state_values.get(var)
    thresh = config.get("min", config.get("threshold", float("inf")))
    if val is None:
        return ConstraintStatus.UNCERTAIN
    if val < thresh:
        return ConstraintStatus.FAILED
    return ConstraintStatus.PASSED


def enum_membership(state_values: dict[str, float], config: dict) -> ConstraintStatus:
    """Placeholder for enum-variable membership checks.

    Enum checks operate on categorical (string) state values rather than
    numeric ones.  Since the current state_values dict is ``str -> float``,
    this validator always returns PASSED as a conservative default.
    A future iteration will support mixed-type state values.
    """
    return ConstraintStatus.PASSED


def default_validator(state_values: dict[str, float], config: dict) -> ConstraintStatus:
    """Fallback validator used when no matching method is found.

    Returns UNCERTAIN — we cannot make a definitive determination
    without a known validation method.
    """
    return ConstraintStatus.UNCERTAIN


# ── Register built-ins ─────────────────────────────────────────────

register_validator("range_check", range_check)
register_validator("threshold_exceeded", threshold_exceeded)
register_validator("enum_membership", enum_membership)
