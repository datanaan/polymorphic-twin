"""Tests for the unified exception hierarchy."""

import pytest

from polytwin.exceptions import (
    ConstraintViolationError,
    DomainPackValidationError,
    IdentityDriftError,
    PermissionDeniedError,
    PolymorphicTwinError,
    SafetyFallbackError,
    ValidationError,
)


class TestExceptionHierarchy:
    """All SDK exceptions inherit from PolymorphicTwinError."""

    def test_base_exception_inherits_from_exception(self) -> None:
        assert issubclass(PolymorphicTwinError, Exception)

    @pytest.mark.parametrize(
        "exc_cls",
        [
            PermissionDeniedError,
            ValidationError,
            DomainPackValidationError,
            ConstraintViolationError,
            SafetyFallbackError,
            IdentityDriftError,
        ],
    )
    def test_subclass_inherits_from_base(self, exc_cls: type) -> None:
        assert issubclass(exc_cls, PolymorphicTwinError)

    @pytest.mark.parametrize(
        "exc_cls",
        [
            PermissionDeniedError,
            ValidationError,
            DomainPackValidationError,
            ConstraintViolationError,
            SafetyFallbackError,
            IdentityDriftError,
        ],
    )
    def test_subclass_inherits_from_exception(self, exc_cls: type) -> None:
        assert issubclass(exc_cls, Exception)


class TestExceptionInstantiation:
    """Each exception can be instantiated with a message."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            PolymorphicTwinError,
            PermissionDeniedError,
            ValidationError,
            DomainPackValidationError,
            ConstraintViolationError,
            SafetyFallbackError,
            IdentityDriftError,
        ],
    )
    def test_instantiation_with_message(self, exc_cls: type) -> None:
        exc = exc_cls("test message")
        assert str(exc) == "test message"
        assert isinstance(exc, PolymorphicTwinError)

    @pytest.mark.parametrize(
        "exc_cls",
        [
            PolymorphicTwinError,
            PermissionDeniedError,
            ValidationError,
            DomainPackValidationError,
            ConstraintViolationError,
            SafetyFallbackError,
            IdentityDriftError,
        ],
    )
    def test_instantiation_without_message(self, exc_cls: type) -> None:
        exc = exc_cls()
        assert isinstance(exc, PolymorphicTwinError)


class TestExceptionCatching:
    """Catching PolymorphicTwinError catches all sub-exceptions."""

    def test_catch_base_catches_validation_error(self) -> None:
        with pytest.raises(PolymorphicTwinError):
            raise ValidationError("data invalid")

    def test_catch_base_catches_constraint_violation(self) -> None:
        with pytest.raises(PolymorphicTwinError):
            raise ConstraintViolationError("constraint failed")

    def test_catch_base_catches_safety_fallback(self) -> None:
        with pytest.raises(PolymorphicTwinError):
            raise SafetyFallbackError("fallback triggered")

    def test_catch_base_catches_identity_drift(self) -> None:
        with pytest.raises(PolymorphicTwinError):
            raise IdentityDriftError("drift exceeded")

    def test_catch_base_catches_permission_denied(self) -> None:
        with pytest.raises(PolymorphicTwinError):
            raise PermissionDeniedError("access denied")

    def test_catch_base_catches_domain_pack_validation(self) -> None:
        with pytest.raises(PolymorphicTwinError):
            raise DomainPackValidationError("bad config")

    def test_catch_exception_catches_base(self) -> None:
        with pytest.raises(PolymorphicTwinError):
            raise PolymorphicTwinError("base error")


class TestExceptionSpecificity:
    """Specific exceptions are distinct types."""

    def test_validation_error_not_constraint_violation(self) -> None:
        assert ValidationError is not ConstraintViolationError

    def test_safety_fallback_not_identity_drift(self) -> None:
        assert SafetyFallbackError is not IdentityDriftError

    def test_permission_denied_not_domain_pack_validation(self) -> None:
        assert PermissionDeniedError is not DomainPackValidationError
