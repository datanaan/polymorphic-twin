"""Integration test fixtures for the Polymorphic-Twin API.

Provides an async HTTP client wired to the FastAPI application using
httpx.AsyncClient with ASGITransport (no real HTTP server needed).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from polytwin.api.app import create_app
from polytwin.api.deps import _reset


@pytest_asyncio.fixture(autouse=True)
async def reset_singletons():
    """Reset all dependency singletons between tests for isolation."""
    _reset()
    yield
    _reset()


@pytest_asyncio.fixture
async def api_client():
    """Async HTTP client for integration testing."""
    app = create_app(test_mode=True)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# ── Shared data fixtures for integration tests ──────────────────────


@pytest.fixture
def minimal_twin_data() -> dict:
    """Minimal valid TwinObject creation payload."""
    return {
        "identity": {
            "type": "device",
            "name": "pump-001",
            "tags": ["rotating", "oil-rig"],
        },
        "lineage": {
            "creator_id": "creator-001",
            "parent_id": None,
            "provenance": [],
        },
    }


@pytest.fixture
def full_twin_data() -> dict:
    """Full TwinObject with state, constraints, and identity invariants."""
    return {
        "identity": {
            "type": "device",
            "name": "pump-001",
            "tags": ["rotating"],
        },
        "lineage": {
            "creator_id": "creator-001",
            "parent_id": None,
            "provenance": [],
        },
        "state": {"lifecycle": "active", "health": "healthy"},
        "state_semantics": {
            "variables": {
                "temperature": {
                    "name": "temperature",
                    "physical_meaning": "Bearing temperature",
                    "unit": "degC",
                    "range_min": -40.0,
                    "range_max": 120.0,
                },
            },
            "current_values": {"temperature": 65.3},
        },
        "constraint_state": {
            "active_constraints": ["cc-temp-limit"],
            "suspended_constraints": [],
            "last_evaluation": [
                {
                    "constraint_id": "cc-temp-limit",
                    "status": "passed",
                    "actual_values": {"temperature": 65.3},
                    "message": "Temperature within safe range",
                }
            ],
        },
        "identity_invariants": {
            "invariants": [
                {
                    "name": "serial_number",
                    "expected_value": "SN-12345",
                    "actual_value": "SN-12345",
                    "confidence": 1.0,
                }
            ],
            "overall_confidence": 1.0,
            "identity_status": "confirmed",
        },
        "action_state": {
            "current_safe_action_set": ["action-shutdown"],
            "fallback_available": True,
        },
        "safe_fallback": {
            "strategy": "safe_state",
            "target_state": {"temperature": 25.0},
        },
        "action_templates": [
            {
                "template_id": "tmpl-shutdown",
                "name": "Shutdown pump",
                "description": "Safely shut down the pump",
                "required_role": "operator",
            }
        ],
        "human_roles": [
            {
                "role_id": "operator",
                "name": "Operator",
                "permission_level": "execute",
            }
        ],
    }


@pytest.fixture
def safety_critical_constraint() -> dict:
    """A safety_critical constraint card for testing."""
    return {
        "constraint_id": "cc-temp-safety",
        "scenario_criticality": "safety_critical",
        "rigidity": "absolute",
        "validation": {
            "type": "range",
            "config": {
                "variable": "temperature",
                "min": 0,
                "max": 100,
            },
        },
    }


@pytest.fixture
def operational_constraint() -> dict:
    """An operational constraint card for testing."""
    return {
        "constraint_id": "cc-temp-operational",
        "scenario_criticality": "operational",
        "rigidity": "absolute",
        "validation": {
            "type": "range",
            "config": {
                "variable": "temperature",
                "min": 10,
                "max": 90,
            },
        },
    }
