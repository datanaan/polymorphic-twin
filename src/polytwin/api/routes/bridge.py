"""Bridge routes: action space generation, decision validation, human response.

The Bridge presents structured action option spaces to human decision makers
without making suggestions or sending commands to physical actuators.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from polytwin.api.deps import (
    get_facade,
    get_human_response,
    get_orchestrator,
    get_validity,
)
from polytwin.bridge.types import ExceptionRequest
from polytwin.tom.types import CallerIdentity, ViewType

router = APIRouter()


# ── Request models ──────────────────────────────────────────────────


class ActionSpaceRequest(BaseModel):
    """Request body for action space generation."""

    view_data: dict = Field(default_factory=dict)
    domain_pack: dict | None = None
    object_id: str | None = None


class DecideRequest(BaseModel):
    """Request body for decision validation."""

    output_id: str
    action_id: str
    role: str
    current_version: str | None = None


class HumanResponseRequest(BaseModel):
    """Request body for human response handling."""

    output_id: str
    response: dict = Field(default_factory=dict)
    role: str = ""


class ExceptionRequestBody(BaseModel):
    """Request body for exception requests."""

    action_type: str
    requester_role: str = ""
    justification: str = ""
    target_constraint: str = ""
    output_id: str = ""


# ── Routes ──────────────────────────────────────────────────────────


@router.post("/action-space")
async def generate_action_space(body: ActionSpaceRequest) -> dict:
    """Generate a four-category action space from view data.

    The action space categorizes actions as immediate, conditional,
    forbidden, or undetermined based on constraint evaluation results.
    """
    orchestrator = get_orchestrator()
    view_data = body.view_data

    # If object_id provided, fetch BridgeDecisionView from facade
    if body.object_id and not view_data:
        caller = CallerIdentity(component="bridge", role="decision_maker")
        facade = get_facade()
        try:
            view = await facade.get_view(
                body.object_id, ViewType.BRIDGE_DECISION, caller
            )
            view_data = view.model_dump()
        except Exception:
            view_data = {}

    result = await orchestrator.generate_action_space(
        view_data=view_data,
        domain_pack=body.domain_pack,
    )
    return result.model_dump()


@router.post("/decide")
async def decide(body: DecideRequest) -> dict:
    """Validate a human decision against the current action space.

    Checks that the output is still valid and the action is permitted.
    """
    validity = get_validity()
    output = validity.get(body.output_id)

    if output is None:
        raise HTTPException(status_code=404, detail="Output not found or expired")

    if body.current_version and not validity.is_valid(body.output_id, body.current_version):
        return {
            "valid": False,
            "reason": "Output version has changed -- regenerate action space",
        }

    # Verify action exists in the output's action space
    all_actions = (
        output.action_space.immediate_actions
        + output.action_space.conditional_actions
    )
    action_ids = [a.action_id for a in all_actions]

    if body.action_id not in action_ids:
        return {"valid": False, "reason": "Action not in current action space"}

    matched = None
    for a in all_actions:
        if a.action_id == body.action_id:
            matched = a
            break

    return {
        "valid": True,
        "action_id": body.action_id,
        "action_type": matched.action_type if matched else "",
        "role": body.role,
    }


@router.get("/roles")
async def list_roles() -> dict:
    """List the human roles recognised by the Bridge.

    These roles map to permission levels defined in the DomainPack.
    """
    return {
        "roles": [
            {"role_id": "operator", "name": "Operator", "permission_level": "execute"},
            {"role_id": "supervisor", "name": "Supervisor", "permission_level": "approve"},
            {"role_id": "engineer", "name": "Engineer", "permission_level": "configure"},
            {"role_id": "safety_officer", "name": "Safety Officer", "permission_level": "override"},
        ],
    }


@router.post("/human-response")
async def human_response(body: HumanResponseRequest) -> dict:
    """Handle a human response to a presented action space.

    Validates that the response references a valid action and the
    responder's role has permission for the requested action.
    """
    validity = get_validity()
    output = validity.get(body.output_id)

    if output is None:
        raise HTTPException(status_code=404, detail="Output not found or expired")

    handler = get_human_response()
    result = await handler.validate_response(body.response, output, body.role)
    return result


@router.post("/exception-request")
async def exception_request(body: ExceptionRequestBody) -> dict:
    """Process an exception request for a forbidden action.

    M4-C3: exception_request != override. Permanently forbidden
    actions can only trigger a review, never a direct override.
    """
    validity = get_validity()
    output = validity.get(body.output_id)

    if output is None:
        raise HTTPException(status_code=404, detail="Output not found or expired")

    request = ExceptionRequest(
        action_type=body.action_type,
        requester_role=body.requester_role,
        justification=body.justification,
        target_constraint=body.target_constraint,
    )
    handler = get_human_response()
    result = await handler.handle_exception_request(request, output)
    return result.model_dump()
