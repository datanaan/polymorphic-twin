"""Tests for Bridge types: data models and invariants.

Key tests:
1. All types instantiate with correct defaults
2. ActionItem defaults: manual execution, low risk, prerequisites met
3. ForbiddenAction can be permanently forbidden
4. ActionSpace starts with empty lists for all four categories
5. BridgeOutput has all required fields with empty defaults
6. ExceptionRequestResult defaults: not approved, no review initiated
"""

from polytwin.bridge.types import (
    ActionItem,
    ActionSpace,
    BridgeOutput,
    ConditionalAction,
    ExceptionRequest,
    ExceptionRequestResult,
    ForbiddenAction,
    UndeterminedAction,
)


class TestDefaultInstantiation:
    def test_action_item_defaults(self):
        item = ActionItem()
        assert item.action_id == ""
        assert item.action_type == ""
        assert item.description == ""
        assert item.execution_mode == "manual"
        assert item.risk_level == "low"
        assert item.prerequisites_met is True
        assert item.lawful_unlock_path == []

    def test_conditional_action_defaults(self):
        ca = ConditionalAction()
        assert ca.unmet_prerequisites == []
        assert ca.conditions_to_unlock == []

    def test_forbidden_action_defaults(self):
        fa = ForbiddenAction()
        assert fa.action_id == ""
        assert fa.prohibition_reason == ""
        assert fa.lawful_unlock_conditions == []
        assert fa.permanently_forbidden is False

    def test_undetermined_action_defaults(self):
        ua = UndeterminedAction()
        assert ua.missing_information == []
        assert ua.required_data_sources == []

    def test_action_space_defaults(self):
        space = ActionSpace()
        assert space.immediate_actions == []
        assert space.conditional_actions == []
        assert space.forbidden_actions == []
        assert space.undetermined_actions == []

    def test_bridge_output_defaults(self):
        out = BridgeOutput()
        assert out.output_id == ""
        assert out.object_id == ""
        assert isinstance(out.action_space, ActionSpace)
        assert out.valid_until == ""
        assert out.version_tag == ""
        assert out.created_at == ""

    def test_exception_request_defaults(self):
        er = ExceptionRequest()
        assert er.request_id == ""
        assert er.action_type == ""
        assert er.requester_role == ""
        assert er.justification == ""
        assert er.target_constraint == ""

    def test_exception_request_result_defaults(self):
        err = ExceptionRequestResult()
        assert err.request_id == ""
        assert err.approved is False
        assert err.review_initiated is False
        assert err.message == ""


class TestCustomFieldValues:
    def test_action_item_with_values(self):
        item = ActionItem(
            action_id="act-1",
            action_type="observe",
            description="Observe temperature",
            execution_mode="semi_auto",
            risk_level="medium",
        )
        assert item.action_id == "act-1"
        assert item.execution_mode == "semi_auto"
        assert item.risk_level == "medium"

    def test_forbidden_action_permanently(self):
        fa = ForbiddenAction(
            action_id="forbid-1",
            action_type="shutdown",
            prohibition_reason="Safety interlock",
            permanently_forbidden=True,
        )
        assert fa.permanently_forbidden is True

    def test_conditional_action_with_prerequisites(self):
        ca = ConditionalAction(
            action_id="cond-1",
            unmet_prerequisites=["pre-1", "pre-2"],
            conditions_to_unlock=["Satisfy pre-1", "Satisfy pre-2"],
            prerequisites_met=False,
        )
        assert len(ca.unmet_prerequisites) == 2
        assert ca.prerequisites_met is False

    def test_bridge_output_with_action_space(self):
        space = ActionSpace(
            immediate_actions=[ActionItem(action_id="a1")],
            forbidden_actions=[ForbiddenAction(action_id="f1", permanently_forbidden=True)],
        )
        out = BridgeOutput(
            output_id="out-1",
            object_id="obj-1",
            action_space=space,
            version_tag="v:abc:1.0",
        )
        assert out.output_id == "out-1"
        assert len(out.action_space.immediate_actions) == 1
        assert len(out.action_space.forbidden_actions) == 1

    def test_exception_request_result_review_only(self):
        """Permanently forbidden: approved=False, review_initiated=True."""
        err = ExceptionRequestResult(
            request_id="req-1",
            approved=False,
            review_initiated=True,
            message="Permanently forbidden action - review initiated",
        )
        assert err.approved is False
        assert err.review_initiated is True


class TestInheritance:
    def test_conditional_action_inherits_action_item(self):
        ca = ConditionalAction(action_id="ca-1", action_type="adjust")
        assert isinstance(ca, ActionItem)
        assert ca.action_id == "ca-1"

    def test_undetermined_action_inherits_action_item(self):
        ua = UndeterminedAction(action_id="ua-1", action_type="check")
        assert isinstance(ua, ActionItem)
        assert ua.action_id == "ua-1"
