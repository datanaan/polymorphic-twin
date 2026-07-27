"""IdentityMonitor: periodic drift evaluation with three states.

Monitors invariant drift for TwinObjects, classifying identity as:
- confirmed: all invariants within tolerance, no rising trend
- uncertain: one or more invariants exceed tolerance, but no rising trend
- forked: invariants exceed tolerance AND drift is consistently rising
"""
from __future__ import annotations

from datetime import UTC, datetime

from polytwin.core.types import DriftSample, IdentityCheckResult


class IdentityMonitor:
    """Evaluate identity drift against configured invariants.

    Tracks historical drift samples to detect rising trends that signal
    identity forking.  Configuration is provided via a dict with keys:
        identity_check_interval (float): seconds between checks (default 1.0)
        drift_tolerance (float): max allowed drift ratio (default 0.05)
        drift_trend_window (int): samples in trend window (default 100)
        drift_trend_threshold (float): min drift increase for rising trend (default 0.02)
        identity_uncertain_timeout (float): seconds before uncertain -> forked (default 30.0)
    """

    def __init__(self, config: dict | None = None) -> None:
        if config is None:
            config = {}
        self.check_interval = config.get("identity_check_interval", 1.0)
        self.drift_tolerance = config.get("drift_tolerance", 0.05)
        self.drift_trend_window = config.get("drift_trend_window", 100)
        self.drift_trend_threshold = config.get("drift_trend_threshold", 0.02)
        self.uncertain_timeout = config.get("identity_uncertain_timeout", 30.0)
        self._samples: dict[str, list[DriftSample]] = {}

    async def check_identity(
        self, obj_id: str, invariants: dict
    ) -> IdentityCheckResult:
        """Evaluate identity drift. Returns confirmed/uncertain/forked.

        Args:
            obj_id: TwinObject identifier.
            invariants: Map of invariant_name -> {"expected": float, "actual": float}.

        Returns:
            IdentityCheckResult with identity_status and drift_values.
        """
        drift_values: dict[str, float] = {}
        for inv_name, inv_data in invariants.items():
            expected = inv_data.get("expected", 0)
            actual = inv_data.get("actual", 0)
            drift = abs(actual - expected) / max(abs(expected), 1e-9)
            drift_values[inv_name] = drift
            self._record_sample(obj_id, inv_name, drift)

        # Check individual drift
        all_within = all(d <= self.drift_tolerance for d in drift_values.values())

        # Check trend
        trend_rising = self._check_trend(obj_id)

        if not all_within and trend_rising:
            status = "forked"
        elif not all_within:
            status = "uncertain"
        else:
            status = "confirmed"

        return IdentityCheckResult(
            identity_status=status,
            drift_values=drift_values,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def _record_sample(
        self, obj_id: str, invariant_name: str, drift: float
    ) -> None:
        """Record a drift sample for trend analysis."""
        if obj_id not in self._samples:
            self._samples[obj_id] = []
        self._samples[obj_id].append(
            DriftSample(
                invariant_name=invariant_name,
                drift=drift,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    def _check_trend(self, obj_id: str) -> bool:
        """Check if drift is consistently rising over the trend window."""
        samples = self._samples.get(obj_id, [])
        if len(samples) < 2:
            return False
        recent = samples[-self.drift_trend_window:]
        return bool(recent[-1].drift > recent[0].drift + self.drift_trend_threshold)
