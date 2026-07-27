"""Constraint boundary edge case tests (M7).

Tests for conservative evaluation behavior at constraint boundaries:
- Missing state variables -> conservative (UNCERTAIN)
- domain_of_validity with missing variable -> conservative (applicable)
- safety_critical not_applicable -> no fallback triggered
- HardGate uncertain -> conservative deny/degrade
- Exact boundary values handled correctly
"""

from __future__ import annotations

import pytest

from polytwin.core.audit import AuditLogWriter
from polytwin.core.engine import ConstraintEngine
from polytwin.core.fallback import SafetyFallback
from polytwin.core.hardgate import HardGate
from polytwin.core.rules.evaluator import evaluate_constraint, evaluate_domain_of_validity
from polytwin.tom.types import ConstraintStatus

pytestmark = pytest.mark.security


class TestConstraintBoundary:
    """Edge case handling at constraint evaluation boundaries."""

    # ── domain_of_validity boundary cases ────────────────────────────────

    def test_missing_variable_conservative_evaluation(self) -> None:
        """domain_of_validity with missing variable -> conservative (applicable).

        If the state variable referenced in a domain_of_validity condition
        is not present in state_values, the constraint should still be
        considered applicable (conservative default).
        """
        conditions = [
            {"type": "state_range", "variable": "pressure", "min": 0, "max": 100},
        ]
        # "pressure" is NOT in state_values
        state_values = {"temperature": 65.0}

        result = evaluate_domain_of_validity(conditions, "all", state_values)
        assert result is True, "Missing variable should result in applicable (conservative)"

    def test_missing_variable_in_validation(self) -> None:
        """Constraint evaluation with missing variable -> UNCERTAIN.

        If the state variable needed by the validator is missing,
        the result should be UNCERTAIN (conservative).
        """
        card = {
            "constraint_id": "cc-pressure",
            "rigidity": "absolute",
            "scenario_criticality": "operational",
            "validation": {
                "method": "range_check",
                "config": {"variable": "pressure", "min": 0, "max": 100},
            },
        }
        state_values = {"temperature": 65.0}  # "pressure" missing

        result = evaluate_constraint(card, state_values)
        assert result.status == ConstraintStatus.UNCERTAIN

    def test_empty_domain_of_validity_always_applicable(self) -> None:
        """No domain_of_validity -> always applicable (liberal default)."""
        result = evaluate_domain_of_validity([], "all", {})
        assert result is True

    def test_unknown_condition_type_conservative(self) -> None:
        """Unknown domain_of_validity condition type -> applicable (conservative)."""
        conditions = [
            {"type": "unknown_condition_type", "variable": "x"},
        ]
        result = evaluate_domain_of_validity(conditions, "all", {})
        assert result is True

    # ── Boundary value handling ───────────────────────────────────────────

    def test_evaluator_exact_boundary_inclusive(self) -> None:
        """Exact boundary values handled correctly for inclusive bounds.

        temperature = 180.0 with max=180 (inclusive=True) -> PASSED
        """
        card = {
            "constraint_id": "cc-temp-boundary",
            "rigidity": "absolute",
            "scenario_criticality": "operational",
            "validation": {
                "method": "range_check",
                "config": {"variable": "temperature", "min": 0, "max": 180, "inclusive": True},
            },
        }
        state_values = {"temperature": 180.0}

        result = evaluate_constraint(card, state_values)
        assert result.status == ConstraintStatus.PASSED

    def test_evaluator_just_over_boundary_inclusive(self) -> None:
        """temperature = 180.01 with max=180 (inclusive) -> FAILED."""
        card = {
            "constraint_id": "cc-temp-over",
            "rigidity": "absolute",
            "scenario_criticality": "operational",
            "validation": {
                "method": "range_check",
                "config": {"variable": "temperature", "max": 180, "inclusive": True},
            },
        }
        state_values = {"temperature": 180.01}

        result = evaluate_constraint(card, state_values)
        assert result.status == ConstraintStatus.FAILED

    def test_evaluator_exact_boundary_exclusive(self) -> None:
        """Exact boundary values with exclusive bounds.

        temperature = 180.0 with max=180 (inclusive=False) -> FAILED
        """
        card = {
            "constraint_id": "cc-temp-exclusive",
            "rigidity": "absolute",
            "scenario_criticality": "operational",
            "validation": {
                "method": "range_check",
                "config": {"variable": "temperature", "max": 180, "inclusive": False},
            },
        }
        state_values = {"temperature": 180.0}

        result = evaluate_constraint(card, state_values)
        assert result.status == ConstraintStatus.FAILED

    def test_evaluator_exact_lower_boundary_inclusive(self) -> None:
        """temperature = 0.0 with min=0 (inclusive) -> PASSED."""
        card = {
            "constraint_id": "cc-temp-lower",
            "rigidity": "absolute",
            "scenario_criticality": "operational",
            "validation": {
                "method": "range_check",
                "config": {"variable": "temperature", "min": 0, "max": 100, "inclusive": True},
            },
        }
        state_values = {"temperature": 0.0}

        result = evaluate_constraint(card, state_values)
        assert result.status == ConstraintStatus.PASSED

    def test_evaluator_negative_boundary(self) -> None:
        """temperature = -0.1 with min=0 (inclusive) -> FAILED."""
        card = {
            "constraint_id": "cc-temp-neg",
            "rigidity": "absolute",
            "scenario_criticality": "operational",
            "validation": {
                "method": "range_check",
                "config": {"variable": "temperature", "min": 0, "max": 100, "inclusive": True},
            },
        }
        state_values = {"temperature": -0.1}

        result = evaluate_constraint(card, state_values)
        assert result.status == ConstraintStatus.FAILED

    # ── safety_critical edge cases ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_safety_critical_not_applicable_no_fallback(self) -> None:
        """safety_critical constraint in not_applicable state -> no fallback.

        When a safety_critical constraint is outside its domain_of_validity,
        it should return NOT_APPLICABLE, and no safety fallback should be triggered.
        """
        engine = ConstraintEngine(
            audit_writer=AuditLogWriter(),
            fallback_handler=SafetyFallback(),
        )
        cards = [
            {
                "constraint_id": "cc-safety-oob",
                "scenario_criticality": "safety_critical",
                "rigidity": "absolute",
                "domain_of_validity": {
                    "conditions": [
                        {"type": "state_range", "variable": "mode", "min": 1, "max": 1},
                    ],
                    "match_mode": "all",
                },
                "validation": {
                    "method": "range_check",
                    "config": {"variable": "temperature", "min": 0, "max": 100},
                },
            }
        ]
        # mode=2 means safety_critical constraint is out of domain
        state_values = {"temperature": 150.0, "mode": 2.0}

        result = await engine.validate(state_values, cards)

        # Should NOT trigger fallback because constraint is not applicable
        assert result.safety_fallback_triggered is False

    @pytest.mark.asyncio
    async def test_multiple_constraints_safety_interrupt_stops_evaluation(self) -> None:
        """When safety_critical fails, evaluation stops immediately.

        No further constraints are evaluated after a safety interrupt.
        """
        engine = ConstraintEngine(
            audit_writer=AuditLogWriter(),
            fallback_handler=SafetyFallback(),
        )
        cards = [
            {
                "constraint_id": "cc-safety-first",
                "scenario_criticality": "safety_critical",
                "rigidity": "absolute",
                "validation": {
                    "method": "range_check",
                    "config": {"variable": "temperature", "min": 0, "max": 100},
                },
            },
            {
                "constraint_id": "cc-operational-second",
                "scenario_criticality": "operational",
                "rigidity": "absolute",
                "validation": {
                    "method": "range_check",
                    "config": {"variable": "pressure", "min": 0, "max": 50},
                },
            },
        ]
        # Temperature out of range triggers safety_critical failure
        state_values = {"temperature": 150.0, "pressure": 10.0}

        result = await engine.validate(state_values, cards)

        # Safety fallback triggered
        assert result.safety_fallback_triggered is True
        # Only 1 constraint was evaluated (interrupt after safety_critical)
        assert result.evaluated_count == 1

    # ── HardGate boundary cases ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_hardgate_uncertain_conservative_deny(self) -> None:
        """HardGate uncertain -> conservative deny/degrade.

        When state data is missing or uncertain, HardGate should not grant
        full access. Missing variables result in degraded or denied links.
        """
        gate = HardGate()
        # Empty view with no state data
        obj_view = {}
        constraints = [
            {
                "constraint_id": "cc-1",
                "domain_of_validity": {},
            }
        ]
        domain_pack = {
            "state_semantics_template": {
                "variables": [
                    {"name": "temperature", "required": True},
                ],
            },
        }

        result = await gate.evaluate(obj_view, constraints, domain_pack)

        # Should not grant all links when data is missing
        assert len(result.denied_links) > 0 or len(result.degraded_links) > 0

    @pytest.mark.asyncio
    async def test_hardgate_missing_state_denies_semantic_check(self) -> None:
        """Missing required state variables deny state_semantic_compatibility."""
        gate = HardGate()
        obj_view = {"state_semantics": {"current_values": {}}}
        constraints = []
        domain_pack = {
            "state_semantics_template": {
                "variables": [
                    {"name": "temperature", "required": True},
                    {"name": "pressure", "required": True},
                ],
            },
        }

        result = await gate.evaluate(obj_view, constraints, domain_pack)
        assert "state_semantic_compatibility" in result.denied_links

    # ── Sensor status boundary ────────────────────────────────────────────

    def test_unknown_sensor_status_conservative(self) -> None:
        """Unknown sensor status -> still applicable (conservative)."""
        conditions = [
            {"type": "sensor_status", "sensor_id": "sensor-xyz", "required_status": "active"},
        ]
        # sensor-xyz not in sensor_status dict -> unknown
        result = evaluate_domain_of_validity(conditions, "all", {}, 1.0, {})
        assert result is True, "Unknown sensor should result in applicable (conservative)"

    def test_offline_sensor_denied(self) -> None:
        """Offline sensor -> not applicable for that condition."""
        conditions = [
            {"type": "sensor_status", "sensor_id": "sensor-1", "required_status": "active"},
        ]
        sensor_status = {"sensor-1": "offline"}
        result = evaluate_domain_of_validity(conditions, "all", {}, 1.0, sensor_status)
        assert result is False, "Offline sensor should make condition not applicable"
