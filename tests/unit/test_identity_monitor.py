"""Tests for IdentityMonitor: periodic drift evaluation.

Test cases:
1. All invariants within tolerance -> confirmed
2. One invariant exceeds tolerance -> uncertain
3. Drift consistently rising -> forked
4. No drift history -> confirmed
5. drift_values correctly calculated
"""
import pytest

from polytwin.core.identity_monitor import IdentityMonitor


def _config(**overrides) -> dict:
    """Build config with optional overrides."""
    defaults = {
        "identity_check_interval": 1.0,
        "drift_tolerance": 0.05,
        "drift_trend_window": 100,
        "drift_trend_threshold": 0.02,
        "identity_uncertain_timeout": 30.0,
    }
    defaults.update(overrides)
    return defaults


# ── Test 1: All within tolerance -> confirmed ───────────────────────


class TestConfirmed:
    @pytest.mark.asyncio
    async def test_all_invariants_within_tolerance(self):
        """All invariants within tolerance -> confirmed."""
        monitor = IdentityMonitor(_config(drift_tolerance=0.05))
        invariants = {
            "temp": {"expected": 100.0, "actual": 101.0},
            "pressure": {"expected": 50.0, "actual": 50.5},
        }
        result = await monitor.check_identity("obj-1", invariants)
        assert result.identity_status == "confirmed"

    @pytest.mark.asyncio
    async def test_exactly_at_tolerance_boundary(self):
        """Drift exactly at tolerance boundary -> confirmed (<=)."""
        monitor = IdentityMonitor(_config(drift_tolerance=0.05))
        invariants = {
            "temp": {"expected": 100.0, "actual": 105.0},  # drift = 0.05 exactly
        }
        result = await monitor.check_identity("obj-1", invariants)
        assert result.identity_status == "confirmed"


# ── Test 2: One exceeds -> uncertain ────────────────────────────────


class TestUncertain:
    @pytest.mark.asyncio
    async def test_one_invariant_exceeds_tolerance(self):
        """One invariant exceeds tolerance (no rising trend) -> uncertain."""
        monitor = IdentityMonitor(_config(drift_tolerance=0.05, drift_trend_threshold=0.5))
        invariants = {
            "temp": {"expected": 100.0, "actual": 108.0},  # drift = 0.08 > 0.05
        }
        result = await monitor.check_identity("obj-1", invariants)
        assert result.identity_status == "uncertain"


# ── Test 3: Rising trend -> forked ─────────────────────────────────


class TestForked:
    @pytest.mark.asyncio
    async def test_drift_rising_trend_forked(self):
        """Drift exceeds tolerance AND rising trend -> forked."""
        monitor = IdentityMonitor(
            _config(drift_tolerance=0.05, drift_trend_threshold=0.01)
        )
        # First check: low drift
        await monitor.check_identity(
            "obj-1", {"temp": {"expected": 100.0, "actual": 102.0}}
        )
        # Second check: high drift, clearly rising
        result = await monitor.check_identity(
            "obj-1", {"temp": {"expected": 100.0, "actual": 115.0}}
        )
        # drift went from 0.02 to 0.15, increase of 0.13 > threshold 0.01
        # and 0.15 > tolerance 0.05
        assert result.identity_status == "forked"


# ── Test 4: No drift history -> confirmed ───────────────────────────


class TestNoHistory:
    @pytest.mark.asyncio
    async def test_no_drift_history_confirmed(self):
        """First check with invariants within tolerance -> confirmed."""
        monitor = IdentityMonitor(_config(drift_tolerance=0.05))
        invariants = {
            "temp": {"expected": 100.0, "actual": 100.5},
        }
        result = await monitor.check_identity("obj-new", invariants)
        assert result.identity_status == "confirmed"

    @pytest.mark.asyncio
    async def test_empty_invariants_confirmed(self):
        """No invariants -> confirmed (all within tolerance vacuously)."""
        monitor = IdentityMonitor(_config())
        result = await monitor.check_identity("obj-empty", {})
        assert result.identity_status == "confirmed"


# ── Test 5: drift_values correctly calculated ──────────────────────


class TestDriftValues:
    @pytest.mark.asyncio
    async def test_drift_values_computed(self):
        """drift_values are correctly computed for each invariant."""
        monitor = IdentityMonitor(_config(drift_tolerance=0.5))
        invariants = {
            "temp": {"expected": 100.0, "actual": 110.0},
            "pressure": {"expected": 50.0, "actual": 48.0},
        }
        result = await monitor.check_identity("obj-1", invariants)
        assert "temp" in result.drift_values
        assert "pressure" in result.drift_values
        assert abs(result.drift_values["temp"] - 0.1) < 1e-9
        assert abs(result.drift_values["pressure"] - 0.04) < 1e-9

    @pytest.mark.asyncio
    async def test_drift_zero_expected(self):
        """When expected is 0, uses 1e-9 denominator -> large drift."""
        monitor = IdentityMonitor(_config(drift_tolerance=0.05))
        invariants = {
            "offset": {"expected": 0.0, "actual": 1.0},
        }
        result = await monitor.check_identity("obj-1", invariants)
        # drift = 1.0 / 1e-9 = very large, but let's check it's computed
        assert result.drift_values["offset"] > 0
