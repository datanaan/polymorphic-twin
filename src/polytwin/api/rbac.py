"""Role-Based Access Control for the Polymorphic-Twin API.

Defines a permission matrix mapping five roles to fourteen fine-grained
actions across the TOM, Core, Lab, Bridge, Audit, and DomainPack domains.
"""
from __future__ import annotations

# ── Permission sets per role ──────────────────────────────────────────

PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "tom:read", "tom:write", "tom:delete",
        "core:validate", "core:hardgate", "core:fallback", "core:certify",
        "lab:explore", "lab:submit",
        "bridge:action_space", "bridge:decide",
        "audit:read", "audit:export",
        "domainpack:manage",
    },
    "operator": {
        "tom:read", "tom:write",
        "core:validate",
        "bridge:action_space", "bridge:decide",
        "audit:read",
    },
    "viewer": {
        "tom:read",
        "audit:read",
    },
    "lab_operator": {
        "tom:read",
        "lab:explore", "lab:submit",
        "core:validate",  # for prescreen only
    },
    "bridge_operator": {
        "tom:read",
        "bridge:action_space", "bridge:decide",
        "core:validate",
    },
}

# ── All known actions (derived from the matrix) ───────────────────────

ALL_ACTIONS: set[str] = set()
for _perms in PERMISSIONS.values():
    ALL_ACTIONS |= _perms


def check_permission(role: str, action: str) -> bool:
    """Check whether a role is authorised for a given action.

    Args:
        role: One of admin, operator, viewer, lab_operator, bridge_operator.
        action: A dotted action string, e.g. ``"tom:read"``.

    Returns:
        True if the role has the permission, False otherwise.
    """
    return action in PERMISSIONS.get(role, set())


def require_permission(role: str, action: str) -> None:
    """Assert that a role has permission for an action.

    Args:
        role: Role identifier.
        action: Dotted action string.

    Raises:
        PermissionDeniedError: When the role lacks the required action.
    """
    from polytwin.exceptions import PermissionDeniedError

    if not check_permission(role, action):
        raise PermissionDeniedError(
            f"Role '{role}' does not have permission '{action}'"
        )
