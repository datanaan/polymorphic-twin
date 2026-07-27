"""Tests for ConstraintEngine: main orchestrator.

Test cases:
1. All constraints pass -> ValidationResult.passed = True
2. Operational failure -> passed = False, no safety fallback
3. M2-C2: safety_critical violation stops further evaluation
4. NOT_APPLICABLE constraints are skipped
5. Audit event written after validation
6. Empty constraint list -> passed = True
"""
import pytest

from polytwin.core.audit import AuditLogWriter
from polytwin.core.engine import ConstraintEngine


def _card(
    constraint_id: str = "c_temp",
    variable: str = "temperature",
    method: str = "range_check",
    config: dict | None = None,
    criticality: str = "operational",
    will_fail: bool = False,
    will_pass: bool = False,
    domain_conditions: list | None = None,
) -> dict:
    """Build a constraint card dict for testing.

    Args:
        will_fail: If True, configure a constraint that will fail (value > max).
        will_pass: If True, configure a constraint that will pass.
    """
    if config is not None:
        pass  # use provided config
    elif will_fail:
        config = {"variable": variable, "max": 0.0}  # any positive value fails
    elif will_pass:
        config = {"variable": variable, "max": 10000.0}  # generous max
    else:
        config = {"variable": variable, "max": 180.0}

    dov: dict = {}
    if domain_conditions is not None:
        dov = {"conditions": domain_conditions, "match_mode": "all"}

    return {
        "constraint_id": constraint_id,
        "scenario_criticality": criticality,
        "validation": {"method": method, "config": config},
        "domain_of_validity": dov,
    }


# ── Test 1: All pass ────────────────────────────────────────────────


class TestAllPass:
    @pytest.mark.asyncio
    async def test_all_constraints_pass(self):
        """All constraints pass -> ValidationResult.passed = True."""
        cards = [
            _card("c1", "temperature", will_pass=True, criticality="operational"),
            _card("c2", "pressure", will_pass=True, criticality="operational"),
        ]
        engine = ConstraintEngine()
        result = await engine.validate({"temperature": 150, "pressure": 50}, cards)
        assert result.passed is True
        assert result.safety_fallback_triggered is False
        assert result.evaluated_count == 2


# ── Test 2: Operational failure ─────────────────────────────────────


class TestOperationalFailure:
    @pytest.mark.asyncio
    async def test_operational_failure_no_safety_fallback(self):
        """Operational failure -> passed = False, no safety fallback."""
        cards = [
            _card("c1", "temperature", will_fail=True, criticality="operational"),
            _card("c2", "pressure", will_pass=True, criticality="operational"),
        ]
        engine = ConstraintEngine()
        result = await engine.validate({"temperature": 150, "pressure": 50}, cards)
        assert result.passed is False
        assert result.safety_fallback_triggered is False
        assert result.evaluated_count == 2


# ── Test 3: M2-C2 Safety critical interrupt ─────────────────────────


class TestSafetyCriticalInterrupt:
    @pytest.mark.asyncio
    async def test_safety_violation_stops_further_evaluation(self):
        """M2-C2: safety_critical violation interrupts — only 1 constraint evaluated."""
        cards = [
            _card(
                "safety_temp",
                "temperature",
                criticality="safety_critical",
                config={"variable": "temperature", "max": 180.0},
            ),
            _card("oper_press", "pressure", will_fail=True, criticality="operational"),
            _card("oper_quality", "quality", will_pass=True, criticality="operational"),
        ]
        engine = ConstraintEngine()
        result = await engine.validate({"temperature": 190, "pressure": 50, "quality": 80}, cards)
        assert result.safety_fallback_triggered is True
        assert result.evaluated_count == 1  # Only safety constraint was evaluated

    @pytest.mark.asyncio
    async def test_safety_passes_evaluates_all(self):
        """Safety constraint passes -> all constraints evaluated."""
        cards = [
            _card(
                "safety_temp",
                "temperature",
                criticality="safety_critical",
                config={"variable": "temperature", "max": 200.0},
            ),
            _card("oper_press", "pressure", will_pass=True, criticality="operational"),
        ]
        engine = ConstraintEngine()
        result = await engine.validate({"temperature": 150, "pressure": 50}, cards)
        assert result.safety_fallback_triggered is False
        assert result.evaluated_count == 2

    @pytest.mark.asyncio
    async def test_safety_fires_on_first_failure_only(self):
        """First safety_critical failure stops evaluation; later ones not reached."""
        cards = [
            _card(
                "safety_a",
                "temperature",
                criticality="safety_critical",
                config={"variable": "temperature", "max": 100.0},
            ),
            _card(
                "safety_b",
                "pressure",
                criticality="safety_critical",
                will_fail=True,
            ),
        ]
        engine = ConstraintEngine()
        result = await engine.validate({"temperature": 150, "pressure": 80}, cards)
        assert result.safety_fallback_triggered is True
        assert result.evaluated_count == 1  # Stopped at safety_a


# ── Test 4: NOT_APPLICABLE skipped ─────────────────────────────────


class TestNotApplicable:
    @pytest.mark.asyncio
    async def test_not_applicable_constraints_skipped(self):
        """NOT_APPLICABLE constraints are not counted in evaluated results."""
        cards = [
            _card(
                "c_inactive",
                "temperature",
                will_pass=True,
                criticality="operational",
                domain_conditions=[
                    {"type": "state_range", "variable": "temperature", "min": 0, "max": 100}
                ],
            ),
            _card("c_active", "pressure", will_pass=True, criticality="operational"),
        ]
        engine = ConstraintEngine()
        result = await engine.validate(
            {"temperature": 200, "pressure": 50},  # temp outside domain -> NOT_APPLICABLE
            cards,
        )
        assert result.evaluated_count == 1  # Only c_active evaluated
        assert result.passed is True


# ── Test 5: Audit event written ────────────────────────────────────


class TestAuditIntegration:
    @pytest.mark.asyncio
    async def test_audit_event_written(self):
        """Validation writes an audit event."""
        audit = AuditLogWriter()
        engine = ConstraintEngine(audit_writer=audit)
        await engine.validate({"temperature": 150}, [
            _card("c1", will_pass=True, criticality="operational"),
        ])
        assert audit.get_event_count() == 1
        events = await audit.query()
        assert events[0]["event_type"] == "constraint_validation"
        assert events[0]["actor"] == "core_engine"

    @pytest.mark.asyncio
    async def test_audit_records_evaluated_count(self):
        """Audit event records number of evaluated constraints."""
        audit = AuditLogWriter()
        engine = ConstraintEngine(audit_writer=audit)
        await engine.validate({"temperature": 150}, [
            _card("c1", will_pass=True, criticality="operational"),
            _card("c2", will_pass=True, criticality="operational"),
        ])
        events = await audit.query()
        assert events[0]["detail"]["evaluated"] == 2

    @pytest.mark.asyncio
    async def test_audit_records_safety_fallback(self):
        """Audit event records safety fallback trigger."""
        audit = AuditLogWriter()
        engine = ConstraintEngine(audit_writer=audit)
        await engine.validate({"temperature": 200}, [
            _card("safety", criticality="safety_critical", config={"variable": "temperature", "max": 180}),
        ])
        events = await audit.query()
        assert events[0]["detail"]["safety_fallback"] is True


# ── Test 6: Empty constraint list ───────────────────────────────────


class TestEmptyConstraints:
    @pytest.mark.asyncio
    async def test_empty_cards_passes(self):
        """No constraint cards -> passed = True (vacuously)."""
        engine = ConstraintEngine()
        result = await engine.validate({"temperature": 150}, [])
        assert result.passed is True
        assert result.evaluated_count == 0
