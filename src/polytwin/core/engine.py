"""ConstraintEngine: main orchestrator for the Core constraint governance.

Ties together constraint evaluation, safety fallback, and audit logging
into a single validation loop.  The key invariant is M2-C2: a
safety_critical violation immediately triggers fallback and stops further
evaluation — no additional constraints are checked after a safety interrupt.
"""
from __future__ import annotations

from polytwin.core.audit import AuditLogWriter
from polytwin.core.fallback import SafetyFallback
from polytwin.core.rules.combinator import combine
from polytwin.core.rules.evaluator import evaluate_constraint
from polytwin.core.types import ValidationResult
from polytwin.tom.types import ConstraintStatus, Criticality


class ConstraintEngine:
    """Main validation orchestrator for the Core constraint engine.

    Orchestrates constraint evaluation with safety-critical interrupt
    semantics, audit logging, and safety fallback execution.

    Args:
        domain_pack: Optional DomainPack configuration dict.
        audit_writer: Optional AuditLogWriter instance (created if None).
        fallback_handler: Optional SafetyFallback instance (created if None).
    """

    def __init__(
        self,
        domain_pack: dict | None = None,
        audit_writer: AuditLogWriter | None = None,
        fallback_handler: SafetyFallback | None = None,
    ) -> None:
        self.domain_pack = domain_pack or {}
        self.audit = audit_writer or AuditLogWriter()
        self.fallback = fallback_handler or SafetyFallback()

    async def validate(
        self,
        state_values: dict[str, float],
        constraint_cards: list[dict],
        identity_confidence: float = 1.0,
        sensor_status: dict | None = None,
    ) -> ValidationResult:
        """M2-C2: Main validation loop with safety_critical interrupt.

        Evaluates constraint cards in order.  When a safety_critical
        constraint fails, immediately triggers safety fallback and STOPS
        evaluation — no further constraints are checked.

        Args:
            state_values: Current state variable values.
            constraint_cards: Constraint card dicts from DomainPack.
            identity_confidence: Current identity confidence (0-1).
            sensor_status: Map of sensor_id -> status string.

        Returns:
            ValidationResult with combined outcome and safety_fallback_triggered.
        """
        if sensor_status is None:
            sensor_status = {}

        results = []
        safety_fallback_triggered = False

        for card in constraint_cards:
            result = evaluate_constraint(
                card, state_values, identity_confidence, sensor_status
            )

            if result.status == ConstraintStatus.NOT_APPLICABLE:
                continue  # Suspend constraint

            results.append(result)

            # M2-C2: Safety_critical interrupt
            if (
                result.status == ConstraintStatus.FAILED
                and result.criticality == Criticality.SAFETY_CRITICAL
            ):
                safety_fallback_triggered = True
                # Trigger fallback and STOP evaluation
                # SafetyFallback expects a dict with "violated_constraint" key
                fallback_info = {"violated_constraint": result.constraint_id}
                await self.fallback.execute({}, fallback_info, self.domain_pack)
                break  # INTERRUPT — don't evaluate further

        # Combine results
        combined = combine(results, mode="priority")
        combined.safety_fallback_triggered = safety_fallback_triggered
        combined.evaluated_count = len(results)

        # Write audit
        await self.audit.write(
            "constraint_validation",
            "core_engine",
            {
                "evaluated": len(results),
                "passed": combined.passed,
                "safety_fallback": safety_fallback_triggered,
            },
        )

        return combined
