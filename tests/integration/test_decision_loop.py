"""Decision loop integration tests (Section 2.3).

Tests the flow: Lab submits -> Quarantine -> Evidence admission ->
Bridge action space.

Validates:
1. Full chain from Lab submission to Bridge action space
2. Full chain traceable via audit
3. Invalid items rejected independently (M2-C4)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_full_decision_chain(api_client: AsyncClient) -> None:
    """Lab submits -> Quarantine -> Evidence admission -> Bridge action space.

    The complete decision loop traces from Lab exploration through Core
    qualification to Bridge action space generation.
    """
    # Step 1: Lab submits candidates
    candidates = [
        {
            "model_id": "model-001",
            "architecture_description": "Bearing temperature predictor",
            "training_data_lineage": "lineage-bearings-v1",
        }
    ]
    submit_resp = await api_client.post(
        "/api/v1/lab/submit",
        json={"candidates": candidates},
    )
    assert submit_resp.status_code == 200
    submit_data = submit_resp.json()
    assert "submission_id" in submit_data
    assert submit_data["hidden_set_info_exposed"] is False

    # Step 2: Core runs constraint validation
    validate_resp = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 65.3},
            "constraint_cards": [
                {
                    "constraint_id": "cc-temp-limit",
                    "scenario_criticality": "operational",
                    "rigidity": "absolute",
                    "validation": {
                        "type": "range",
                        "config": {"variable": "temperature", "min": 0, "max": 100},
                    },
                }
            ],
        },
    )
    assert validate_resp.status_code == 200
    validation = validate_resp.json()
    assert "passed" in validation

    # Step 3: Evidence admission
    evidence_resp = await api_client.post(
        "/api/v1/core/evidence/admit",
        json={
            "items": [{"item_id": "ev-001", "data": "test evidence"}],
            "validation_results": {"ev-001": {"passed": True, "source": "public_set"}},
        },
    )
    assert evidence_resp.status_code == 200
    evidence_data = evidence_resp.json()
    assert "feedback" in evidence_data
    assert "items" in evidence_data

    # Step 4: Bridge generates action space
    action_resp = await api_client.post(
        "/api/v1/bridge/action-space",
        json={
            "view_data": {
                "twin_object_id": "obj-001",
                "constraint_state": {"active_constraints": ["cc-temp-limit"]},
                "constraint_summary": [],
            },
        },
    )
    assert action_resp.status_code == 200
    action_data = action_resp.json()
    assert "output_id" in action_data
    assert "action_space" in action_data


async def test_audit_trail_traces_full_chain(api_client: AsyncClient) -> None:
    """Full chain is traceable via audit log."""
    # Run a validation to generate audit events
    await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 65.3},
            "constraint_cards": [
                {
                    "constraint_id": "cc-temp-audit",
                    "scenario_criticality": "operational",
                    "rigidity": "absolute",
                    "validation": {
                        "type": "range",
                        "config": {"variable": "temperature", "min": 0, "max": 100},
                    },
                }
            ],
        },
    )

    # Query audit trail
    audit_resp = await api_client.get("/api/v1/core/audit")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert audit_data["count"] >= 1
    events = audit_data["events"]
    # Should have at least one constraint_validation event
    event_types = [e["event_type"] for e in events]
    assert "constraint_validation" in event_types


async def test_evidence_items_rejected_independently(
    api_client: AsyncClient,
) -> None:
    """M2-C4: Each evidence item is judged independently.

    One item's rejection does not affect another item's outcome.
    """
    items = [
        {"item_id": "ev-good", "data": "valid evidence"},
        {"item_id": "ev-bad", "audit_benchmark_reference": "leaked"},
        {"item_id": "ev-also-good", "data": "another valid piece"},
    ]
    validation_results = {
        "ev-good": {"passed": True, "source": "public_set"},
        "ev-bad": {"passed": True, "source": "public_set"},
        "ev-also-good": {"passed": True, "source": "public_set"},
    }

    response = await api_client.post(
        "/api/v1/core/evidence/admit",
        json={"items": items, "validation_results": validation_results},
    )
    assert response.status_code == 200
    result = response.json()

    # ev-good and ev-also-good should be admitted
    # ev-bad should be rejected (contains hidden reference)
    admitted_ids = [i["item_id"] for i in result["items"] if i["admitted"]]
    rejected_ids = [i["item_id"] for i in result["items"] if not i["admitted"]]

    assert "ev-good" in admitted_ids
    assert "ev-also-good" in admitted_ids
    assert "ev-bad" in rejected_ids

    # Independence: ev-good and ev-also-good both admitted despite ev-bad rejection
    assert len(admitted_ids) == 2
    assert len(rejected_ids) == 1


async def test_quarantine_rejects_non_lab_caller(api_client: AsyncClient) -> None:
    """Quarantine rejects submissions from non-Lab callers."""
    response = await api_client.post(
        "/api/v1/core/quarantine/submit",
        json={
            "submission": {
                "hypothesis_id": "hyp-001",
                "lineage": "lineage-001",
                "domain_id": "test-domain",
            },
            "caller_component": "bridge",
            "caller_role": "decision_maker",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["rejected"] is True
    assert "caller_not_authorized" in result["reason"]


async def test_quarantine_rejects_sensitive_info(api_client: AsyncClient) -> None:
    """Quarantine rejects submissions containing sensitive information."""
    response = await api_client.post(
        "/api/v1/core/quarantine/submit",
        json={
            "submission": {
                "hypothesis_id": "hyp-001",
                "lineage": "lineage-001",
                "domain_id": "test-domain",
                "payload": "data with hidden_challenge_set reference",
            },
            "caller_component": "lab",
            "caller_role": "explorer",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["rejected"] is True
    assert "sensitive_info" in result["reason"]


async def test_model_certification_flow(api_client: AsyncClient) -> None:
    """Model certification issues and verifies certificates."""
    # Certify a model
    certify_resp = await api_client.post(
        "/api/v1/core/certify",
        json={"model_id": "model-cert-001", "score": 0.95},
    )
    assert certify_resp.status_code == 200
    cert_data = certify_resp.json()
    assert cert_data["granted"] is True
    assert cert_data["certificate"]["model_id"] == "model-cert-001"

    # Score below threshold should be denied
    deny_resp = await api_client.post(
        "/api/v1/core/certify",
        json={"model_id": "model-cert-002", "score": 0.5},
    )
    assert deny_resp.status_code == 200
    deny_data = deny_resp.json()
    assert deny_data["granted"] is False
