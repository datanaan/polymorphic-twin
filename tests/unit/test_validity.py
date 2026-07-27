"""Tests for the ValidityManager.

Key tests:
1. Output valid with matching version
2. Output invalid after version change
3. Invalidate version removes all matching outputs
4. DomainPack version change invalidates outputs
5. Unregistered outputs are invalid
"""
import pytest

from polytwin.bridge.types import ActionSpace, BridgeOutput
from polytwin.bridge.validity import ValidityManager


@pytest.fixture
def manager():
    return ValidityManager()


def _make_output(output_id: str = "out-1", version_tag: str = "v:abc:1.0") -> BridgeOutput:
    return BridgeOutput(
        output_id=output_id,
        object_id="obj-1",
        action_space=ActionSpace(),
        version_tag=version_tag,
        created_at="2026-01-01T00:00:00+00:00",
        valid_until="2026-01-01T00:05:00+00:00",
    )


class TestRegistration:
    def test_register_output(self, manager):
        output = _make_output()
        manager.register(output)
        assert manager.registered_count == 1

    def test_register_multiple_outputs(self, manager):
        manager.register(_make_output("out-1", "v:abc:1.0"))
        manager.register(_make_output("out-2", "v:abc:1.0"))
        manager.register(_make_output("out-3", "v:def:2.0"))
        assert manager.registered_count == 3

    def test_clear_removes_all(self, manager):
        manager.register(_make_output("out-1", "v:abc:1.0"))
        manager.register(_make_output("out-2", "v:def:2.0"))
        manager.clear()
        assert manager.registered_count == 0


class TestValidity:
    def test_valid_with_matching_version(self, manager):
        output = _make_output(version_tag="v:abc:1.0")
        manager.register(output)
        assert manager.is_valid("out-1", "v:abc:1.0") is True

    def test_invalid_with_different_version(self, manager):
        output = _make_output(version_tag="v:abc:1.0")
        manager.register(output)
        assert manager.is_valid("out-1", "v:abc:2.0") is False

    def test_unregistered_output_is_invalid(self, manager):
        assert manager.is_valid("nonexistent", "v:abc:1.0") is False

    def test_output_valid_only_for_its_version(self, manager):
        manager.register(_make_output("out-1", "v:aaa:1.0"))
        manager.register(_make_output("out-2", "v:bbb:1.0"))
        assert manager.is_valid("out-1", "v:aaa:1.0") is True
        assert manager.is_valid("out-2", "v:bbb:1.0") is True
        assert manager.is_valid("out-1", "v:bbb:1.0") is False
        assert manager.is_valid("out-2", "v:aaa:1.0") is False


class TestInvalidateVersion:
    def test_invalidate_removes_matching(self, manager):
        manager.register(_make_output("out-1", "v:abc:1.0"))
        manager.register(_make_output("out-2", "v:abc:1.0"))
        manager.register(_make_output("out-3", "v:def:2.0"))

        invalidated = manager.invalidate_version("v:abc:1.0")
        assert len(invalidated) == 2
        assert "out-1" in invalidated
        assert "out-2" in invalidated
        assert manager.registered_count == 1

    def test_invalidate_preserves_other_versions(self, manager):
        manager.register(_make_output("out-1", "v:abc:1.0"))
        manager.register(_make_output("out-2", "v:def:2.0"))

        manager.invalidate_version("v:abc:1.0")
        assert manager.registered_count == 1
        assert manager.is_valid("out-2", "v:def:2.0") is True

    def test_invalidate_nonexistent_version(self, manager):
        manager.register(_make_output("out-1", "v:abc:1.0"))
        invalidated = manager.invalidate_version("v:xxx:9.0")
        assert len(invalidated) == 0
        assert manager.registered_count == 1

    def test_invalidate_then_check_invalid(self, manager):
        manager.register(_make_output("out-1", "v:abc:1.0"))
        manager.invalidate_version("v:abc:1.0")
        assert manager.is_valid("out-1", "v:abc:1.0") is False


class TestDomainPackVersionChange:
    def test_domainpack_version_change_invalidates(self, manager):
        """When DomainPack version changes, outputs with old version become invalid."""
        manager.register(_make_output("out-1", "v:aaa:1.0"))
        manager.register(_make_output("out-2", "v:aaa:1.0"))

        # Simulate DomainPack upgrade: invalidate all v1.0 outputs
        invalidated = manager.invalidate_version("v:aaa:1.0")
        assert len(invalidated) == 2

        # New outputs will have new version tags
        assert manager.registered_count == 0

    def test_get_registered_output(self, manager):
        output = _make_output()
        manager.register(output)
        retrieved = manager.get("out-1")
        assert retrieved is not None
        assert retrieved.output_id == "out-1"

    def test_get_unregistered_returns_none(self, manager):
        assert manager.get("nonexistent") is None
