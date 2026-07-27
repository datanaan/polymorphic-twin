# tests/unit/test_domainpack_validation.py
"""Test that validate_domainpack.py correctly accepts valid configs
and rejects invalid ones for specific reasons."""
from pathlib import Path

# Import the validation function directly
from scripts.validate_domainpack import validate_domainpack

CONFIGS = Path("configs/examples")


class TestValidDomainPack:
    def test_minimal_domain_pack_passes(self):
        errors = validate_domainpack(CONFIGS / "minimal-domain-pack.yaml")
        assert errors == [], f"Unexpected errors: {errors}"


class TestRigidityCriticalityViolation:
    def test_soft_with_safety_critical_rejected(self):
        errors = validate_domainpack(CONFIGS / "invalid-soft-safety.yaml")
        assert len(errors) > 0
        error_messages = [e.message for e in errors]
        assert any("safety_critical" in m and "soft" in m for m in error_messages), (
            f"Expected rigidity-criticality violation, got: {error_messages}"
        )


class TestMissingFallback:
    def test_missing_target_state_rejected(self):
        errors = validate_domainpack(CONFIGS / "invalid-missing-fallback.yaml")
        assert len(errors) > 0
        error_messages = [e.message for e in errors]
        assert any("target_state" in m for m in error_messages), (
            f"Expected missing target_state error, got: {error_messages}"
        )


class TestUndefinedVariableReference:
    def test_undefined_variable_in_domain_of_validity_rejected(self):
        errors = validate_domainpack(CONFIGS / "invalid-undefined-variable.yaml")
        assert len(errors) > 0
        error_messages = [e.message for e in errors]
        # Should catch both: domain_of_validity ref and validation config ref
        undefined_refs = [m for m in error_messages if "undefined state variable" in m]
        assert len(undefined_refs) >= 1, (
            f"Expected undefined variable references, got: {error_messages}"
        )
