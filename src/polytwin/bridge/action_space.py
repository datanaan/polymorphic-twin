"""Action space builder for the Bridge decision interface.

Constructs a four-category action space from BridgeDecisionView data
and DomainPack configuration:

1. immediate_actions: All constraints passed, prerequisites met.
2. conditional_actions: Some prerequisites not yet satisfied.
3. forbidden_actions: Safety-critical constraint violations.
4. undetermined_actions: Insufficient data to determine feasibility.
"""
from __future__ import annotations

from polytwin.bridge.types import (
    ActionItem,
    ActionSpace,
    ConditionalAction,
    ForbiddenAction,
    UndeterminedAction,
)


def _extract_constraint_state(view_data: dict) -> dict:
    """Extract constraint state from view data, handling multiple formats."""
    result = view_data.get("constraint_state", {})
    return result if isinstance(result, dict) else {}


def _extract_constraint_summary(view_data: dict) -> list[dict]:
    """Extract constraint summary from view data.

    Supports both 'constraint_summary' (BridgeDecisionView format)
    and 'constraint_state.last_evaluation' (internal format).
    """
    # BridgeDecisionView provides constraint_summary
    summary = view_data.get("constraint_summary", [])
    if summary:
        return list(summary) if not isinstance(summary, list) else summary

    # Internal format: constraint_state.last_evaluation
    constraint_state = _extract_constraint_state(view_data)
    result = constraint_state.get("last_evaluation", [])
    return list(result) if not isinstance(result, list) else result


def _extract_action_templates(view_data: dict, domain_pack: dict | None) -> list[dict]:
    """Extract action templates from view data or domain pack."""
    # BridgeDecisionView provides action_templates directly
    templates = view_data.get("action_templates", [])
    if templates:
        return list(templates) if not isinstance(templates, list) else templates

    # Fall back to domain pack
    if domain_pack:
        templates_raw = domain_pack.get("action_templates", {})
        # action_templates may be a dict keyed by action_type_id
        if isinstance(templates_raw, dict):
            return list(templates_raw.values())
        if isinstance(templates_raw, list):
            return list(templates_raw)
    return []


def _extract_human_roles(view_data: dict, domain_pack: dict | None) -> list[dict]:
    """Extract human roles from view data or domain pack."""
    roles = view_data.get("human_roles", [])
    if roles:
        return list(roles) if not isinstance(roles, list) else roles
    if domain_pack:
        result = domain_pack.get("human_roles", [])
        return list(result) if not isinstance(result, list) else result
    return []


def _is_safety_critical_failed(entry: dict) -> bool:
    """Check if a constraint entry represents a safety-critical failure."""
    status = entry.get("status", "")
    criticality = entry.get("criticality", "")
    # Handle both string and enum values
    status_val = status.value if hasattr(status, "value") else str(status)
    criticality_val = criticality.value if hasattr(criticality, "value") else str(criticality)
    return status_val in ("failed", "uncertain") and criticality_val == "safety_critical"


def _is_constraint_failed(entry: dict) -> bool:
    """Check if a constraint entry represents any failure."""
    status = entry.get("status", "")
    status_val = status.value if hasattr(status, "value") else str(status)
    return status_val == "failed"


def _has_prerequisites(entry: dict) -> bool:
    """Check if a constraint evaluation mentions unmet prerequisites."""
    prerequisites = entry.get("prerequisites", [])
    unmet = entry.get("unmet_prerequisites", [])
    return bool(prerequisites) or bool(unmet)


class ActionSpaceBuilder:
    """Builds a four-category action space from BridgeDecisionView data.

    The builder categorizes actions based on:
    - Constraint evaluation results (passed, failed, uncertain)
    - Prerequisite satisfaction status
    - Criticality levels (safety_critical, identity_critical, operational, informational)
    - Data availability for determination
    """

    def build(self, view_data: dict, domain_pack: dict | None = None) -> ActionSpace:
        """Build four-category action space from BridgeDecisionView data.

        Args:
            view_data: Dictionary containing BridgeDecisionView-projected data.
                Expected keys: constraint_state, constraint_summary,
                action_state, action_templates, human_roles.
            domain_pack: Optional DomainPack configuration dictionary for
                enriching action templates and role permissions.

        Returns:
            ActionSpace with actions categorized into four buckets.
        """
        immediate: list[ActionItem] = []
        conditional: list[ConditionalAction] = []
        forbidden: list[ForbiddenAction] = []
        undetermined: list[UndeterminedAction] = []

        constraint_summary = _extract_constraint_summary(view_data)
        templates = _extract_action_templates(view_data, domain_pack)
        _extract_constraint_state(view_data)

        # Track constraint statuses for categorization
        all_passed = True
        has_uncertain = False
        has_missing_data = False
        failed_critical: list[dict] = []
        unmet_prereq_entries: list[dict] = []

        for entry in constraint_summary:
            status = entry.get("status", "passed")
            status_val = status.value if hasattr(status, "value") else str(status)
            criticality = entry.get("criticality", "operational")
            criticality_val = criticality.value if hasattr(criticality, "value") else str(criticality)

            if status_val == "passed":
                continue
            elif status_val == "failed":
                all_passed = False
                if criticality_val == "safety_critical":
                    failed_critical.append(entry)
                elif _has_prerequisites(entry):
                    unmet_prereq_entries.append(entry)
            elif status_val == "uncertain":
                all_passed = False
                has_uncertain = True
                if criticality_val == "safety_critical":
                    failed_critical.append(entry)
            elif status_val == "not_applicable":
                continue

        # Check for missing data indicators
        view_data.get("data_sources", [])
        missing_fields = view_data.get("missing_fields", [])
        if missing_fields or (has_uncertain and not constraint_summary):
            has_missing_data = True

        # Build action items from templates if available
        if templates:
            for tmpl in templates:
                self._categorize_template(
                    tmpl, constraint_summary, all_passed,
                    failed_critical, unmet_prereq_entries,
                    immediate, conditional, forbidden, undetermined,
                    has_missing_data,
                )
        else:
            # Build from constraint evaluations directly
            self._build_from_constraints(
                constraint_summary, all_passed,
                failed_critical, unmet_prereq_entries,
                immediate, conditional, forbidden, undetermined,
                has_missing_data, has_uncertain,
            )

        # Add safe fallback as an immediate action if available
        safe_fallback = view_data.get("safe_fallback")
        if safe_fallback and all_passed:
            fallback = safe_fallback if isinstance(safe_fallback, dict) else {}
            immediate.append(ActionItem(
                action_id="safe-fallback-default",
                action_type="safe_fallback",
                description=fallback.get("strategy", "Execute safe fallback strategy"),
                execution_mode="manual",
                risk_level="low",
                prerequisites_met=True,
                lawful_unlock_path=["confirm_fallback"],
            ))

        return ActionSpace(
            immediate_actions=immediate,
            conditional_actions=conditional,
            forbidden_actions=forbidden,
            undetermined_actions=undetermined,
        )

    def _categorize_template(
        self,
        template: dict,
        constraint_summary: list[dict],
        all_passed: bool,
        failed_critical: list[dict],
        unmet_prereq_entries: list[dict],
        immediate: list[ActionItem],
        conditional: list[ConditionalAction],
        forbidden: list[ForbiddenAction],
        undetermined: list[UndeterminedAction],
        has_missing_data: bool,
    ) -> None:
        """Categorize a single action template into the appropriate bucket."""
        tmpl_id = template.get("action_type_id", template.get("template_id", ""))
        tmpl_name = template.get("name", template.get("description_template", ""))
        prereqs = template.get("typical_prerequisites", [])
        prohibition_reasons = template.get("typical_prohibition_reasons", [])
        applicable_when = template.get("applicable_when", [])

        # Check if this template is blocked by a safety-critical failure
        is_blocked_by_critical = False
        for fc in failed_critical:
            constraint_id = fc.get("constraint_id", "")
            if applicable_when and constraint_id not in applicable_when:
                continue
            is_blocked_by_critical = True
            break

        if is_blocked_by_critical:
            forbidden.append(ForbiddenAction(
                action_id=f"forbid-{tmpl_id}",
                action_type=tmpl_id,
                description=tmpl_name,
                prohibition_reason="Blocked by safety-critical constraint failure",
                lawful_unlock_conditions=["Resolve safety-critical violation"],
                permanently_forbidden=False,
            ))
        elif prohibition_reasons:
            # Template has inherent prohibition reasons
            is_permanent = any("permanent" in r.lower() for r in prohibition_reasons)
            forbidden.append(ForbiddenAction(
                action_id=f"forbid-{tmpl_id}",
                action_type=tmpl_id,
                description=tmpl_name,
                prohibition_reason=prohibition_reasons[0],
                lawful_unlock_conditions=prohibition_reasons[1:] if len(prohibition_reasons) > 1 else [],
                permanently_forbidden=is_permanent,
            ))
        elif prereqs and not all_passed:
            # Has prerequisites and some constraints are not all passed
            unmet = [p for p in prereqs if not self._is_prereq_satisfied(p, constraint_summary)]
            if unmet:
                conditional.append(ConditionalAction(
                    action_id=f"cond-{tmpl_id}",
                    action_type=tmpl_id,
                    description=tmpl_name,
                    execution_mode="manual",
                    risk_level="medium",
                    prerequisites_met=False,
                    lawful_unlock_path=unmet,
                    unmet_prerequisites=unmet,
                    conditions_to_unlock=unmet,
                ))
            else:
                immediate.append(ActionItem(
                    action_id=f"imm-{tmpl_id}",
                    action_type=tmpl_id,
                    description=tmpl_name,
                    execution_mode="manual",
                    risk_level="low",
                    prerequisites_met=True,
                ))
        elif has_missing_data:
            undetermined.append(UndeterminedAction(
                action_id=f"undet-{tmpl_id}",
                action_type=tmpl_id,
                description=tmpl_name,
                missing_information=["Insufficient data to determine feasibility"],
                required_data_sources=["Constraint evaluation data"],
            ))
        else:
            # All clear -- immediate action
            immediate.append(ActionItem(
                action_id=f"imm-{tmpl_id}",
                action_type=tmpl_id,
                description=tmpl_name,
                execution_mode="manual",
                risk_level="low",
                prerequisites_met=True,
            ))

    def _build_from_constraints(
        self,
        constraint_summary: list[dict],
        all_passed: bool,
        failed_critical: list[dict],
        unmet_prereq_entries: list[dict],
        immediate: list[ActionItem],
        conditional: list[ConditionalAction],
        forbidden: list[ForbiddenAction],
        undetermined: list[UndeterminedAction],
        has_missing_data: bool,
        has_uncertain: bool,
    ) -> None:
        """Build action items directly from constraint evaluation results."""
        # Forbidden actions from safety-critical failures
        for fc in failed_critical:
            constraint_id = fc.get("constraint_id", "unknown")
            reason = fc.get("message", fc.get("prohibition_reason", ""))
            if not reason:
                reason = f"Safety-critical constraint {constraint_id} failed"
            forbidden.append(ForbiddenAction(
                action_id=f"forbid-{constraint_id}",
                action_type=f"action-for-{constraint_id}",
                description=f"Action blocked by {constraint_id}",
                prohibition_reason=reason,
                lawful_unlock_conditions=[f"Resolve {constraint_id} violation"],
                permanently_forbidden=False,
            ))

        # Conditional actions from unmet prerequisites
        for entry in unmet_prereq_entries:
            constraint_id = entry.get("constraint_id", "unknown")
            prereqs = entry.get("prerequisites", entry.get("unmet_prerequisites", []))
            conditional.append(ConditionalAction(
                action_id=f"cond-{constraint_id}",
                action_type=f"action-for-{constraint_id}",
                description=f"Action conditional on {constraint_id}",
                execution_mode="manual",
                risk_level="medium",
                prerequisites_met=False,
                lawful_unlock_path=prereqs,
                unmet_prerequisites=prereqs,
                conditions_to_unlock=prereqs,
            ))

        # Undetermined actions from uncertain evaluations with missing data
        if has_missing_data:
            undetermined.append(UndeterminedAction(
                action_id="undet-data-gap",
                action_type="data_gap_action",
                description="Action feasibility cannot be determined",
                missing_information=["Required data not available"],
                required_data_sources=["Sensor data", "Constraint evaluation"],
            ))

        # Immediate observation action when all constraints passed
        if all_passed and not constraint_summary:
            # Empty view with no constraints -- observation available
            immediate.append(ActionItem(
                action_id="imm-observe-default",
                action_type="observe",
                description="Observe current system state",
                execution_mode="manual",
                risk_level="low",
                prerequisites_met=True,
            ))
        elif all_passed:
            # All constraints passed -- observation action
            immediate.append(ActionItem(
                action_id="imm-observe-all-passed",
                action_type="observe",
                description="All constraints passed -- observation available",
                execution_mode="manual",
                risk_level="low",
                prerequisites_met=True,
            ))

    @staticmethod
    def _is_prereq_satisfied(prereq: str, constraint_summary: list[dict]) -> bool:
        """Check if a prerequisite is satisfied based on constraint evaluations."""
        for entry in constraint_summary:
            status = entry.get("status", "passed")
            status_val = status.value if hasattr(status, "value") else str(status)
            if prereq in entry.get("constraint_id", ""):
                return status_val == "passed"
        # If no matching constraint found, assume not satisfied
        return False
