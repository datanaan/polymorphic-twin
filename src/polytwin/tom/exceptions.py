"""TOM-layer exceptions.

Defines exceptions raised by the TwinObject facade and store
when access-control or permission rules are violated.
"""

from __future__ import annotations


class PermissionDeniedError(Exception):
    """Raised when a caller attempts an operation they are not authorized for.

    Attributes:
        caller: Component identifier of the caller (e.g. "core_runtime").
        view_type: The view type or operation that was denied.
        reason: Human-readable explanation of why access was denied.
    """

    def __init__(self, caller: str, view_type: str, reason: str) -> None:
        self.caller = caller
        self.view_type = view_type
        self.reason = reason
        super().__init__(
            f"Caller '{caller}' denied access to '{view_type}': {reason}"
        )
