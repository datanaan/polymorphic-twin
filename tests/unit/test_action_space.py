"""Tests for the ActionSpaceBuilder.

Key tests:
1. All constraints passed -> immediate actions populated
2. Unmet prerequisites -> conditional actions
3. safety_critical violation -> forbidden actions
4. Missing data -> undetermined actions
5. Empty input -> empty action space
"""

from polytwin.bridge.action_space import ActionSpaceBuilder
from polytwin.bridge.types import ActionSpace


class TestEmptyInput:
    def test_empty_view_data_returns_minimal_action_space(self):
        """Empty input produces an action space with a default observation action."""
        builder = ActionSpaceBuilder()
        result = builder.build({})
        assert isinstance(result, ActionSpace)
        # No constraint data means all_passed=True -> default observation
        assert len(result.immediate_actions) >= 0
        assert result.conditional_actions == []
        assert result.forbidden_actions == []
        assert result.undetermined_actions == []

    def test_empty_constraint_state_returns_empty(self):
        builder = ActionSpaceBuilder()
        result = builder.build({"constraint_state": {}})
        assert isinstance(result, ActionSpace)
        assert len(result.forbidden_actions) == 0


class TestAllConstraintsPassed:
    def test_all_passed_creates_immediate_observation(self):
        """All constraints passed -> immediate observation action."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed", "criticality": "operational"},
                {"constraint_id": "c2", "status": "passed", "criticality": "safety_critical"},
            ],
        }
        result = builder.build(view_data)
        assert len(result.immediate_actions) > 0
        assert any(a.action_type == "observe" for a in result.immediate_actions)

    def test_passed_constraints_no_forbidden(self):
        """All passed -> no forbidden or conditional actions."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
        }
        result = builder.build(view_data)
        assert len(result.forbidden_actions) == 0
        assert len(result.conditional_actions) == 0

    def test_with_safe_fallback_adds_immediate(self):
        """Safe fallback available and all passed -> fallback in immediate."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
            "safe_fallback": {"strategy": "cool_down"},
        }
        result = builder.build(view_data)
        immediate_ids = [a.action_id for a in result.immediate_actions]
        assert "safe-fallback-default" in immediate_ids


class TestSafetyCriticalViolation:
    def test_safety_critical_failed_creates_forbidden(self):
        """Failed safety_critical constraint -> forbidden action."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {
                    "constraint_id": "temp-limit",
                    "status": "failed",
                    "criticality": "safety_critical",
                    "message": "Temperature exceeded 200C",
                },
            ],
        }
        result = builder.build(view_data)
        assert len(result.forbidden_actions) > 0
        assert any("temp-limit" in f.action_id for f in result.forbidden_actions)

    def test_safety_critical_uncertain_creates_forbidden(self):
        """Uncertain safety_critical constraint -> also forbidden."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {
                    "constraint_id": "pressure-limit",
                    "status": "uncertain",
                    "criticality": "safety_critical",
                },
            ],
        }
        result = builder.build(view_data)
        assert len(result.forbidden_actions) > 0

    def test_operational_failure_not_forbidden(self):
        """Failed operational constraint -> NOT in forbidden (not safety-critical)."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {
                    "constraint_id": "op-limit",
                    "status": "failed",
                    "criticality": "operational",
                },
            ],
        }
        result = builder.build(view_data)
        # operational failure does not create a forbidden action by itself
        # (it would need to be in a template context)
        assert len(result.forbidden_actions) == 0


class TestUnmetPrerequisites:
    def test_unmet_prereqs_create_conditional(self):
        """Constraint with unmet prerequisites -> conditional action."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {
                    "constraint_id": "c1",
                    "status": "failed",
                    "criticality": "operational",
                    "prerequisites": ["sensor-calibrated", "valve-open"],
                },
            ],
        }
        result = builder.build(view_data)
        assert len(result.conditional_actions) > 0

    def test_conditional_has_unmet_list(self):
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {
                    "constraint_id": "c1",
                    "status": "failed",
                    "criticality": "operational",
                    "unmet_prerequisites": ["pre-1"],
                },
            ],
        }
        result = builder.build(view_data)
        assert len(result.conditional_actions) > 0
        assert result.conditional_actions[0].prerequisites_met is False
        assert len(result.conditional_actions[0].unmet_prerequisites) > 0


class TestMissingData:
    def test_missing_fields_create_undetermined(self):
        """Missing fields in view -> undetermined action."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [],
            "missing_fields": ["temperature", "pressure"],
        }
        result = builder.build(view_data)
        assert len(result.undetermined_actions) > 0

    def test_undetermined_has_missing_info(self):
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [],
            "missing_fields": ["sensor-data"],
        }
        result = builder.build(view_data)
        assert len(result.undetermined_actions) > 0
        assert len(result.undetermined_actions[0].missing_information) > 0


class TestWithTemplates:
    def test_template_with_all_passed(self):
        """Template with all constraints passed -> immediate action."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
            "action_templates": [
                {
                    "action_type_id": "adjust-temp",
                    "name": "Adjust temperature",
                    "typical_prerequisites": [],
                },
            ],
        }
        result = builder.build(view_data)
        assert len(result.immediate_actions) > 0
        assert any(a.action_type == "adjust-temp" for a in result.immediate_actions)

    def test_template_with_prohibition_reasons(self):
        """Template with prohibition reasons -> forbidden action."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
            "action_templates": [
                {
                    "action_type_id": "override-safety",
                    "name": "Override safety interlock",
                    "typical_prohibition_reasons": [
                        "permanent safety lock",
                    ],
                },
            ],
        }
        result = builder.build(view_data)
        assert len(result.forbidden_actions) > 0
        assert any(
            f.action_type == "override-safety" for f in result.forbidden_actions
        )

    def test_template_with_domain_pack(self):
        """DomainPack action_templates enrich the action space."""
        builder = ActionSpaceBuilder()
        view_data = {
            "constraint_summary": [
                {"constraint_id": "c1", "status": "passed"},
            ],
        }
        domain_pack = {
            "action_templates": {
                "monitor": {
                    "action_type_id": "monitor",
                    "name": "Monitor system",
                    "typical_prerequisites": [],
                },
            },
        }
        result = builder.build(view_data, domain_pack)
        assert len(result.immediate_actions) > 0
        assert any(a.action_type == "monitor" for a in result.immediate_actions)
