"""Multi-scene DomainPack switching tests (M6).

Verifies that loading different DomainPacks and switching between them
works correctly through the Core/Lab/Bridge pipeline without requiring
any code changes.

Validates:
1. Each DomainPack loads and passes validation
2. Core validates state using each DomainPack's constraints
3. Lab explores hypotheses with each DomainPack's data
4. Bridge generates action spaces for each DomainPack
5. Switching DomainPacks mid-session works cleanly
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


# ── DomainPack payloads (minimal inline versions for API testing) ──────


def _make_domain_pack(domain_id: str, variables: list[str], constraints: list[dict]) -> dict:
    """Build a minimal DomainPack dict for Core validation."""
    return {
        "domain_id": domain_id,
        "domain_version": "0.1.0",
        "state_semantics_template": {
            "variables": [
                {"name": v, "physical_meaning": v, "unit": "unit", "range_min": 0, "range_max": 100}
                for v in variables
            ],
        },
        "constraint_cards": {"absolute": constraints, "soft": [], "learnable": []},
        "safe_fallback": {"target_state": {"state_description": "safe"}},
        "action_templates": {
            "immediate_action_types": [],
            "conditional_action_types": [],
            "forbidden_action_types": [],
        },
        "human_roles": [],
    }


MINIMAL_DP = _make_domain_pack(
    "example.minimal_device_monitor",
    ["temperature", "pressure"],
    [
        {
            "constraint_id": "cc-temp-limit",
            "scenario_criticality": "safety_critical",
            "validation": {"type": "range", "config": {"variable": "temperature", "min": 0, "max": 100}},
        }
    ],
)

CHEMICAL_DP = _make_domain_pack(
    "cstr.thermal_control",
    ["reactor_temp", "coolant_flow", "reaction_rate", "product_quality", "vessel_pressure"],
    [
        {
            "constraint_id": "temp_upper_limit",
            "scenario_criticality": "safety_critical",
            "validation": {"type": "range", "config": {"variable": "reactor_temp", "min": 0, "max": 350}},
        },
        {
            "constraint_id": "pressure_upper_limit",
            "scenario_criticality": "safety_critical",
            "validation": {"type": "range", "config": {"variable": "vessel_pressure", "min": 0, "max": 15}},
        },
    ],
)

WIND_DP = _make_domain_pack(
    "wind_turbine.bearing_monitor",
    ["vibration_freq", "bearing_temp", "rotor_speed", "power_output", "oil_quality_index"],
    [
        {
            "constraint_id": "vibration_limit",
            "scenario_criticality": "safety_critical",
            "validation": {"type": "range", "config": {"variable": "vibration_freq", "min": 0, "max": 2500}},
        },
    ],
)

KNOWLEDGE_DP = _make_domain_pack(
    "knowledge.personal_mgmt",
    ["knowledge_freshness", "link_density", "coverage_ratio", "contradiction_count", "usage_frequency"],
    [
        {
            "constraint_id": "freshness_limit",
            "scenario_criticality": "operational",
            "validation": {"type": "range", "config": {"variable": "knowledge_freshness", "min": 0, "max": 90}},
        },
    ],
)

ALL_PACKS = [
    ("minimal", MINIMAL_DP),
    ("chemical", CHEMICAL_DP),
    ("wind", WIND_DP),
    ("knowledge", KNOWLEDGE_DP),
]


# ── Tests ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("pack_name,domain_pack", ALL_PACKS, ids=[p[0] for p in ALL_PACKS])
async def test_core_validates_with_each_domainpack(
    api_client: AsyncClient, pack_name: str, domain_pack: dict
) -> None:
    """Core validates state values using each DomainPack's constraints."""
    # Extract first constraint for validation
    first_constraint = domain_pack["constraint_cards"]["absolute"][0]
    var_name = first_constraint["validation"]["config"]["variable"]
    var_max = first_constraint["validation"]["config"]["max"]

    # Valid state
    response = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {var_name: var_max * 0.5},
            "constraint_cards": [first_constraint],
            "domain_pack": domain_pack,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["passed"] is True


@pytest.mark.parametrize("pack_name,domain_pack", ALL_PACKS, ids=[p[0] for p in ALL_PACKS])
async def test_lab_explores_with_each_domainpack(
    api_client: AsyncClient, pack_name: str, domain_pack: dict
) -> None:
    """Lab generates hypotheses for each DomainPack scenario."""
    first_constraint = domain_pack["constraint_cards"]["absolute"][0]
    var_name = first_constraint["validation"]["config"]["variable"]
    var_max = first_constraint["validation"]["config"]["max"]

    response = await api_client.post(
        "/api/v1/lab/explore/hypothesis",
        json={
            "data": {"state_variables": {var_name: var_max * 0.5}},
            "constraints": [first_constraint],
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert "hypotheses" in result


@pytest.mark.parametrize("pack_name,domain_pack", ALL_PACKS, ids=[p[0] for p in ALL_PACKS])
async def test_bridge_generates_action_space_for_each_domainpack(
    api_client: AsyncClient, pack_name: str, domain_pack: dict
) -> None:
    """Bridge generates action spaces for each DomainPack scenario."""
    first_constraint = domain_pack["constraint_cards"]["absolute"][0]

    response = await api_client.post(
        "/api/v1/bridge/action-space",
        json={
            "view_data": {
                "twin_object_id": f"obj-{pack_name}-001",
                "constraint_state": {"active_constraints": [first_constraint["constraint_id"]]},
                "constraint_summary": [],
            },
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert "output_id" in result
    assert "action_space" in result


async def test_switch_domainpack_mid_session(api_client: AsyncClient) -> None:
    """Switch from one DomainPack to another within the same session.

    Verifies that processing with one DomainPack, then immediately
    processing with a different DomainPack produces correct results
    for each -- no state leaks between DomainPacks.
    """
    # Step 1: Validate with minimal DomainPack
    resp1 = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 50.0},
            "constraint_cards": [
                {
                    "constraint_id": "cc-temp-limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "temperature", "min": 0, "max": 100}},
                }
            ],
            "domain_pack": MINIMAL_DP,
        },
    )
    assert resp1.status_code == 200
    assert resp1.json()["passed"] is True

    # Step 2: Switch to chemical reactor DomainPack
    resp2 = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"reactor_temp": 200.0},
            "constraint_cards": [
                {
                    "constraint_id": "temp_upper_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "reactor_temp", "min": 0, "max": 350}},
                }
            ],
            "domain_pack": CHEMICAL_DP,
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["passed"] is True

    # Step 3: Switch to wind turbine DomainPack
    resp3 = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"vibration_freq": 1200.0},
            "constraint_cards": [
                {
                    "constraint_id": "vibration_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "vibration_freq", "min": 0, "max": 2500}},
                }
            ],
            "domain_pack": WIND_DP,
        },
    )
    assert resp3.status_code == 200
    assert resp3.json()["passed"] is True

    # Step 4: Switch to knowledge management DomainPack
    resp4 = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"knowledge_freshness": 30.0},
            "constraint_cards": [
                {
                    "constraint_id": "freshness_limit",
                    "scenario_criticality": "operational",
                    "validation": {"type": "range", "config": {"variable": "knowledge_freshness", "min": 0, "max": 90}},
                }
            ],
            "domain_pack": KNOWLEDGE_DP,
        },
    )
    assert resp4.status_code == 200
    assert resp4.json()["passed"] is True


async def test_switch_back_to_original_domainpack(api_client: AsyncClient) -> None:
    """Switch away and back to the same DomainPack produces consistent results."""
    constraint = {
        "constraint_id": "cc-temp-limit",
        "scenario_criticality": "safety_critical",
        "validation": {"type": "range", "config": {"variable": "temperature", "min": 0, "max": 100}},
    }

    # First validation
    resp1 = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 65.0},
            "constraint_cards": [constraint],
            "domain_pack": MINIMAL_DP,
        },
    )
    assert resp1.status_code == 200
    result1 = resp1.json()

    # Switch to different DomainPack
    await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"reactor_temp": 200.0},
            "constraint_cards": [CHEMICAL_DP["constraint_cards"]["absolute"][0]],
            "domain_pack": CHEMICAL_DP,
        },
    )

    # Switch back -- same input should produce same result
    resp2 = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 65.0},
            "constraint_cards": [constraint],
            "domain_pack": MINIMAL_DP,
        },
    )
    assert resp2.status_code == 200
    result2 = resp2.json()
    assert result2["passed"] == result1["passed"]
