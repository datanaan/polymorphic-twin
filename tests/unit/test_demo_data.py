"""Tests for CSTR demo data generator and scenario files.

Test cases:
1. CSTRDataGenerator produces correct tick structure
2. TickType enum covers all five types
3. Normal ticks have small fluctuations
4. Drift ticks increase monotonically
5. Spike ticks produce large changes
6. Oscillation ticks produce sinusoidal patterns
7. Failure ticks zero coolant flow
8. generate_sequence produces correct length
9. generate_mixed_sequence interleaves types
10. Reset clears tick count
11. Scenario JSON files are valid
12. DemoRunner loads and runs scenarios
"""
import json
from pathlib import Path

import pytest

from polytwin.demo.data_generator import CSTRDataGenerator, TickType
from polytwin.demo.runner import DemoRunner

SCENARIOS_DIR = Path("configs/examples/scenarios")


# ── Test 1: Tick structure ───────────────────────────────────────────


class TestTickStructure:
    def test_tick_has_required_keys(self):
        gen = CSTRDataGenerator()
        tick = gen.generate_tick()
        assert "tick" in tick
        assert "type" in tick
        assert "state" in tick

    def test_tick_number_increments(self):
        gen = CSTRDataGenerator()
        t1 = gen.generate_tick()
        t2 = gen.generate_tick()
        assert t2["tick"] == t1["tick"] + 1

    def test_state_has_all_variables(self):
        gen = CSTRDataGenerator()
        tick = gen.generate_tick()
        expected_vars = {
            "reactor_temp", "coolant_flow", "feed_rate",
            "concentration_a", "concentration_b", "vessel_pressure",
        }
        assert set(tick["state"].keys()) == expected_vars


# ── Test 2: TickType enum ────────────────────────────────────────────


class TestTickType:
    def test_all_five_types_exist(self):
        types = {t.value for t in TickType}
        assert types == {"normal", "drift", "spike", "oscillation", "failure"}

    def test_tick_type_is_string(self):
        for tt in TickType:
            assert isinstance(tt.value, str)

    def test_type_value_in_tick(self):
        gen = CSTRDataGenerator()
        for tt in TickType:
            gen.reset()
            tick = gen.generate_tick(tt)
            assert tick["type"] == tt.value


# ── Test 3: Normal ticks ─────────────────────────────────────────────


class TestNormalTicks:
    def test_normal_small_fluctuation(self):
        gen = CSTRDataGenerator(config={"seed": 42})
        ticks = gen.generate_sequence(100, TickType.NORMAL)
        # Mean should be close to base state
        temps = [t["state"]["reactor_temp"] for t in ticks]
        assert abs(sum(temps) / len(temps) - 200.0) < 5.0

    def test_normal_does_not_exceed_safety_on_average(self):
        gen = CSTRDataGenerator(config={"seed": 42})
        ticks = gen.generate_sequence(100, TickType.NORMAL)
        # With small fluctuations, should stay well below 350
        assert all(t["state"]["reactor_temp"] < 300 for t in ticks)


# ── Test 4: Drift ticks ─────────────────────────────────────────────


class TestDriftTicks:
    def test_drift_temperature_increases(self):
        gen = CSTRDataGenerator()
        temps = []
        for _ in range(5):
            tick = gen.generate_tick(TickType.DRIFT)
            temps.append(tick["state"]["reactor_temp"])
        # Temperature should be monotonically increasing
        for i in range(1, len(temps)):
            assert temps[i] > temps[i - 1]

    def test_drift_eventually_violates_constraint(self):
        gen = CSTRDataGenerator()
        # After enough drift ticks, temp should exceed 350
        temps = []
        for _ in range(30):
            tick = gen.generate_tick(TickType.DRIFT)
            temps.append(tick["state"]["reactor_temp"])
        assert max(temps) > 350.0


# ── Test 5: Spike ticks ─────────────────────────────────────────────


class TestSpikeTicks:
    def test_spike_produces_large_change(self):
        gen = CSTRDataGenerator(config={"seed": 42})
        base_temp = gen.base_state["reactor_temp"]
        tick = gen.generate_tick(TickType.SPIKE)
        # Spike should be +/- 50 from base
        assert abs(tick["state"]["reactor_temp"] - base_temp) >= 40.0


# ── Test 6: Oscillation ticks ───────────────────────────────────────


class TestOscillationTicks:
    def test_oscillation_is_bounded(self):
        gen = CSTRDataGenerator()
        temps = []
        for _ in range(50):
            tick = gen.generate_tick(TickType.OSCILLATION)
            temps.append(tick["state"]["reactor_temp"])
        # Oscillation amplitude is 10 around 200, so range should be ~190-210
        assert min(temps) >= 180
        assert max(temps) <= 220


# ── Test 7: Failure ticks ───────────────────────────────────────────


class TestFailureTicks:
    def test_failure_zero_coolant(self):
        gen = CSTRDataGenerator()
        tick = gen.generate_tick(TickType.FAILURE)
        assert tick["state"]["coolant_flow"] == 0.0

    def test_failure_temperature_rises(self):
        gen = CSTRDataGenerator()
        base_temp = gen.base_state["reactor_temp"]
        tick = gen.generate_tick(TickType.FAILURE)
        assert tick["state"]["reactor_temp"] > base_temp


# ── Test 8: generate_sequence ────────────────────────────────────────


class TestGenerateSequence:
    def test_correct_length(self):
        gen = CSTRDataGenerator()
        seq = gen.generate_sequence(10)
        assert len(seq) == 10

    def test_sequential_tick_numbers(self):
        gen = CSTRDataGenerator()
        seq = gen.generate_sequence(5)
        assert [t["tick"] for t in seq] == [1, 2, 3, 4, 5]

    def test_sequence_type(self):
        gen = CSTRDataGenerator()
        seq = gen.generate_sequence(3, TickType.FAILURE)
        assert all(t["type"] == "failure" for t in seq)


# ── Test 9: generate_mixed_sequence ──────────────────────────────────


class TestMixedSequence:
    def test_mixed_sequence_length(self):
        gen = CSTRDataGenerator()
        pattern = [(3, TickType.NORMAL), (2, TickType.DRIFT)]
        seq = gen.generate_mixed_sequence(pattern)
        assert len(seq) == 5

    def test_mixed_sequence_types(self):
        gen = CSTRDataGenerator()
        pattern = [(2, TickType.NORMAL), (1, TickType.FAILURE)]
        seq = gen.generate_mixed_sequence(pattern)
        assert seq[0]["type"] == "normal"
        assert seq[1]["type"] == "normal"
        assert seq[2]["type"] == "failure"


# ── Test 10: Reset ───────────────────────────────────────────────────


class TestReset:
    def test_reset_clears_tick_count(self):
        gen = CSTRDataGenerator()
        gen.generate_sequence(5)
        assert gen.tick_count == 5
        gen.reset()
        assert gen.tick_count == 0
        tick = gen.generate_tick()
        assert tick["tick"] == 1


# ── Test 11: Scenario JSON files ─────────────────────────────────────


class TestScenarioFiles:
    @pytest.fixture
    def scenario_files(self):
        return sorted(SCENARIOS_DIR.glob("*.json"))

    def test_six_scenario_files_exist(self, scenario_files):
        assert len(scenario_files) == 6

    def test_scenario_structure(self, scenario_files):
        for path in scenario_files:
            with open(path) as f:
                data = json.load(f)
            assert "name" in data, f"{path.name}: missing 'name'"
            assert "description" in data, f"{path.name}: missing 'description'"
            assert "domain_pack_id" in data, f"{path.name}: missing 'domain_pack_id'"
            assert data["domain_pack_id"] == "demo.cstr"
            assert "ticks" in data, f"{path.name}: missing 'ticks'"
            assert len(data["ticks"]) > 0, f"{path.name}: empty ticks"
            assert "expected_result" in data, f"{path.name}: missing 'expected_result'"

            # Verify each tick structure
            for tick in data["ticks"]:
                assert "tick" in tick
                assert "type" in tick
                assert "state" in tick
                assert isinstance(tick["state"], dict)
                assert "reactor_temp" in tick["state"]

    def test_normal_operation_scenario(self):
        with open(SCENARIOS_DIR / "normal-operation.json") as f:
            data = json.load(f)
        assert data["expected_result"] == "all_pass"
        assert len(data["ticks"]) == 20

    def test_temperature_drift_scenario(self):
        with open(SCENARIOS_DIR / "temperature-drift.json") as f:
            data = json.load(f)
        assert data["expected_result"] == "constraint_violation"
        # Should contain some ticks that exceed 350C
        temps = [t["state"]["reactor_temp"] for t in data["ticks"]]
        assert max(temps) > 350.0

    def test_coolant_failure_scenario(self):
        with open(SCENARIOS_DIR / "coolant-failure.json") as f:
            data = json.load(f)
        assert data["expected_result"] == "safety_fallback"
        # Should contain failure ticks
        types = {t["type"] for t in data["ticks"]}
        assert "failure" in types

    def test_pressure_spike_scenario(self):
        with open(SCENARIOS_DIR / "pressure-spike.json") as f:
            data = json.load(f)
        assert data["expected_result"] == "constraint_violation"

    def test_oscillation_scenario(self):
        with open(SCENARIOS_DIR / "oscillation.json") as f:
            data = json.load(f)
        assert data["expected_result"] == "mixed"

    def test_mixed_scenario(self):
        with open(SCENARIOS_DIR / "mixed-scenarios.json") as f:
            data = json.load(f)
        assert data["expected_result"] == "mixed"
        types = {t["type"] for t in data["ticks"]}
        assert len(types) >= 3  # Should have multiple tick types


# ── Test 12: DemoRunner integration ──────────────────────────────────


class TestDemoRunner:
    @pytest.fixture
    def runner(self):
        from polytwin.config import EngineConfig
        from polytwin.engine import PolymorphicTwinEngine
        config = EngineConfig(domain_pack_dirs=["configs/examples"])
        engine = PolymorphicTwinEngine(config)
        return DemoRunner(engine)

    @pytest.mark.asyncio
    async def test_run_normal_scenario(self, runner):
        result = await runner.run_scenario(
            SCENARIOS_DIR / "normal-operation.json"
        )
        assert result["scenario"] == "Normal Operation"
        assert result["ticks"] == 20
        assert "results" in result
        assert "summary" in result
        assert result["summary"]["total_ticks"] == 20
        # Normal operation should mostly pass
        assert result["summary"]["pass_rate"] > 0.8

    @pytest.mark.asyncio
    async def test_run_drift_scenario(self, runner):
        result = await runner.run_scenario(
            SCENARIOS_DIR / "temperature-drift.json"
        )
        assert result["summary"]["failed"] > 0

    @pytest.mark.asyncio
    async def test_run_coolant_failure(self, runner):
        result = await runner.run_scenario(
            SCENARIOS_DIR / "coolant-failure.json"
        )
        assert result["summary"]["safety_fallbacks"] > 0

    @pytest.mark.asyncio
    async def test_format_result(self, runner):
        result = await runner.run_scenario(
            SCENARIOS_DIR / "normal-operation.json"
        )
        formatted = DemoRunner.format_result(result)
        assert "Normal Operation" in formatted
        assert "Ticks: 20" in formatted

    @pytest.mark.asyncio
    async def test_run_all_scenarios(self, runner):
        results = await runner.run_all_scenarios(SCENARIOS_DIR)
        assert len(results) == 6

    @pytest.mark.asyncio
    async def test_invalid_domain_pack(self, runner):
        """Runner raises ValueError for unknown DomainPack."""
        import os
        import tempfile
        bad_scenario = {
            "name": "Bad",
            "description": "Test",
            "domain_pack_id": "nonexistent.pack",
            "ticks": [{"tick": 1, "type": "normal", "state": {"reactor_temp": 200}}],
            "expected_result": "error",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(bad_scenario, f)
            tmp = f.name
        try:
            with pytest.raises(ValueError, match="not loaded"):
                await runner.run_scenario(tmp)
        finally:
            os.unlink(tmp)


# ── Test: Config overrides ───────────────────────────────────────────


class TestConfigOverrides:
    def test_custom_base_state(self):
        gen = CSTRDataGenerator(config={
            "base_state": {"reactor_temp": 300.0, "coolant_flow": 60.0,
                           "feed_rate": 15.0, "concentration_a": 5.0,
                           "concentration_b": 3.0, "vessel_pressure": 8.0}
        })
        tick = gen.generate_tick(TickType.NORMAL)
        # With small noise, should be near 300
        assert abs(tick["state"]["reactor_temp"] - 300.0) < 10

    def test_seed_reproducibility(self):
        gen1 = CSTRDataGenerator(config={"seed": 123})
        gen2 = CSTRDataGenerator(config={"seed": 123})
        seq1 = gen1.generate_sequence(5, TickType.NORMAL)
        seq2 = gen2.generate_sequence(5, TickType.NORMAL)
        for t1, t2 in zip(seq1, seq2, strict=False):
            assert t1["state"]["reactor_temp"] == t2["state"]["reactor_temp"]
