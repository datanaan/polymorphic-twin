"""Bridge orchestrator: stateless main entry point for the decision interface.

The BridgeOrchestrator generates structured action spaces from TwinObject
view data. Each call produces a fresh BridgeOutput with a unique ID.
No state persists between calls.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from polytwin.bridge.action_space import ActionSpaceBuilder
from polytwin.bridge.types import BridgeOutput

# Default validity window for generated outputs (in minutes)
_DEFAULT_VALIDITY_MINUTES = 5


class BridgeOrchestrator:
    """Stateless orchestrator for the Bridge decision interface.

    Generates BridgeOutput instances from view data and optional
    DomainPack configuration. Each invocation creates a new output
    with a fresh UUID -- no persistent state is maintained.
    """

    def __init__(
        self,
        action_builder: ActionSpaceBuilder | None = None,
        validity_minutes: int = _DEFAULT_VALIDITY_MINUTES,
    ) -> None:
        self._builder = action_builder or ActionSpaceBuilder()
        self._validity_minutes = validity_minutes

    async def generate_action_space(
        self,
        view_data: dict,
        domain_pack: dict | None = None,
    ) -> BridgeOutput:
        """Generate action space from view data. Stateless -- no persistent state.

        Args:
            view_data: BridgeDecisionView-projected TwinObject data.
            domain_pack: Optional DomainPack configuration dictionary.

        Returns:
            BridgeOutput with a fresh UUID, computed validity window,
            and version tag derived from the view data.
        """
        action_space = self._builder.build(view_data, domain_pack)

        now = datetime.now(UTC)
        valid_until = now + timedelta(minutes=self._validity_minutes)
        version_tag = self._compute_version_tag(view_data, domain_pack)

        return BridgeOutput(
            output_id=str(uuid.uuid4()),
            object_id=view_data.get("twin_object_id", ""),
            action_space=action_space,
            valid_until=valid_until.isoformat(),
            version_tag=version_tag,
            created_at=now.isoformat(),
        )

    @staticmethod
    def _compute_version_tag(
        view_data: dict,
        domain_pack: dict | None = None,
    ) -> str:
        """Compute a version tag from view data and domain pack.

        The version tag encodes the state of the view data and
        domain pack version so that validity checks can detect
        when the underlying data has changed.

        Args:
            view_data: The view data dictionary.
            domain_pack: Optional domain pack configuration.

        Returns:
            A string version tag in the format "v:<view_hash>:<dp_version>".
        """
        # Hash the constraint state to detect changes
        constraint_state = view_data.get("constraint_state", {})
        constraint_summary = view_data.get("constraint_summary", [])

        # Simple deterministic hash of constraint results
        parts: list[str] = []
        for entry in constraint_summary:
            cid = entry.get("constraint_id", "")
            status = entry.get("status", "")
            status_val = status.value if hasattr(status, "value") else str(status)
            parts.append(f"{cid}={status_val}")

        if not parts:
            # Use active constraints list as fallback
            active = constraint_state.get("active_constraints", [])
            parts = list(active)

        view_hash = hash(",".join(parts)) if parts else 0
        view_hash_str = f"{abs(view_hash):08x}"

        dp_version = ""
        if domain_pack:
            dp_version = domain_pack.get("domain_version", "")

        return f"v:{view_hash_str}:{dp_version}"
