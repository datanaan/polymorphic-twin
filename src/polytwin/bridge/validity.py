"""Validity manager for Bridge outputs.

Tracks output validity based on version tag changes. When a version
tag changes (e.g. due to constraint state update or DomainPack version
change), all outputs associated with the old version are invalidated.
"""
from __future__ import annotations

from polytwin.bridge.types import BridgeOutput


class ValidityManager:
    """Tracks BridgeOutput validity by version tag.

    Registers outputs and provides fast lookup to check whether an
    output is still valid against the current version tag.

    Note: This manager is NOT part of the stateless Bridge contract
    per se -- it is a utility that consumers use to track whether
    previously generated outputs are still fresh. The manager itself
    is stateful but the BridgeOrchestrator remains stateless.
    """

    def __init__(self) -> None:
        self._outputs: dict[str, BridgeOutput] = {}

    def register(self, output: BridgeOutput) -> None:
        """Register a BridgeOutput for validity tracking.

        Args:
            output: The BridgeOutput to register.
        """
        self._outputs[output.output_id] = output

    def is_valid(self, output_id: str, current_version: str) -> bool:
        """Check whether a registered output is still valid.

        An output is valid if:
        1. It has been registered (exists in the store).
        2. Its version_tag matches the current_version.

        Args:
            output_id: The output to check.
            current_version: The current version tag to compare against.

        Returns:
            True if the output exists and its version matches.
        """
        output = self._outputs.get(output_id)
        if output is None:
            return False
        return output.version_tag == current_version

    def invalidate_version(self, version_tag: str) -> list[str]:
        """Invalidate all outputs for a given version tag.

        Args:
            version_tag: The version tag to invalidate.

        Returns:
            List of output IDs that were invalidated.
        """
        invalidated: list[str] = []
        for oid, output in list(self._outputs.items()):
            if output.version_tag == version_tag:
                invalidated.append(oid)
                del self._outputs[oid]
        return invalidated

    def get(self, output_id: str) -> BridgeOutput | None:
        """Retrieve a registered output by ID.

        Args:
            output_id: The output ID to look up.

        Returns:
            The BridgeOutput if registered, None otherwise.
        """
        return self._outputs.get(output_id)

    def clear(self) -> None:
        """Remove all registered outputs."""
        self._outputs.clear()

    @property
    def registered_count(self) -> int:
        """Number of currently registered outputs."""
        return len(self._outputs)
