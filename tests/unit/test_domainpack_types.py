"""Tests for DomainPack Pydantic types (types.py)."""
from pathlib import Path

import pytest
import yaml

from polytwin.domainpack.types import (
    ConstraintCard,
    DomainOfValidity,
    DomainPack,
    InheritancePolicy,
    RigidityCriticalityCompatibility,
    SafeFallback,
    StateVariable,
    ValidityCondition,
)

CONFIGS = Path("configs/examples")


class TestDomainPackParsing:
    """Test parsing the minimal-domain-pack.yaml into a DomainPack model."""

    @pytest.fixture()
    def minimal_data(self) -> dict:
        text = (CONFIGS / "minimal-domain-pack.yaml").read_text()
        return yaml.safe_load(text)

    def test_parse_minimal_domain_pack(self, minimal_data):
        pack = DomainPack.model_validate(minimal_data)
        assert pack.domain_id == "example.minimal_device_monitor"
        assert pack.domain_name == "最小设备监控场景"
        assert pack.domain_version == "0.1.0"

    def test_variables_property(self, minimal_data):
        pack = DomainPack.model_validate(minimal_data)
        vars_ = pack.variables
        var_names = {v.name for v in vars_}
        assert "temperature" in var_names
        assert "pressure" in var_names
        assert "operating_mode" in var_names
        assert "vibration_freq" in var_names
        assert "output_quality" in var_names
        assert len(vars_) == 5

    def test_variable_names_property(self, minimal_data):
        pack = DomainPack.model_validate(minimal_data)
        assert pack.variable_names == {
            "temperature", "pressure", "operating_mode",
            "vibration_freq", "output_quality",
        }

    def test_safe_fallback_parsed(self, minimal_data):
        pack = DomainPack.model_validate(minimal_data)
        assert pack.safe_fallback.policy_id == "minimal_safe_shutdown"
        assert pack.safe_fallback.target_state is not None
        assert pack.safe_fallback.max_duration == "PT5M"

    def test_human_roles_parsed(self, minimal_data):
        pack = DomainPack.model_validate(minimal_data)
        assert len(pack.human_roles) == 2
        assert pack.human_roles[0].role_id == "operator"
        assert pack.human_roles[1].role_id == "supervisor"

    def test_inheritance_policy_parsed(self, minimal_data):
        pack = DomainPack.model_validate(minimal_data)
        ip = pack.inheritance_policy
        assert ip.can_relax_parent_absolute_constraints is False
        assert ip.can_lower_parent_criticality is False
        assert ip.conflict_resolution == "stricter_wins"


class TestValidityConditionTypes:
    """Test all 5 ValidityCondition types parse correctly."""

    def test_state_range_condition(self):
        cond = ValidityCondition(
            type="state_range",
            variable="temperature",
            min=-20.0,
            max=200.0,
            inclusive=True,
        )
        assert cond.type == "state_range"
        assert cond.variable == "temperature"
        assert cond.min == -20.0
        assert cond.max == 200.0
        assert cond.inclusive is True

    def test_state_enum_condition(self):
        cond = ValidityCondition(
            type="state_enum",
            variable="operating_mode",
            values=["normal", "startup"],
        )
        assert cond.type == "state_enum"
        assert cond.values == ["normal", "startup"]

    def test_sensor_status_condition(self):
        cond = ValidityCondition(
            type="sensor_status",
            sensor_id="thermocouple_internal",
            required_status="active",
        )
        assert cond.type == "sensor_status"
        assert cond.sensor_id == "thermocouple_internal"
        assert cond.required_status == "active"

    def test_identity_confidence_condition(self):
        cond = ValidityCondition(
            type="identity_confidence",
            min_confidence=0.7,
        )
        assert cond.type == "identity_confidence"
        assert cond.min_confidence == 0.7

    def test_composite_condition(self):
        cond = ValidityCondition(
            type="composite",
            operator="and",
            sub_conditions=[
                ValidityCondition(type="state_range", variable="temperature", min=50.0, max=180.0),
                ValidityCondition(type="state_range", variable="pressure", min=5.0, max=45.0),
            ],
        )
        assert cond.type == "composite"
        assert cond.operator == "and"
        assert len(cond.sub_conditions) == 2
        assert cond.sub_conditions[0].variable == "temperature"

    def test_composite_from_yaml_data(self):
        """Parse the composite condition from minimal-domain-pack.yaml."""
        data = yaml.safe_load((CONFIGS / "minimal-domain-pack.yaml").read_text())
        # temp_pressure_coupling constraint has a composite condition
        coupling_card = None
        for card in data["constraint_cards"]["absolute"]:
            if card["constraint_id"] == "temp_pressure_coupling":
                coupling_card = card
                break
        assert coupling_card is not None
        dov = DomainOfValidity.model_validate(coupling_card["domain_of_validity"])
        assert len(dov.conditions) == 1
        composite = dov.conditions[0]
        assert composite.type == "composite"
        assert composite.operator == "and"
        assert len(composite.sub_conditions) == 2


class TestConstraintCardParsing:
    """Test ConstraintCard parsing from YAML data."""

    def test_absolute_constraint_card(self):
        data = {
            "constraint_id": "temp_safety_limit",
            "scenario_criticality": "safety_critical",
            "domain_of_validity": {
                "conditions": [
                    {"type": "state_range", "variable": "temperature", "min": -20.0, "max": 200.0},
                ],
            },
            "validation": {"method": "range_check", "config": {"variable": "temperature", "max": 180.0}},
            "tolerance": {"absolute": 2.0},
            "violation_priority": 1,
        }
        card = ConstraintCard.model_validate(data)
        assert card.constraint_id == "temp_safety_limit"
        assert card.scenario_criticality == "safety_critical"
        assert card.tolerance is not None
        assert card.tolerance.absolute == 2.0
        assert card.violation_priority == 1

    def test_soft_constraint_card_with_weight(self):
        data = {
            "constraint_id": "output_quality_target",
            "scenario_criticality": "operational",
            "weight": 0.8,
            "domain_of_validity": {"conditions": []},
            "validation": {"method": "threshold_exceeded", "config": {}},
        }
        card = ConstraintCard.model_validate(data)
        assert card.weight == 0.8
        assert card.scenario_criticality == "operational"


class TestDefaultValues:
    """Test that default values are correct."""

    def test_validity_condition_defaults(self):
        cond = ValidityCondition(type="state_range", variable="x")
        assert cond.inclusive is True
        assert cond.min is None
        assert cond.max is None
        assert cond.values is None
        assert cond.sub_conditions is None

    def test_domain_of_validity_defaults(self):
        dov = DomainOfValidity()
        assert dov.conditions == []
        assert dov.match_mode == "all"

    def test_state_variable_defaults(self):
        sv = StateVariable(
            name="test_var",
            physical_meaning="test",
            unit="unitless",
        )
        assert sv.range_min == 0.0
        assert sv.range_max == 0.0
        assert sv.observability == "observable"
        assert sv.controllability == "uncontrollable"
        assert sv.measurement_source is None
        assert sv.required is True

    def test_inheritance_policy_defaults(self):
        ip = InheritancePolicy()
        assert ip.can_relax_parent_absolute_constraints is False
        assert ip.can_lower_parent_criticality is False
        assert ip.conflict_resolution == "stricter_wins"

    def test_rigidity_criticality_compatibility_defaults(self):
        rcc = RigidityCriticalityCompatibility()
        assert rcc.safety_critical == "must_be_absolute"
        assert rcc.identity_critical == "absolute_or_strictly_audited"

    def test_safe_fallback_defaults(self):
        sf = SafeFallback(policy_id="test")
        assert sf.max_duration == "PT0S"
        assert sf.unavailable_action == "safe_shutdown"
        assert sf.post_fallback_action == "hold"
