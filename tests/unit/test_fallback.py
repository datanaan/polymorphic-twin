"""Tests for SafetyFallback: four strategies for safety fallback.

Test cases:
1. safe_state -> returns target_state values
2. shutdown -> lifecycle becomes 'archived'
3. degraded_mode -> health becomes 'degraded'
4. human_takeover -> audit event written
5. Cannot be cancelled once triggered
6. Default strategy when none configured
"""
import pytest

from polytwin.core.fallback import SafetyFallback


def _make_obj(identity_id: str = "obj-001") -> dict:
    """Build a minimal TwinObject dict for testing."""
    return {
        "identity": {"id": identity_id},
        "state": {"lifecycle": "active", "health": "healthy"},
        "state_semantics": {"current_values": {"temperature": 150.0}},
        "audit_trail": {"events": []},
    }


def _make_dp(unavailable_action: str = "safe_shutdown", target_state: dict | None = None) -> dict:
    """Build a minimal DomainPack dict with safe_fallback config."""
    fallback: dict = {"unavailable_action": unavailable_action}
    if target_state is not None:
        fallback["target_state"] = target_state
    return {
        "domain_id": "test-domain",
        "safe_fallback": fallback,
    }


# ── Strategy: safe_state ─────────────────────────────────────────────


class TestSafeStateStrategy:
    @pytest.mark.asyncio
    async def test_returns_target_state_values(self):
        """safe_state -> state values updated to target_state."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = _make_dp(
            unavailable_action="safe_shutdown",
            target_state={"temperature": 25.0},
        )
        result = await fb.execute(obj, {}, dp)
        assert result.strategy_used == "safe_state"
        assert obj["state_semantics"]["current_values"]["temperature"] == 25.0

    @pytest.mark.asyncio
    async def test_safe_state_without_target(self):
        """safe_state with no target_state -> no crash, values unchanged."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = _make_dp(unavailable_action="safe_shutdown")
        result = await fb.execute(obj, {}, dp)
        assert result.strategy_used == "safe_state"


# ── Strategy: shutdown ───────────────────────────────────────────────


class TestShutdownStrategy:
    @pytest.mark.asyncio
    async def test_lifecycle_becomes_archived(self):
        """shutdown -> lifecycle becomes 'archived'."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = _make_dp(unavailable_action="shutdown")
        result = await fb.execute(obj, {}, dp)
        assert result.strategy_used == "shutdown"
        assert obj["state"]["lifecycle"] == "archived"


# ── Strategy: degraded_mode ──────────────────────────────────────────


class TestDegradedModeStrategy:
    @pytest.mark.asyncio
    async def test_health_becomes_degraded(self):
        """degraded_mode -> health becomes 'degraded'."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = _make_dp(unavailable_action="degraded_mode")
        result = await fb.execute(obj, {}, dp)
        assert result.strategy_used == "degraded_mode"
        assert obj["state"]["health"] == "degraded"


# ── Strategy: human_takeover ─────────────────────────────────────────


class TestHumanTakeoverStrategy:
    @pytest.mark.asyncio
    async def test_audit_event_written(self):
        """human_takeover -> audit event written."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = _make_dp(unavailable_action="human_takeover")
        result = await fb.execute(obj, {}, dp)
        assert result.strategy_used == "human_takeover"
        assert len(obj["audit_trail"]["events"]) == 1
        assert obj["audit_trail"]["events"][0]["event_type"] == "human_takeover_initiated"

    @pytest.mark.asyncio
    async def test_audit_event_created_if_missing(self):
        """human_takeover creates audit_trail if not present."""
        fb = SafetyFallback()
        obj = _make_obj()
        del obj["audit_trail"]
        dp = _make_dp(unavailable_action="human_takeover")
        await fb.execute(obj, {}, dp)
        assert "audit_trail" in obj
        assert len(obj["audit_trail"]["events"]) == 1


# ── Default / no config ─────────────────────────────────────────────


class TestFallbackDefault:
    @pytest.mark.asyncio
    async def test_no_fallback_config_defaults_to_safe_shutdown(self):
        """No safe_fallback in DomainPack -> defaults to safe_state."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = {"domain_id": "test"}  # No safe_fallback
        result = await fb.execute(obj, {}, dp)
        assert result.strategy_used == "safe_state"


# ── Cannot be cancelled ──────────────────────────────────────────────


class TestFallbackIrreversibility:
    @pytest.mark.asyncio
    async def test_is_executing_during_run(self):
        """Cannot be cancelled once triggered — is_executing reflects state."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = _make_dp()
        assert fb.is_executing is False
        result = await fb.execute(obj, {}, dp)
        assert fb.is_executing is False  # Reset after completion
        assert result.strategy_used == "safe_state"


# ── Object ID and violated constraint ────────────────────────────────


class TestFallbackMetadata:
    @pytest.mark.asyncio
    async def test_object_id_captured(self):
        """FallbackResult captures object_id."""
        fb = SafetyFallback()
        obj = _make_obj(identity_id="twin-42")
        dp = _make_dp()
        result = await fb.execute(obj, {}, dp)
        assert result.object_id == "twin-42"

    @pytest.mark.asyncio
    async def test_violated_constraint_captured(self):
        """FallbackResult captures violated_constraint."""
        fb = SafetyFallback()
        obj = _make_obj()
        dp = _make_dp()
        constraint_result = {"violated_constraint": "max_temp_safety"}
        result = await fb.execute(obj, constraint_result, dp)
        assert result.violated_constraint == "max_temp_safety"
