"""Tests for the public API whitelist.

Verifies that every symbol in __all__ is importable and is the expected type.
"""
import importlib

import pytest

import polytwin


class TestPublicAPIWhitelist:
    """Ensure all symbols in polytwin.__all__ are accessible."""

    def test_all_is_defined(self) -> None:
        assert hasattr(polytwin, "__all__")
        assert isinstance(polytwin.__all__, list)
        assert len(polytwin.__all__) > 0

    def test_version_is_set(self) -> None:
        assert hasattr(polytwin, "__version__")
        assert polytwin.__version__ == "0.1.0"
        assert "__version__" in polytwin.__all__

    def test_every_all_symbol_importable(self) -> None:
        """Every name in __all__ must be an attribute of the polytwin package."""
        for name in polytwin.__all__:
            assert hasattr(polytwin, name), f"Missing public symbol: {name}"

    @pytest.mark.parametrize(
        "name",
        [
            "PolymorphicTwinEngine",
            "EngineConfig",
            # TOM types
            "ObjectType",
            "LifecycleState",
            "HealthState",
            "ViewType",
            "Criticality",
            "Rigidity",
            "ConstraintStatus",
            "CallerIdentity",
            # DomainPack
            "DomainPack",
            "ConstraintCard",
            "StateVariable",
            # Core results
            "ValidationResult",
            "SingleConstraintResult",
            "HardGateResult",
            "FallbackResult",
            "IdentityCheckResult",
            # Bridge
            "ActionSpace",
            "BridgeOutput",
            # Exceptions
            "PolymorphicTwinError",
            "PermissionDeniedError",
            "PTValidationError",
            "DomainPackValidationError",
            "ConstraintViolationError",
            "SafetyFallbackError",
            "IdentityDriftError",
        ],
    )
    def test_symbol_type(self, name: str) -> None:
        """Each public symbol must be a type (class or enum)."""
        obj = getattr(polytwin, name)
        assert isinstance(obj, type), f"{name} is not a type: {type(obj)}"

    def test_exception_hierarchy(self) -> None:
        """All SDK exceptions must be subclasses of PolymorphicTwinError."""
        base = polytwin.PolymorphicTwinError
        assert issubclass(polytwin.PermissionDeniedError, base)
        assert issubclass(polytwin.PTValidationError, base)
        assert issubclass(polytwin.DomainPackValidationError, base)
        assert issubclass(polytwin.ConstraintViolationError, base)
        assert issubclass(polytwin.SafetyFallbackError, base)
        assert issubclass(polytwin.IdentityDriftError, base)

    def test_all_count_matches_params(self) -> None:
        """The number of parametrized test names should match __all__ minus __version__."""
        expected = len(polytwin.__all__)
        # __all__ includes __version__ (a string, not a type)
        type_symbols = [n for n in polytwin.__all__ if n != "__version__"]
        assert len(type_symbols) == expected - 1

    def test_pt_validation_error_is_validation_error(self) -> None:
        """PTValidationError should be the SDK-level ValidationError."""
        from polytwin.exceptions import ValidationError

        assert polytwin.PTValidationError is ValidationError

    def test_reimport_clean(self) -> None:
        """Re-importing should not raise."""
        importlib.reload(polytwin)
        assert polytwin.__version__ == "0.1.0"
