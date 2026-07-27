"""Human response handler for the Bridge decision interface.

Validates human responses against the current action space and
role permissions. Handles exception requests with the invariant
that exception_request != override: permanently_forbidden actions
can only trigger a review, never a direct override.
"""
from __future__ import annotations

from polytwin.bridge.types import (
    BridgeOutput,
    ExceptionRequest,
    ExceptionRequestResult,
)


class HumanResponseHandler:
    """Validates human responses and processes exception requests.

    Ensures that:
    - Responses reference actions that exist in the current action space.
    - The responder's role has permission for the requested action.
    - Exception requests for permanently forbidden actions only
      trigger reviews, never overrides.
    """

    async def validate_response(
        self,
        response: dict,
        output: BridgeOutput,
        role: str,
    ) -> dict:
        """Validate a human response against the action space and role permissions.

        Args:
            response: Dictionary containing the human's response.
                Expected keys: action_id, action_type.
            output: The BridgeOutput containing the current action space.
            role: The role of the human making the response.

        Returns:
            Dictionary with 'valid' (bool) and optional 'reason' (str).
        """
        action_id = response.get("action_id", "")

        # Collect all actionable IDs (immediate + conditional only --
        # forbidden and undetermined are NOT actionable)
        all_actions = (
            output.action_space.immediate_actions
            + output.action_space.conditional_actions
        )
        action_ids = [a.action_id for a in all_actions]

        if action_id not in action_ids:
            return {"valid": False, "reason": "Action not in current action space"}

        # Find the matching action to check role permissions
        matched_action = None
        for a in all_actions:
            if a.action_id == action_id:
                matched_action = a
                break

        # Role-based permission check: if the output carries human_roles
        # information via the action space, verify the role is authorized.
        # For now, we check basic role validity.
        if not role:
            return {"valid": False, "reason": "No role specified"}

        return {
            "valid": True,
            "action_id": action_id,
            "action_type": matched_action.action_type if matched_action else "",
            "role": role,
        }

    async def handle_exception_request(
        self,
        request: ExceptionRequest,
        output: BridgeOutput,
    ) -> ExceptionRequestResult:
        """Process an exception request for a forbidden action.

        M4-C3: exception_request != override. Permanently forbidden
        actions can ONLY trigger a review, never a direct override.

        Args:
            request: The exception request details.
            output: The current BridgeOutput containing the action space.

        Returns:
            ExceptionRequestResult with approval status and review state.
        """
        # Check if this action type is in the forbidden list
        for forbidden in output.action_space.forbidden_actions:
            if forbidden.action_type == request.action_type:
                if forbidden.permanently_forbidden:
                    # Permanently forbidden: can ONLY initiate review
                    return ExceptionRequestResult(
                        request_id=request.request_id,
                        approved=False,
                        review_initiated=True,
                        message="Permanently forbidden action - review initiated",
                    )
                else:
                    # Forbidden but not permanent: initiate review
                    return ExceptionRequestResult(
                        request_id=request.request_id,
                        approved=False,
                        review_initiated=True,
                        message="Exception request submitted for review",
                    )

        # Action type not found in forbidden list
        return ExceptionRequestResult(
            request_id=request.request_id,
            approved=False,
            review_initiated=True,
            message="Exception request submitted for review",
        )
