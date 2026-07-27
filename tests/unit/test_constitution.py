"""Tests for the BridgeConstitution.

Key tests:
1. Output containing "建议" -> violation detected
2. Output containing "recommend" -> violation detected
3. Output containing "suggestion" -> violation detected
4. Output containing "should" -> violation detected
5. Clean output -> no violations
6. Direct command to actuator -> flagged
7. Action description with forbidden word -> flagged
"""

from polytwin.bridge.constitution import BridgeConstitution
from polytwin.bridge.types import (
    ActionItem,
    ActionSpace,
    BridgeOutput,
    ForbiddenAction,
)


def _make_output(**overrides) -> BridgeOutput:
    defaults = {
        "output_id": "out-1",
        "object_id": "obj-1",
        "action_space": ActionSpace(),
        "version_tag": "v:abc:1.0",
    }
    defaults.update(overrides)
    return BridgeOutput(**defaults)


class TestOutputValidation:
    def test_clean_output_no_violations(self):
        """Clean output with no forbidden words -> no violations."""
        output = _make_output()
        violations = BridgeConstitution.validate_output(output)
        assert violations == []

    def test_suggestion_word_in_description_violation(self):
        """Output containing '建议' in action description -> violation."""
        output = _make_output(
            action_space=ActionSpace(
                immediate_actions=[
                    ActionItem(
                        action_id="a1",
                        description="建议执行冷却操作",
                    ),
                ],
            ),
        )
        violations = BridgeConstitution.validate_output(output)
        assert len(violations) > 0
        assert any("建议" in v for v in violations)

    def test_recommend_violation(self):
        """Output containing 'recommend' -> violation."""
        output = _make_output(
            action_space=ActionSpace(
                immediate_actions=[
                    ActionItem(
                        action_id="a1",
                        description="We recommend adjusting temperature",
                    ),
                ],
            ),
        )
        violations = BridgeConstitution.validate_output(output)
        assert len(violations) > 0
        assert any("recommend" in v for v in violations)

    def test_suggestion_violation(self):
        """Output containing 'suggestion' -> violation."""
        output = _make_output(
            action_space=ActionSpace(
                immediate_actions=[
                    ActionItem(
                        action_id="a1",
                        description="A suggestion for improvement",
                    ),
                ],
            ),
        )
        violations = BridgeConstitution.validate_output(output)
        assert len(violations) > 0
        assert any("suggestion" in v for v in violations)

    def test_should_violation(self):
        """Output containing 'should' -> violation."""
        output = _make_output(
            action_space=ActionSpace(
                immediate_actions=[
                    ActionItem(
                        action_id="a1",
                        description="You should monitor temperature",
                    ),
                ],
            ),
        )
        violations = BridgeConstitution.validate_output(output)
        assert len(violations) > 0
        assert any("should" in v for v in violations)

    def test_multiple_violations(self):
        """Output with multiple forbidden words -> multiple violations."""
        output = _make_output(
            action_space=ActionSpace(
                immediate_actions=[
                    ActionItem(
                        action_id="a1",
                        description="We recommend this adjustment",
                    ),
                    ActionItem(
                        action_id="a2",
                        description="A suggestion for later",
                    ),
                ],
            ),
        )
        violations = BridgeConstitution.validate_output(output)
        assert len(violations) >= 2

    def test_forbidden_word_in_forbidden_action_reason(self):
        """Forbidden word in prohibition_reason -> violation."""
        output = _make_output(
            action_space=ActionSpace(
                forbidden_actions=[
                    ForbiddenAction(
                        action_id="f1",
                        prohibition_reason="This action should not be taken",
                    ),
                ],
            ),
        )
        violations = BridgeConstitution.validate_output(output)
        assert len(violations) > 0


class TestActuatorCommands:
    def test_direct_command_flagged(self):
        """Action with direct_command=True -> flagged as actuator command."""
        action = {"direct_command": True, "action_id": "a1"}
        assert BridgeConstitution.is_command_to_actuator(action) is True

    def test_indirect_action_not_flagged(self):
        """Action without direct_command -> not flagged."""
        action = {"action_id": "a1", "action_type": "observe"}
        assert BridgeConstitution.is_command_to_actuator(action) is False

    def test_explicit_false_not_flagged(self):
        """Action with direct_command=False -> not flagged."""
        action = {"direct_command": False, "action_id": "a1"}
        assert BridgeConstitution.is_command_to_actuator(action) is False

    def test_missing_key_not_flagged(self):
        """Action without direct_command key -> not flagged."""
        action = {"action_id": "a1"}
        assert BridgeConstitution.is_command_to_actuator(action) is False


class TestActionValidation:
    def test_action_with_forbidden_word_in_description(self):
        """Action description containing forbidden word -> violation."""
        action = {
            "description": "We recommend this action",
            "direct_command": False,
        }
        violations = BridgeConstitution.validate_action(action)
        assert len(violations) > 0
        assert any("recommend" in v for v in violations)

    def test_action_direct_command_violation(self):
        """Action with direct_command=True -> constitution violation."""
        action = {
            "description": "Execute",
            "direct_command": True,
        }
        violations = BridgeConstitution.validate_action(action)
        assert len(violations) > 0
        assert any("direct command" in v.lower() for v in violations)

    def test_clean_action_no_violations(self):
        """Clean action -> no violations."""
        action = {
            "description": "Observe current state",
            "direct_command": False,
        }
        violations = BridgeConstitution.validate_action(action)
        assert violations == []

    def test_forbidden_words_list_immutable(self):
        """FORBIDDEN_WORDS is a class-level constant."""
        words = BridgeConstitution.FORBIDDEN_WORDS
        assert "建议" in words
        assert "recommend" in words
        assert "suggestion" in words
        assert "should" in words
