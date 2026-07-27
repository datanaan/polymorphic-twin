"""SafetyFallback: irreversible safety fallback execution.

Four strategies for emergency retreat when constraints are violated.
Once triggered, the fallback cannot be cancelled.

Strategies:
- safe_state: retreat to configured target_state values
- shutdown: set lifecycle to 'archived'
- degraded_mode: set health to 'degraded'
- human_takeover: write audit event for human intervention
"""
from __future__ import annotations

from polytwin.core.types import FallbackResult


class SafetyFallback:
    """Execute safety fallback strategies.

    Once a fallback is triggered, it cannot be interrupted.  The
    strategy is determined by the DomainPack's safe_fallback config,
    falling back to ``safe_shutdown`` if none is configured.
    """

    def __init__(self) -> None:
        self._executing = False

    async def execute(
        self,
        obj: dict,
        constraint_result: dict,
        domain_pack: dict,
    ) -> FallbackResult:
        """Execute safety fallback.  Cannot be interrupted once started.

        Args:
            obj: TwinObject representation (dict with identity, state, etc.).
            constraint_result: The validation result that triggered fallback.
            domain_pack: DomainPack configuration dict.

        Returns:
            FallbackResult recording what was done.
        """
        self._executing = True
        try:
            fallback_config = domain_pack.get("safe_fallback")
            strategy = (
                fallback_config.get("unavailable_action", "safe_shutdown")
                if fallback_config
                else "safe_shutdown"
            )

            violated = ""
            if constraint_result:
                violated = constraint_result.get("violated_constraint", "")

            object_id = (
                obj.get("identity", {}).get("id", "")
                if isinstance(obj.get("identity"), dict)
                else str(obj.get("identity", ""))
            )

            if strategy == "safe_shutdown" or strategy == "safe_state":
                result = await self._safe_state(obj, fallback_config)
            elif strategy == "shutdown":
                result = await self._shutdown(obj)
            elif strategy == "degraded_mode":
                result = await self._degraded(obj)
            elif strategy == "human_takeover":
                result = await self._human_takeover(obj)
            else:
                # Unknown strategy — fall back to safe_state
                result = await self._safe_state(obj, fallback_config)

            result.object_id = object_id
            result.violated_constraint = violated
            return result
        finally:
            self._executing = False

    @property
    def is_executing(self) -> bool:
        """Whether a fallback is currently in progress."""
        return self._executing

    async def _safe_state(self, obj: dict, fallback_config: dict | None) -> FallbackResult:
        """Retreat to configured target_state values."""
        target_state: dict = {}
        if fallback_config:
            target_state = fallback_config.get("target_state", {})

        # Apply target state values to the object
        if target_state and "state_semantics" in obj:
            state_sem = obj["state_semantics"]
            if isinstance(state_sem, dict):
                current = state_sem.get("current_values", {})
                current.update(target_state)
                state_sem["current_values"] = current

        return FallbackResult(
            strategy_used="safe_state",
            object_id="",
            violated_constraint="",
        )

    async def _shutdown(self, obj: dict) -> FallbackResult:
        """Set lifecycle to 'archived'."""
        state = obj.get("state", {})
        if isinstance(state, dict):
            state["lifecycle"] = "archived"
        else:
            obj["state"] = {"lifecycle": "archived"}

        return FallbackResult(
            strategy_used="shutdown",
            object_id="",
            violated_constraint="",
        )

    async def _degraded(self, obj: dict) -> FallbackResult:
        """Set health to 'degraded'."""
        state = obj.get("state", {})
        if isinstance(state, dict):
            state["health"] = "degraded"
        else:
            obj["state"] = {"health": "degraded"}

        return FallbackResult(
            strategy_used="degraded_mode",
            object_id="",
            violated_constraint="",
        )

    async def _human_takeover(self, obj: dict) -> FallbackResult:
        """Write audit event for human intervention."""
        audit_trail = obj.get("audit_trail")
        if audit_trail is None:
            obj["audit_trail"] = {"events": []}
            audit_trail = obj["audit_trail"]

        events = audit_trail.get("events", []) if isinstance(audit_trail, dict) else []
        events.append({
            "event_type": "human_takeover_initiated",
            "actor": "safety_fallback",
            "detail": {"reason": "safety_fallback_triggered"},
        })
        if isinstance(audit_trail, dict):
            audit_trail["events"] = events

        return FallbackResult(
            strategy_used="human_takeover",
            object_id="",
            violated_constraint="",
        )
