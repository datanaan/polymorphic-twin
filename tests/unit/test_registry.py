"""Tests for the validation function registry.

Test cases:
1. range_check within range -> PASSED
2. range_check over max -> FAILED
3. range_check under min -> FAILED
4. threshold_exceeded below threshold -> FAILED
5. threshold_exceeded above threshold -> PASSED
6. unknown validator -> UNCERTAIN
"""


from polytwin.core.rules.registry import (
    default_validator,
    enum_membership,
    get_validator,
    range_check,
    register_validator,
    threshold_exceeded,
)
from polytwin.tom.types import ConstraintStatus

# ── range_check ─────────────────────────────────────────────────────


class TestRangeCheck:
    # Test 1: within range -> PASSED
    def test_within_range(self):
        status = range_check({"temperature": 150.0}, {"variable": "temperature", "max": 180.0})
        assert status == ConstraintStatus.PASSED

    # Test 2: over max -> FAILED
    def test_over_max(self):
        status = range_check({"temperature": 190.0}, {"variable": "temperature", "max": 180.0})
        assert status == ConstraintStatus.FAILED

    # Test 3: under min -> FAILED
    def test_under_min(self):
        status = range_check({"temperature": -5.0}, {"variable": "temperature", "min": 0.0})
        assert status == ConstraintStatus.FAILED

    def test_within_min_max(self):
        status = range_check(
            {"temperature": 50.0},
            {"variable": "temperature", "min": 0.0, "max": 100.0},
        )
        assert status == ConstraintStatus.PASSED

    def test_exclusive_over_max(self):
        status = range_check(
            {"temperature": 180.0},
            {"variable": "temperature", "max": 180.0, "inclusive": False},
        )
        assert status == ConstraintStatus.FAILED

    def test_exclusive_at_boundary_minus(self):
        status = range_check(
            {"temperature": 179.9},
            {"variable": "temperature", "max": 180.0, "inclusive": False},
        )
        assert status == ConstraintStatus.PASSED

    def test_missing_variable_uncertain(self):
        status = range_check({}, {"variable": "temperature", "max": 180.0})
        assert status == ConstraintStatus.UNCERTAIN

    def test_no_bounds_always_passes(self):
        status = range_check({"temperature": 9999.0}, {"variable": "temperature"})
        assert status == ConstraintStatus.PASSED


# ── threshold_exceeded ──────────────────────────────────────────────


class TestThresholdExceeded:
    # Test 4: below threshold -> FAILED
    def test_below_threshold(self):
        status = threshold_exceeded(
            {"power": 30.0}, {"variable": "power", "threshold": 50.0}
        )
        assert status == ConstraintStatus.FAILED

    # Test 5: above threshold -> PASSED
    def test_above_threshold(self):
        status = threshold_exceeded(
            {"power": 60.0}, {"variable": "power", "threshold": 50.0}
        )
        assert status == ConstraintStatus.PASSED

    def test_at_threshold(self):
        status = threshold_exceeded(
            {"power": 50.0}, {"variable": "power", "threshold": 50.0}
        )
        assert status == ConstraintStatus.PASSED

    def test_missing_variable_uncertain(self):
        status = threshold_exceeded({}, {"variable": "power", "threshold": 50.0})
        assert status == ConstraintStatus.UNCERTAIN

    def test_min_key_as_threshold(self):
        status = threshold_exceeded(
            {"power": 30.0}, {"variable": "power", "min": 50.0}
        )
        assert status == ConstraintStatus.FAILED


# ── enum_membership ─────────────────────────────────────────────────


class TestEnumMembership:
    def test_always_passes(self):
        status = enum_membership({}, {})
        assert status == ConstraintStatus.PASSED


# ── default_validator ───────────────────────────────────────────────


class TestDefaultValidator:
    # Test 6: unknown validator -> UNCERTAIN
    def test_unknown_validator_returns_uncertain(self):
        fn = get_validator("nonexistent_method_xyz")
        status = fn({"x": 1.0}, {"variable": "x"})
        assert status == ConstraintStatus.UNCERTAIN

    def test_default_validator_uncertain(self):
        status = default_validator({"x": 1.0}, {})
        assert status == ConstraintStatus.UNCERTAIN


# ── Registry lookup ─────────────────────────────────────────────────


class TestRegistryLookup:
    def test_range_check_registered(self):
        fn = get_validator("range_check")
        assert fn is range_check

    def test_threshold_exceeded_registered(self):
        fn = get_validator("threshold_exceeded")
        assert fn is threshold_exceeded

    def test_enum_membership_registered(self):
        fn = get_validator("enum_membership")
        assert fn is enum_membership

    def test_register_custom_validator(self):
        def custom_check(state_values, config):
            return ConstraintStatus.PASSED

        register_validator("custom_test", custom_check)
        fn = get_validator("custom_test")
        assert fn is custom_check
        status = fn({}, {})
        assert status == ConstraintStatus.PASSED
