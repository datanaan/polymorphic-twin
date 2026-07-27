"""Tests for HardGate: six-check link qualification gate.

Test cases:
1. State semantic compatibility: missing variable -> denied
2. State semantic compatibility: all present -> granted
3. Constraint domain match: mode not in domain -> degraded
4. Constraint domain match: mode in domain -> granted
5. Observation readiness: sensor offline -> denied
6. Observation readiness: all active -> granted
7. Task type permission: autonomous_control without cert -> denied
8. Task type permission: with cert -> granted
9. Safety boundary: uncertainty exceeds -> degraded
10. Safety boundary: within bounds -> granted
11. Intervention effectiveness: no path for production_control -> degraded
12. Intervention effectiveness: path exists -> granted
13. Full evaluation: all pass -> all granted
14. Full evaluation: mix of results -> proper classification
"""
import pytest

from polytwin.core.hardgate import HardGate


def _make_domain_pack(
    variables: list[dict] | None = None,
    safety_bounds: dict | None = None,
) -> dict:
    """Build a minimal DomainPack dict for testing."""
    if variables is None:
        variables = [
            {"name": "temperature", "required": True},
            {"name": "pressure", "required": True},
        ]
    return {
        "domain_id": "test-domain",
        "state_semantics_template": {"variables": variables},
        "safe_fallback": {"unavailable_action": "safe_shutdown"},
        "safety_bounds": safety_bounds or {},
    }


def _make_obj_view(
    current_values: dict | None = None,
    sensor_status: dict | None = None,
    task_type: str = "",
    certificates: list[str] | None = None,
    uncertainty: dict | None = None,
    intervention_paths: dict | None = None,
) -> dict:
    """Build a minimal TwinObject view dict for testing."""
    if current_values is None:
        current_values = {"temperature": 100.0, "pressure": 200.0}
    return {
        "state_semantics": {"current_values": current_values},
        "sensor_status": sensor_status or {},
        "task_type": task_type,
        "certificates": certificates or [],
        "uncertainty": uncertainty or {},
        "intervention_paths": intervention_paths or {},
    }


# ── Check 1: State semantic compatibility ─────────────────────────────


class TestStateSemanticCompatibility:
    @pytest.mark.asyncio
    async def test_missing_required_variable_denied(self):
        """Variable missing -> denied."""
        gate = HardGate()
        dp = _make_domain_pack(variables=[
            {"name": "temperature", "required": True},
            {"name": "pressure", "required": True},
            {"name": "flow_rate", "required": True},
        ])
        obj = _make_obj_view(current_values={"temperature": 100.0, "pressure": 200.0})
        result = await gate.evaluate(obj, [], dp)
        assert "state_semantic_compatibility" in result.denied_links

    @pytest.mark.asyncio
    async def test_all_required_present_granted(self):
        """All required variables present -> granted."""
        gate = HardGate()
        dp = _make_domain_pack()
        obj = _make_obj_view()
        result = await gate.evaluate(obj, [], dp)
        assert "state_semantic_compatibility" in result.granted_links


# ── Check 2: Constraint domain match ─────────────────────────────────


class TestConstraintDomainMatch:
    @pytest.mark.asyncio
    async def test_mode_not_in_domain_degraded(self):
        """Mode not in domain_of_validity -> degraded."""
        gate = HardGate()
        constraints = [{
            "constraint_id": "c1",
            "domain_of_validity": {
                "conditions": [
                    {"type": "state_enum", "variable": "mode", "values": ["heating", "cooling"]},
                ],
            },
        }]
        obj = _make_obj_view(current_values={"temperature": 100.0, "pressure": 200.0, "mode": "standby"})
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, constraints, dp)
        assert "constraint_domain_match" in result.degraded_links

    @pytest.mark.asyncio
    async def test_mode_in_domain_granted(self):
        """Mode in domain_of_validity -> granted."""
        gate = HardGate()
        constraints = [{
            "constraint_id": "c1",
            "domain_of_validity": {
                "conditions": [
                    {"type": "state_enum", "variable": "mode", "values": ["heating", "cooling"]},
                ],
            },
        }]
        obj = _make_obj_view(current_values={"temperature": 100.0, "pressure": 200.0, "mode": "heating"})
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, constraints, dp)
        assert "constraint_domain_match" in result.granted_links

    @pytest.mark.asyncio
    async def test_no_constraints_granted(self):
        """No constraints -> granted (nothing to check)."""
        gate = HardGate()
        obj = _make_obj_view()
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, [], dp)
        assert "constraint_domain_match" in result.granted_links


# ── Check 3: Observation readiness ────────────────────────────────────


class TestObservationReadiness:
    @pytest.mark.asyncio
    async def test_sensor_offline_denied(self):
        """Sensor offline -> denied."""
        gate = HardGate()
        dp = _make_domain_pack(variables=[
            {"name": "temperature", "required": True, "measurement_source": "sensor_t1"},
        ])
        obj = _make_obj_view(sensor_status={"sensor_t1": "offline"})
        result = await gate.evaluate(obj, [], dp)
        assert "observation_readiness" in result.denied_links

    @pytest.mark.asyncio
    async def test_sensor_fault_denied(self):
        """Sensor fault -> denied."""
        gate = HardGate()
        dp = _make_domain_pack(variables=[
            {"name": "temperature", "required": True, "measurement_source": "sensor_t1"},
        ])
        obj = _make_obj_view(sensor_status={"sensor_t1": "fault"})
        result = await gate.evaluate(obj, [], dp)
        assert "observation_readiness" in result.denied_links

    @pytest.mark.asyncio
    async def test_all_sensors_active_granted(self):
        """All sensors active -> granted."""
        gate = HardGate()
        dp = _make_domain_pack(variables=[
            {"name": "temperature", "required": True, "measurement_source": "sensor_t1"},
        ])
        obj = _make_obj_view(sensor_status={"sensor_t1": "active"})
        result = await gate.evaluate(obj, [], dp)
        assert "observation_readiness" in result.granted_links


# ── Check 4: Task type permission ─────────────────────────────────────


class TestTaskTypePermission:
    @pytest.mark.asyncio
    async def test_autonomous_control_without_cert_denied(self):
        """autonomous_control without cert -> denied."""
        gate = HardGate()
        obj = _make_obj_view(task_type="autonomous_control", certificates=[])
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, [], dp)
        assert "task_type_permission" in result.denied_links

    @pytest.mark.asyncio
    async def test_autonomous_control_with_cert_granted(self):
        """autonomous_control with cert -> granted."""
        gate = HardGate()
        obj = _make_obj_view(
            task_type="autonomous_control",
            certificates=["autonomous_control_cert"],
        )
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, [], dp)
        assert "task_type_permission" in result.granted_links

    @pytest.mark.asyncio
    async def test_normal_task_type_granted(self):
        """Regular task type -> granted."""
        gate = HardGate()
        obj = _make_obj_view(task_type="monitoring")
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, [], dp)
        assert "task_type_permission" in result.granted_links


# ── Check 5: Safety boundary ──────────────────────────────────────────


class TestSafetyBoundary:
    @pytest.mark.asyncio
    async def test_uncertainty_exceeds_bounds_degraded(self):
        """Uncertainty propagation exceeds -> degraded."""
        gate = HardGate()
        dp = _make_domain_pack(safety_bounds={"temperature": 5.0})
        obj = _make_obj_view(uncertainty={"temperature": 10.0})
        result = await gate.evaluate(obj, [], dp)
        assert "safety_boundary" in result.degraded_links

    @pytest.mark.asyncio
    async def test_uncertainty_within_bounds_granted(self):
        """Uncertainty within bounds -> granted."""
        gate = HardGate()
        dp = _make_domain_pack(safety_bounds={"temperature": 5.0})
        obj = _make_obj_view(uncertainty={"temperature": 3.0})
        result = await gate.evaluate(obj, [], dp)
        assert "safety_boundary" in result.granted_links

    @pytest.mark.asyncio
    async def test_no_uncertainty_data_granted(self):
        """No uncertainty data -> granted."""
        gate = HardGate()
        dp = _make_domain_pack()
        obj = _make_obj_view()
        result = await gate.evaluate(obj, [], dp)
        assert "safety_boundary" in result.granted_links


# ── Check 6: Intervention effectiveness ───────────────────────────────


class TestInterventionEffectiveness:
    @pytest.mark.asyncio
    async def test_production_control_no_path_degraded(self):
        """production_control without path -> degraded."""
        gate = HardGate()
        obj = _make_obj_view(
            task_type="production_control",
            intervention_paths={},
        )
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, [], dp)
        assert "intervention_effectiveness" in result.degraded_links

    @pytest.mark.asyncio
    async def test_production_control_with_path_granted(self):
        """production_control with path -> granted."""
        gate = HardGate()
        obj = _make_obj_view(
            task_type="production_control",
            intervention_paths={"production_control": "manual_override"},
        )
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, [], dp)
        assert "intervention_effectiveness" in result.granted_links

    @pytest.mark.asyncio
    async def test_non_production_task_granted(self):
        """Non-production task -> granted."""
        gate = HardGate()
        obj = _make_obj_view(task_type="monitoring")
        dp = _make_domain_pack()
        result = await gate.evaluate(obj, [], dp)
        assert "intervention_effectiveness" in result.granted_links


# ── Full evaluation ──────────────────────────────────────────────────


class TestHardGateFullEvaluation:
    @pytest.mark.asyncio
    async def test_all_checks_pass(self):
        """All 6 checks pass -> all in granted, none in degraded/denied."""
        gate = HardGate()
        dp = _make_domain_pack()
        obj = _make_obj_view()
        result = await gate.evaluate(obj, [], dp)
        assert len(result.granted_links) == 6
        assert len(result.degraded_links) == 0
        assert len(result.denied_links) == 0

    @pytest.mark.asyncio
    async def test_mixed_results(self):
        """Mix of passed/degraded/denied across checks."""
        gate = HardGate()
        dp = _make_domain_pack(
            variables=[
                {"name": "temperature", "required": True},
                {"name": "flow_rate", "required": True},
            ],
            safety_bounds={"temperature": 5.0},
        )
        obj = _make_obj_view(
            current_values={"temperature": 100.0},
            task_type="autonomous_control",
            certificates=[],
            uncertainty={"temperature": 10.0},
        )
        result = await gate.evaluate(obj, [], dp)
        # state_semantic_compatibility: missing flow_rate -> denied
        assert "state_semantic_compatibility" in result.denied_links
        # task_type_permission: no cert -> denied
        assert "task_type_permission" in result.denied_links
        # safety_boundary: exceeds -> degraded
        assert "safety_boundary" in result.degraded_links


# ── Isolation: must not import certification ─────────────────────────


class TestHardGateIsolation:
    def test_no_certification_import(self):
        """hardgate.py MUST NOT import certification.py."""
        import ast
        import importlib

        mod = importlib.import_module("polytwin.core.hardgate")
        source = mod.__loader__.get_source(mod.__name__)  # type: ignore[union-attr]
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    assert "certification" not in alias.name
