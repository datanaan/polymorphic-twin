"""Bridge-specific type definitions.

These types define the data structures used by the Bridge decision
interface layer. All models are Pydantic v2 BaseModel instances.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """A single actionable item in the immediate action category.

    Attributes:
        action_id: Unique action identifier.
        action_type: Category of action (e.g. "observe", "adjust").
        description: Human-readable description of what this action does.
        execution_mode: How the action is executed (manual, semi_auto, autonomous).
        risk_level: Assessed risk level (low, medium, high).
        prerequisites_met: Whether all prerequisites for this action are satisfied.
        lawful_unlock_path: Ordered list of steps to lawfully unlock this action.
    """

    action_id: str = ""
    action_type: str = ""
    description: str = ""
    execution_mode: str = "manual"  # manual | semi_auto | autonomous
    risk_level: str = "low"  # low | medium | high
    prerequisites_met: bool = True
    lawful_unlock_path: list[str] = Field(default_factory=list)


class ConditionalAction(ActionItem):
    """An action that requires prerequisites to be met before execution.

    Attributes:
        unmet_prerequisites: List of prerequisites not yet satisfied.
        conditions_to_unlock: Steps required to unlock this action.
    """

    unmet_prerequisites: list[str] = Field(default_factory=list)
    conditions_to_unlock: list[str] = Field(default_factory=list)


class ForbiddenAction(BaseModel):
    """An action that is currently prohibited.

    Attributes:
        action_id: Unique action identifier.
        action_type: Category of action.
        description: Human-readable description of the forbidden action.
        prohibition_reason: Why this action is forbidden.
        lawful_unlock_conditions: Conditions under which this action could be unlocked.
        permanently_forbidden: If True, this action can never be unlocked directly.
    """

    action_id: str = ""
    action_type: str = ""
    description: str = ""
    prohibition_reason: str = ""
    lawful_unlock_conditions: list[str] = Field(default_factory=list)
    permanently_forbidden: bool = False


class UndeterminedAction(ActionItem):
    """An action whose feasibility cannot be determined due to insufficient data.

    Attributes:
        missing_information: List of data points needed to determine feasibility.
        required_data_sources: Sources that could provide the missing information.
    """

    missing_information: list[str] = Field(default_factory=list)
    required_data_sources: list[str] = Field(default_factory=list)


class ActionSpace(BaseModel):
    """Four-category action space presented to human decision makers.

    Categories:
        immediate_actions: Actions with all prerequisites met, ready to execute.
        conditional_actions: Actions with unmet prerequisites, require unlock steps.
        forbidden_actions: Actions currently prohibited by constraint violations.
        undetermined_actions: Actions whose feasibility is unknown due to missing data.
    """

    immediate_actions: list[ActionItem] = Field(default_factory=list)
    conditional_actions: list[ConditionalAction] = Field(default_factory=list)
    forbidden_actions: list[ForbiddenAction] = Field(default_factory=list)
    undetermined_actions: list[UndeterminedAction] = Field(default_factory=list)


class BridgeOutput(BaseModel):
    """Complete output from the Bridge decision interface.

    Attributes:
        output_id: Unique output identifier.
        object_id: The TwinObject identifier this output pertains to.
        action_space: The four-category action space.
        valid_until: ISO 8601 timestamp when this output expires.
        version_tag: Version tag for validity tracking.
        created_at: ISO 8601 timestamp when this output was created.
    """

    output_id: str = ""
    object_id: str = ""
    action_space: ActionSpace = Field(default_factory=ActionSpace)
    valid_until: str = ""
    version_tag: str = ""
    created_at: str = ""


class ExceptionRequest(BaseModel):
    """A request to make an exception for a forbidden or conditional action.

    Attributes:
        request_id: Unique request identifier.
        action_type: The type of action being requested.
        requester_role: The role of the human making the request.
        justification: Why the exception should be considered.
        target_constraint: The constraint being challenged.
    """

    request_id: str = ""
    action_type: str = ""
    requester_role: str = ""
    justification: str = ""
    target_constraint: str = ""


class ExceptionRequestResult(BaseModel):
    """Result of processing an exception request.

    Note: exception_request != override. Permanently forbidden actions
    can only trigger a review, never a direct override.

    Attributes:
        request_id: The request this result pertains to.
        approved: Whether the exception was approved (always False initially).
        review_initiated: Whether a review process has been started.
        message: Human-readable explanation of the result.
    """

    request_id: str = ""
    approved: bool = False
    review_initiated: bool = False
    message: str = ""
