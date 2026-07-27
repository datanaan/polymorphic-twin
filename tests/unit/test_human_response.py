"""Tests for the HumanResponseHandler.

Key tests:
1. Valid action in immediate -> accepted
2. Action not in space -> rejected
3. Permanently forbidden exception_request -> review only, NOT override
4. Role without permission -> rejected (no role specified)
5. Forbidden action not directly actionable
"""
import pytest

from polytwin.bridge.human_response import HumanResponseHandler
from polytwin.bridge.types import (
    ActionItem,
    ActionSpace,
    BridgeOutput,
    ConditionalAction,
    ExceptionRequest,
    ExceptionRequestResult,
    ForbiddenAction,
)


@pytest.fixture
def handler():
    return HumanResponseHandler()


def _make_output_with_actions(
    immediate=None,
    conditional=None,
    forbidden=None,
) -> BridgeOutput:
    return BridgeOutput(
        output_id="out-1",
        object_id="obj-1",
        action_space=ActionSpace(
            immediate_actions=immediate or [],
            conditional_actions=conditional or [],
            forbidden_actions=forbidden or [],
        ),
        version_tag="v:abc:1.0",
    )


class TestValidateResponse:
    @pytest.mark.asyncio
    async def test_valid_immediate_action_accepted(self, handler):
        output = _make_output_with_actions(
            immediate=[ActionItem(action_id="a1", action_type="observe")],
        )
        response = {"action_id": "a1"}
        result = await handler.validate_response(response, output, role="operator")
        assert result["valid"] is True
        assert result["action_id"] == "a1"

    @pytest.mark.asyncio
    async def test_valid_conditional_action_accepted(self, handler):
        output = _make_output_with_actions(
            conditional=[ConditionalAction(action_id="c1", action_type="adjust")],
        )
        response = {"action_id": "c1"}
        result = await handler.validate_response(response, output, role="operator")
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_action_not_in_space_rejected(self, handler):
        output = _make_output_with_actions(
            immediate=[ActionItem(action_id="a1")],
        )
        response = {"action_id": "nonexistent"}
        result = await handler.validate_response(response, output, role="operator")
        assert result["valid"] is False
        assert "not in current action space" in result["reason"]

    @pytest.mark.asyncio
    async def test_forbidden_action_not_actionable(self, handler):
        """Forbidden actions are NOT in the actionable set."""
        output = _make_output_with_actions(
            forbidden=[ForbiddenAction(action_id="f1", action_type="shutdown")],
        )
        response = {"action_id": "f1"}
        result = await handler.validate_response(response, output, role="operator")
        assert result["valid"] is False
        assert "not in current action space" in result["reason"]

    @pytest.mark.asyncio
    async def test_no_role_rejected(self, handler):
        output = _make_output_with_actions(
            immediate=[ActionItem(action_id="a1")],
        )
        response = {"action_id": "a1"}
        result = await handler.validate_response(response, output, role="")
        assert result["valid"] is False
        assert "No role specified" in result["reason"]

    @pytest.mark.asyncio
    async def test_empty_action_id_rejected(self, handler):
        output = _make_output_with_actions(
            immediate=[ActionItem(action_id="a1")],
        )
        response = {"action_id": ""}
        result = await handler.validate_response(response, output, role="operator")
        assert result["valid"] is False


class TestExceptionRequest:
    @pytest.mark.asyncio
    async def test_permanently_forbidden_only_review(self, handler):
        """M4-C3: permanently forbidden -> review ONLY, never override."""
        output = _make_output_with_actions(
            forbidden=[
                ForbiddenAction(
                    action_id="f1",
                    action_type="emergency-shutdown",
                    permanently_forbidden=True,
                ),
            ],
        )
        request = ExceptionRequest(
            request_id="req-1",
            action_type="emergency-shutdown",
            requester_role="admin",
            justification="System needs restart",
            target_constraint="safety-interlock",
        )
        result = await handler.handle_exception_request(request, output)
        assert isinstance(result, ExceptionRequestResult)
        assert result.approved is False
        assert result.review_initiated is True
        assert "Permanently forbidden" in result.message

    @pytest.mark.asyncio
    async def test_non_permanent_forbidden_also_review(self, handler):
        """Non-permanent forbidden: still not approved, review initiated."""
        output = _make_output_with_actions(
            forbidden=[
                ForbiddenAction(
                    action_id="f2",
                    action_type="override-temp",
                    permanently_forbidden=False,
                ),
            ],
        )
        request = ExceptionRequest(
            request_id="req-2",
            action_type="override-temp",
            requester_role="operator",
            justification="Temporary override needed",
        )
        result = await handler.handle_exception_request(request, output)
        assert result.approved is False
        assert result.review_initiated is True
        assert "review" in result.message.lower()

    @pytest.mark.asyncio
    async def test_exception_for_non_forbidden_action(self, handler):
        """Exception request for an action not in forbidden list."""
        output = _make_output_with_actions()
        request = ExceptionRequest(
            request_id="req-3",
            action_type="unknown-action",
            requester_role="admin",
        )
        result = await handler.handle_exception_request(request, output)
        assert result.approved is False
        assert result.review_initiated is True

    @pytest.mark.asyncio
    async def test_exception_never_approved_automatically(self, handler):
        """Exception requests are NEVER automatically approved."""
        output = _make_output_with_actions(
            forbidden=[
                ForbiddenAction(
                    action_id="f1",
                    action_type="any-action",
                    permanently_forbidden=False,
                ),
            ],
        )
        request = ExceptionRequest(
            request_id="req-4",
            action_type="any-action",
            requester_role="admin",
            justification="Good reason",
        )
        result = await handler.handle_exception_request(request, output)
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_exception_request_result_has_request_id(self, handler):
        output = _make_output_with_actions()
        request = ExceptionRequest(request_id="req-5", action_type="test")
        result = await handler.handle_exception_request(request, output)
        assert result.request_id == "req-5"
