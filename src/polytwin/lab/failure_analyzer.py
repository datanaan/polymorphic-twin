"""Failure correlation analyzer: discovers patterns in failure event sequences.

Analyzes desensitized failure logs released by Core to find correlations
between events. The Lab only sees desensitized data — no hidden validation
set references or internal Core state.
"""
from __future__ import annotations

import uuid

from polytwin.lab.types import CorrelationFinding, ExplorationBudget


class FailureAnalyzer:
    """Correlates failure events from desensitized logs.

    The analyzer looks for temporal and causal patterns in failure
    event sequences, producing CorrelationFinding instances that
    describe the strength and significance of discovered correlations.
    """

    async def analyze(
        self,
        failure_logs: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> list[CorrelationFinding]:
        """Analyze failure logs for correlation patterns.

        Args:
            failure_logs: Desensitized failure log records.
            budget: Optional resource budget.

        Returns:
            List of CorrelationFinding instances.
        """
        if not failure_logs:
            return []

        findings: list[CorrelationFinding] = []

        # Group events by proximity (sequential events that share variables)
        for i in range(len(failure_logs) - 1):
            event_a = failure_logs[i]
            event_b = failure_logs[i + 1]

            shared_vars = self._find_shared_variables(event_a, event_b)
            if shared_vars:
                correlation_strength = self._compute_correlation(event_a, event_b)
                findings.append(
                    CorrelationFinding(
                        finding_id=str(uuid.uuid4()),
                        event_sequence=[event_a, event_b],
                        correlation_strength=correlation_strength,
                        statistical_significance=correlation_strength * 0.9,
                    )
                )

        return findings

    @staticmethod
    def _find_shared_variables(event_a: dict, event_b: dict) -> set[str]:
        """Find state variables mentioned in both events."""
        vars_a = set(event_a.get("variables", {}).keys()) if isinstance(event_a.get("variables"), dict) else set()
        vars_b = set(event_b.get("variables", {}).keys()) if isinstance(event_b.get("variables"), dict) else set()
        return vars_a & vars_b

    @staticmethod
    def _compute_correlation(event_a: dict, event_b: dict) -> float:
        """Compute a simple correlation score between two events.

        This is a heuristic based on shared variables and temporal proximity.
        """
        shared = 0
        total = 0

        keys_a = set(event_a.get("variables", {}).keys()) if isinstance(event_a.get("variables"), dict) else set()
        keys_b = set(event_b.get("variables", {}).keys()) if isinstance(event_b.get("variables"), dict) else set()
        all_keys = keys_a | keys_b

        if not all_keys:
            return 0.0

        for key in all_keys:
            total += 1
            if key in keys_a and key in keys_b:
                shared += 1

        return shared / total if total > 0 else 0.0
