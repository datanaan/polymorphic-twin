"""Bridge constitution enforcement.

Enforces the invariants that define the Bridge's role in the system:
1. Bridge outputs MUST NOT contain suggestion words (e.g. "建议", "recommend").
2. Bridge MUST NOT send direct commands to physical actuators.
"""
from __future__ import annotations

from polytwin.bridge.types import BridgeOutput


class BridgeConstitution:
    """Enforces Bridge constitution rules on outputs and actions.

    The constitution ensures that the Bridge stays within its defined
    role: presenting structured action option spaces without making
    recommendations or sending commands to physical actuators.
    """

    FORBIDDEN_WORDS: list[str] = [
        "建议",
        "recommend",
        "suggestion",
        "should",
    ]

    @classmethod
    def validate_output(cls, output: BridgeOutput) -> list[str]:
        """Check a BridgeOutput for constitution violations.

        Scans the serialized output for forbidden words that would
        indicate the Bridge is making suggestions rather than presenting
        neutral action options.

        Args:
            output: The BridgeOutput to validate.

        Returns:
            List of violation description strings. Empty if no violations.
        """
        violations: list[str] = []
        output_text = output.model_dump_json()
        for word in cls.FORBIDDEN_WORDS:
            if word in output_text:
                violations.append(
                    f"Constitution violation: output contains '{word}'"
                )
        return violations

    @classmethod
    def is_command_to_actuator(cls, action: dict) -> bool:
        """Check whether an action represents a direct command to a physical actuator.

        The Bridge MUST NOT send commands to physical actuators. This
        method detects if an action dictionary contains a direct_command
        flag set to True.

        Args:
            action: Dictionary describing an action.

        Returns:
            True if the action is a direct command to an actuator.
        """
        return action.get("direct_command", False) is True

    @classmethod
    def validate_action(cls, action: dict) -> list[str]:
        """Check a single action dictionary for constitution violations.

        Args:
            action: Dictionary describing an action.

        Returns:
            List of violation description strings. Empty if no violations.
        """
        violations: list[str] = []

        if cls.is_command_to_actuator(action):
            violations.append(
                "Constitution violation: action is a direct command to actuator"
            )

        # Check description for forbidden words
        description = action.get("description", "")
        for word in cls.FORBIDDEN_WORDS:
            if word in description:
                violations.append(
                    f"Constitution violation: action description contains '{word}'"
                )

        return violations
