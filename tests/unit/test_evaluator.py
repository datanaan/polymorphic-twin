"""Tests for the four-state constraint evaluator and domain_of_validity.

Test cases:
1.  temp=150, max=180 -> PASSED
2.  temp=190, max=180 -> FAILED
3.  temp=250, domain=[0,200] -> NOT_APPLICABLE
4.  missing variable -> still applicable (conservative)
5.  sensor offline -> still applicable (conservative)
6.  sensor active -> normal evaluation
7.  identity_low (0.5 < min 0.8) -> NOT_APPLICABLE
8.  composite AND all match -> applicable
9.  composite AND one miss -> NOT_APPLICABLE
10. empty domain -> always applicable
"""


from polytwin.core.rules.evaluator import evaluate_constraint, evaluate_domain_of_validity
from polytwin.tom.types import ConstraintStatus


def _card(
    constraint_id: str = "c_temp",
    variable: str = "temperature",
    method: str = "range_check",
    config: dict | None = None,
    domain_conditions: list | None = None,
    match_mode: str = "all",
    scenario_criticality: str = "safety_critical",
) -> dict:
    """Helper to build a minimal constraint card dict."""
    if config is None:
        config = {"variable": variable, "max": 180.0}
    dov: dict = {}
    if domain_conditions is not None:
        dov = {"conditions": domain_conditions, "match_mode": match_mode}
    return {
        "constraint_id": constraint_id,
        "scenario_criticality": scenario_criticality,
        "validation": {"method": method, "config": config},
        "domain_of_validity": dov,
    }


# ── Domain of validity tests ───────────────────────────────────────


class TestDomainOfValidity:
    """Tests 3, 4, 5, 7, 8, 9, 10 — domain_of_validity behaviour."""

    # Test 10: empty domain -> always applicable
    def test_empty_domain_always_applicable(self):
        assert evaluate_domain_of_validity([], "all", {}) is True

    # Test 3: value outside domain range -> NOT_APPLICABLE
    def test_state_range_outside_domain(self):
        conditions = [{"type": "state_range", "variable": "temperature", "min": 0, "max": 200}]
        assert evaluate_domain_of_validity(conditions, "all", {"temperature": 250}) is False

    # Test 4: missing variable -> still applicable (conservative)
    def test_missing_variable_still_applicable(self):
        conditions = [{"type": "state_range", "variable": "nonexistent", "min": 0, "max": 100}]
        assert evaluate_domain_of_validity(conditions, "all", {}) is True

    # Test 5: sensor offline (unknown) -> still applicable (conservative)
    def test_unknown_sensor_still_applicable(self):
        conditions = [{"type": "sensor_status", "sensor_id": "s1", "required_status": "active"}]
        # No sensor_status dict provided -> sensor is unknown -> applicable
        assert evaluate_domain_of_validity(conditions, "all", {}) is True

    # Test 6b: sensor active -> constraint is applicable
    def test_sensor_active_applicable(self):
        conditions = [{"type": "sensor_status", "sensor_id": "s1", "required_status": "active"}]
        assert (
            evaluate_domain_of_validity(
                conditions, "all", {}, sensor_status={"s1": "active"}
            )
            is True
        )

    # Test 6c: sensor inactive -> constraint NOT applicable
    def test_sensor_inactive_not_applicable(self):
        conditions = [{"type": "sensor_status", "sensor_id": "s1", "required_status": "active"}]
        assert (
            evaluate_domain_of_validity(
                conditions, "all", {}, sensor_status={"s1": "offline"}
            )
            is False
        )

    # Test 7: identity confidence too low -> NOT_APPLICABLE
    def test_identity_confidence_low(self):
        conditions = [{"type": "identity_confidence", "min_confidence": 0.8}]
        assert evaluate_domain_of_validity(conditions, "all", {}, identity_confidence=0.5) is False

    # Test 7b: identity confidence sufficient -> applicable
    def test_identity_confidence_sufficient(self):
        conditions = [{"type": "identity_confidence", "min_confidence": 0.8}]
        assert evaluate_domain_of_validity(conditions, "all", {}, identity_confidence=0.9) is True

    # Test 8: composite AND all match -> applicable
    def test_composite_and_all_match(self):
        conditions = [
            {
                "type": "composite",
                "operator": "and",
                "sub_conditions": [
                    {"type": "state_range", "variable": "temp", "min": 0, "max": 200},
                    {"type": "state_range", "variable": "pressure", "min": 0, "max": 100},
                ],
            }
        ]
        state = {"temp": 50, "pressure": 30}
        assert evaluate_domain_of_validity(conditions, "all", state) is True

    # Test 9: composite AND one miss -> NOT_APPLICABLE
    def test_composite_and_one_miss(self):
        conditions = [
            {
                "type": "composite",
                "operator": "and",
                "sub_conditions": [
                    {"type": "state_range", "variable": "temp", "min": 0, "max": 200},
                    {"type": "state_range", "variable": "pressure", "min": 0, "max": 100},
                ],
            }
        ]
        state = {"temp": 50, "pressure": 150}  # pressure out of range
        assert evaluate_domain_of_validity(conditions, "all", state) is False

    # match_mode "any" -> at least one condition must match
    def test_match_mode_any(self):
        conditions = [
            {"type": "state_range", "variable": "temp", "min": 0, "max": 100},
            {"type": "state_range", "variable": "temp", "min": 200, "max": 300},
        ]
        # temp=250 is in second range but not first
        assert evaluate_domain_of_validity(conditions, "any", {"temp": 250}) is True

    # match_mode "all" -> all conditions must match
    def test_match_mode_all_fails(self):
        conditions = [
            {"type": "state_range", "variable": "temp", "min": 0, "max": 100},
            {"type": "state_range", "variable": "temp", "min": 200, "max": 300},
        ]
        # temp=50 is in first range but not second
        assert evaluate_domain_of_validity(conditions, "all", {"temp": 50}) is False

    # Exclusive bounds
    def test_state_range_exclusive_bounds(self):
        conditions = [{"type": "state_range", "variable": "x", "min": 0, "max": 100, "inclusive": False}]
        # Exactly on boundary should be excluded
        assert evaluate_domain_of_validity(conditions, "all", {"x": 100}) is False
        assert evaluate_domain_of_validity(conditions, "all", {"x": 0}) is False
        assert evaluate_domain_of_validity(conditions, "all", {"x": 50}) is True


# ── Full evaluator tests ───────────────────────────────────────────


class TestEvaluateConstraint:
    """Tests 1, 2, 3 — full evaluator with validation + domain."""

    # Test 1: temp=150, max=180 -> PASSED
    def test_temp_within_range_passed(self):
        card = _card(config={"variable": "temperature", "max": 180.0})
        result = evaluate_constraint(card, {"temperature": 150.0})
        assert result.status == ConstraintStatus.PASSED
        assert result.constraint_id == "c_temp"

    # Test 2: temp=190, max=180 -> FAILED
    def test_temp_over_max_failed(self):
        card = _card(config={"variable": "temperature", "max": 180.0})
        result = evaluate_constraint(card, {"temperature": 190.0})
        assert result.status == ConstraintStatus.FAILED

    # Test 3: temp=250, domain=[0,200] -> NOT_APPLICABLE
    def test_outside_domain_not_applicable(self):
        card = _card(
            config={"variable": "temperature", "max": 180.0},
            domain_conditions=[
                {"type": "state_range", "variable": "temperature", "min": 0, "max": 200}
            ],
        )
        result = evaluate_constraint(card, {"temperature": 250.0})
        assert result.status == ConstraintStatus.NOT_APPLICABLE

    # Test 4b: missing variable in validation -> UNCERTAIN
    def test_missing_validation_variable_uncertain(self):
        card = _card(config={"variable": "nonexistent", "max": 100.0})
        result = evaluate_constraint(card, {"temperature": 50.0})
        assert result.status == ConstraintStatus.UNCERTAIN

    # Test 5b: sensor offline but validation still runs (conservative)
    def test_sensor_unknown_still_evaluates(self):
        card = _card(
            config={"variable": "temperature", "max": 180.0},
            domain_conditions=[
                {"type": "sensor_status", "sensor_id": "s1", "required_status": "active"}
            ],
        )
        # No sensor_status -> sensor unknown -> still applicable -> evaluation proceeds
        result = evaluate_constraint(card, {"temperature": 150.0})
        assert result.status == ConstraintStatus.PASSED

    # Test 6: sensor active -> normal evaluation
    def test_sensor_active_normal_eval(self):
        card = _card(
            config={"variable": "temperature", "max": 180.0},
            domain_conditions=[
                {"type": "sensor_status", "sensor_id": "s1", "required_status": "active"}
            ],
        )
        result = evaluate_constraint(
            card, {"temperature": 150.0}, sensor_status={"s1": "active"}
        )
        assert result.status == ConstraintStatus.PASSED

    # Test with threshold_exceeded validator
    def test_threshold_exceeded_validator(self):
        card = _card(
            method="threshold_exceeded",
            config={"variable": "power", "threshold": 50.0},
        )
        result = evaluate_constraint(card, {"power": 60.0})
        assert result.status == ConstraintStatus.PASSED

    def test_threshold_exceeded_below_fails(self):
        card = _card(
            method="threshold_exceeded",
            config={"variable": "power", "threshold": 50.0},
        )
        result = evaluate_constraint(card, {"power": 30.0})
        assert result.status == ConstraintStatus.FAILED

    # Message content check
    def test_result_message_contains_id(self):
        card = _card(constraint_id="my_constraint")
        result = evaluate_constraint(card, {"temperature": 150.0})
        assert "my_constraint" in result.message

    # Criticality propagation
    def test_criticality_propagated(self):
        card = _card(scenario_criticality="safety_critical")
        result = evaluate_constraint(card, {"temperature": 150.0})
        assert result.criticality.value == "safety_critical"
