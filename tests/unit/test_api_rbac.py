"""Tests for the RBAC permission matrix."""
from __future__ import annotations

import pytest

from polytwin.api.rbac import (
    ALL_ACTIONS,
    PERMISSIONS,
    check_permission,
    require_permission,
)
from polytwin.exceptions import PermissionDeniedError


class TestPermissionMatrix:
    """Validate the shape and contents of the 5-role x 14-action matrix."""

    def test_five_roles_defined(self) -> None:
        assert set(PERMISSIONS.keys()) == {
            "admin",
            "operator",
            "viewer",
            "lab_operator",
            "bridge_operator",
        }

    def test_admin_has_all_14_permissions(self) -> None:
        assert len(PERMISSIONS["admin"]) == 14

    def test_admin_permissions_are_superset(self) -> None:
        """Every other role's permissions are a subset of admin."""
        for role, perms in PERMISSIONS.items():
            if role != "admin":
                assert perms <= PERMISSIONS["admin"]

    def test_viewer_has_two_permissions(self) -> None:
        assert PERMISSIONS["viewer"] == {"tom:read", "audit:read"}

    def test_all_actions_has_14_entries(self) -> None:
        assert len(ALL_ACTIONS) == 14


class TestCheckPermission:
    """check_permission returns correct boolean for role/action combos."""

    def test_admin_has_tom_write(self) -> None:
        assert check_permission("admin", "tom:write") is True

    def test_viewer_cannot_tom_write(self) -> None:
        assert check_permission("viewer", "tom:write") is False

    def test_lab_operator_has_lab_explore(self) -> None:
        assert check_permission("lab_operator", "lab:explore") is True

    def test_lab_operator_has_lab_submit(self) -> None:
        assert check_permission("lab_operator", "lab:submit") is True

    def test_lab_operator_has_core_validate(self) -> None:
        assert check_permission("lab_operator", "core:validate") is True

    def test_bridge_operator_cannot_lab_submit(self) -> None:
        assert check_permission("bridge_operator", "lab:submit") is False

    def test_bridge_operator_has_bridge_decide(self) -> None:
        assert check_permission("bridge_operator", "bridge:decide") is True

    def test_unknown_role_has_no_permissions(self) -> None:
        assert check_permission("hacker", "tom:read") is False

    def test_operator_has_audit_read(self) -> None:
        assert check_permission("operator", "audit:read") is True

    def test_operator_cannot_domainpack_manage(self) -> None:
        assert check_permission("operator", "domainpack:manage") is False


class TestRequirePermission:
    """require_permission raises PermissionDeniedError on denial."""

    def test_allowed_action_does_not_raise(self) -> None:
        require_permission("admin", "tom:write")  # should not raise

    def test_denied_action_raises_permission_denied(self) -> None:
        with pytest.raises(PermissionDeniedError):
            require_permission("viewer", "tom:write")

    def test_unknown_role_raises_permission_denied(self) -> None:
        with pytest.raises(PermissionDeniedError):
            require_permission("unknown", "tom:read")

    def test_error_message_contains_role_and_action(self) -> None:
        with pytest.raises(PermissionDeniedError, match="viewer.*tom:write"):
            require_permission("viewer", "tom:write")
