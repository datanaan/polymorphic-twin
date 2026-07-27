"""Tests for the in-memory simulation engine (M9b)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from polytwin.domainpack.parser import parse_domainpack
from polytwin.simulator.engine import SimulationEngine, SimulationStep

# ── Helpers ──────────────────────────────────────────────────────────

EXAMPLE_DP = Path("configs/examples/minimal-domain-pack.yaml")


def _run(coro):
    """Run an async coroutine synchronously for testing."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── 1. Simulator with DomainPack -- state settable ───────────────────


class TestSimulatorState:
    """State management tests."""

    def test_set_and_get_state(self):
        engine = SimulationEngine()
        engine.set_state({"temperature": 50.0, "pressure": 10.0})
        state = engine.get_state()
        assert state == {"temperature": 50.0, "pressure": 10.0}

    def test_get_state_returns_copy(self):
        engine = SimulationEngine()
        engine.set_state({"temperature": 50.0})
        state = engine.get_state()
        state["temperature"] = 999.0
        assert engine.get_state()["temperature"] == 50.0

    def test_set_state_overwrites_previous(self):
        engine = SimulationEngine()
        engine.set_state({"a": 1.0})
        engine.set_state({"b": 2.0})
        assert engine.get_state() == {"b": 2.0}


# ── 2. Step validates constraints → returns SimulationStep ───────────


class TestSimulatorStep:
    """Single step validation tests."""

    def test_step_returns_simulation_step(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)
        engine.set_state({"temperature": 50.0, "pressure": 10.0})
        step = _run(engine.step())
        assert isinstance(step, SimulationStep)
        assert step.tick == 1
        assert isinstance(step.passed, bool)
        assert isinstance(step.evaluated, int)
        assert isinstance(step.safety_fallback, bool)

    def test_step_with_valid_state_passes(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)
        # Provide all variables so every constraint reaches a definitive state.
        # vibration_freq and output_quality are needed to avoid UNCERTAIN results.
        engine.set_state({
            "temperature": 50.0,
            "pressure": 10.0,
            "operating_mode": 0.0,
            "vibration_freq": 100.0,
            "output_quality": 90.0,
        })
        step = _run(engine.step())
        assert step.passed is True

    def test_step_with_violating_state_fails(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)
        engine.set_state({"temperature": 200.0, "pressure": 10.0})
        step = _run(engine.step())
        # Temperature 200 exceeds safety limit of 180
        assert step.passed is False
        assert step.safety_fallback is True

    def test_step_records_individual_results(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)
        engine.set_state({"temperature": 50.0, "pressure": 10.0})
        step = _run(engine.step())
        assert isinstance(step.individual, list)
        # Should have evaluated some constraints
        assert len(step.individual) > 0
        for indiv in step.individual:
            assert "id" in indiv
            assert "status" in indiv


# ── 3. Multiple steps → history accumulated ──────────────────────────


class TestSimulatorHistory:
    """History accumulation tests."""

    def test_history_accumulated_over_steps(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)
        engine.set_state({"temperature": 50.0, "pressure": 10.0})

        _run(engine.step())
        _run(engine.step())
        _run(engine.step())

        history = engine.get_history()
        assert len(history) == 3
        assert history[0]["tick"] == 1
        assert history[1]["tick"] == 2
        assert history[2]["tick"] == 3

    def test_history_returns_copy(self):
        engine = SimulationEngine()
        history = engine.get_history()
        history.append({"fake": True})
        assert len(engine.get_history()) == 0


# ── 4. Export results → includes manifest ────────────────────────────


class TestSimulatorExport:
    """Export results tests."""

    def test_export_includes_manifest(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)
        engine.set_state({"temperature": 50.0, "pressure": 10.0})
        _run(engine.step())
        _run(engine.step())

        results = engine.export_results()
        assert "manifest" in results
        assert results["manifest"]["domain_pack"] == dp.domain_id
        assert results["manifest"]["ticks"] == 2
        assert "exported_at" in results["manifest"]

    def test_export_includes_history(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)
        engine.set_state({"temperature": 50.0, "pressure": 10.0})
        _run(engine.step())

        results = engine.export_results()
        assert "history" in results
        assert len(results["history"]) == 1
        assert results["history"][0]["tick"] == 1

    def test_export_manifest_timestamp_is_iso_format(self):
        engine = SimulationEngine()
        results = engine.export_results()
        ts = results["manifest"]["exported_at"]
        # Should be parseable as ISO format
        assert "T" in ts


# ── 5. Empty DomainPack → no constraints, always passes ─────────────


class TestSimulatorEmptyDomainPack:
    """Empty / no DomainPack tests."""

    def test_no_domain_pack_always_passes(self):
        engine = SimulationEngine()  # No DomainPack
        engine.set_state({"anything": 42.0})
        step = _run(engine.step())
        assert step.passed is True
        assert step.evaluated == 0
        assert step.safety_fallback is False
        assert step.individual == []

    def test_export_without_domain_pack(self):
        engine = SimulationEngine()
        _run(engine.step())
        results = engine.export_results()
        assert results["manifest"]["domain_pack"] is None
        assert results["manifest"]["ticks"] == 1


# ── 6. State update between steps → reflected in results ─────────────


class TestSimulatorStateUpdate:
    """State mutation between steps."""

    def test_state_change_reflected_in_results(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)

        # First step: valid state (all variables provided)
        engine.set_state({
            "temperature": 50.0,
            "pressure": 10.0,
            "operating_mode": 0.0,
            "vibration_freq": 100.0,
            "output_quality": 90.0,
        })
        step1 = _run(engine.step())
        assert step1.passed is True

        # Second step: violate safety constraint
        engine.set_state({
            "temperature": 200.0,
            "pressure": 10.0,
            "operating_mode": 0.0,
            "vibration_freq": 100.0,
            "output_quality": 90.0,
        })
        step2 = _run(engine.step())
        assert step2.passed is False
        assert step2.safety_fallback is True

    def test_state_change_reflected_in_history(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)

        full_valid = {
            "temperature": 50.0,
            "pressure": 10.0,
            "operating_mode": 0.0,
            "vibration_freq": 100.0,
            "output_quality": 90.0,
        }
        engine.set_state(full_valid)
        _run(engine.step())

        engine.set_state({**full_valid, "temperature": 200.0})
        _run(engine.step())

        history = engine.get_history()
        assert history[0]["state"]["temperature"] == 50.0
        assert history[1]["state"]["temperature"] == 200.0
        assert history[0]["passed"] is True
        assert history[1]["passed"] is False

    def test_state_change_reflected_in_export(self):
        dp = parse_domainpack(EXAMPLE_DP)
        engine = SimulationEngine(dp)

        engine.set_state({"temperature": 50.0, "pressure": 10.0})
        _run(engine.step())

        engine.set_state({"temperature": 100.0, "pressure": 20.0})
        _run(engine.step())

        results = engine.export_results()
        assert results["history"][0]["state"]["temperature"] == 50.0
        assert results["history"][1]["state"]["temperature"] == 100.0
