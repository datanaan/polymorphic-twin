"""Bridge module: stateless decision interface layer for the Polymorphic-Twin framework.

The Bridge translates TwinObject views into structured action option spaces
for human decision makers. It is STATELESS -- no persistent state between calls.
It MUST NOT contain suggestions or equivalent in outputs.
exception_request != override -- permanently_forbidden actions can only trigger review.
Bridge does NOT send commands to physical actuators.

Key components:
- BridgeOrchestrator: main stateless entry point
- ActionSpaceBuilder: constructs 4-category action spaces
- ValidityManager: tracks output validity by version
- HumanResponseHandler: validates human responses and exception requests
- BridgeConstitution: enforces bridge constitution rules
"""
from polytwin.bridge.action_space import ActionSpaceBuilder
from polytwin.bridge.constitution import BridgeConstitution
from polytwin.bridge.human_response import HumanResponseHandler
from polytwin.bridge.orchestrator import BridgeOrchestrator
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
from polytwin.bridge.validity import ValidityManager

__all__ = [
    "ActionItem",
    "ActionSpace",
    "ActionSpaceBuilder",
    "BridgeConstitution",
    "BridgeOrchestrator",
    "BridgeOutput",
    "ConditionalAction",
    "ExceptionRequest",
    "ExceptionRequestResult",
    "ForbiddenAction",
    "HumanResponseHandler",
    "UndeterminedAction",
    "ValidityManager",
]
