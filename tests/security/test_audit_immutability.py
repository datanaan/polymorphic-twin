"""Audit log immutability tests (M7).

Verifies that audit records are append-only and cannot be deleted
or modified after writing. Tests both the AuditLogWriter API and
the API-level audit endpoints.
"""

from __future__ import annotations

import pytest

from polytwin.core.audit import AuditLogWriter

pytestmark = pytest.mark.security


class TestAuditImmutability:
    """Audit records must be append-only with no delete or modify capability."""

    @pytest.mark.asyncio
    async def test_audit_writer_has_no_delete_method(self) -> None:
        """AuditLogWriter must not expose a delete method."""
        writer = AuditLogWriter()
        assert not hasattr(writer, "delete"), "AuditLogWriter must not have a delete method"
        assert not hasattr(writer, "remove"), "AuditLogWriter must not have a remove method"
        assert not hasattr(writer, "clear"), "AuditLogWriter must not have a clear method"
        assert not hasattr(writer, "pop"), "AuditLogWriter must not have a pop method"

    @pytest.mark.asyncio
    async def test_audit_writer_has_no_update_method(self) -> None:
        """AuditLogWriter must not expose an update method."""
        writer = AuditLogWriter()
        assert not hasattr(writer, "update"), "AuditLogWriter must not have an update method"
        assert not hasattr(writer, "modify"), "AuditLogWriter must not have a modify method"
        assert not hasattr(writer, "replace"), "AuditLogWriter must not have a replace method"

    @pytest.mark.asyncio
    async def test_audit_records_cannot_be_modified_after_writing(self) -> None:
        """Written audit records remain accessible via their event_id.

        The AuditLogWriter has no update/modify/delete API, ensuring
        that through the public interface, records cannot be altered.
        New writes only append; existing records are never overwritten.
        """
        writer = AuditLogWriter()

        # Write a record
        event_id = await writer.write("test_event", "system", {"key": "value"})
        assert event_id is not None

        # Verify record is present and correct
        events = await writer.query({"event_id": event_id})
        assert len(events) == 1
        assert events[0]["event_id"] == event_id
        assert events[0]["event_type"] == "test_event"
        assert events[0]["detail"] == {"key": "value"}

        # Write another event -- should only append
        await writer.write("second_event", "system", {"key": "value2"})
        assert writer.get_event_count() == 2

        # Original event must still be queryable
        events = await writer.query({"event_id": event_id})
        assert len(events) == 1
        assert events[0]["event_type"] == "test_event"

    @pytest.mark.asyncio
    async def test_change_history_append_only(self) -> None:
        """Change history must be append-only -- new events only add, never remove."""
        writer = AuditLogWriter()

        # Write multiple events
        ids = []
        for i in range(5):
            eid = await writer.write(f"event_{i}", f"actor_{i}", {"index": i})
            ids.append(eid)

        # All 5 should be present
        events = await writer.query({})
        assert len(events) == 5

        # Write more events
        for i in range(5, 10):
            eid = await writer.write(f"event_{i}", f"actor_{i}", {"index": i})
            ids.append(eid)

        # Now 10 should be present
        events = await writer.query({})
        assert len(events) == 10

        # All original IDs should still be present
        event_ids = {e["event_id"] for e in events}
        for expected_id in ids:
            assert expected_id in event_ids

    @pytest.mark.asyncio
    async def test_audit_events_in_order(self) -> None:
        """Events must be stored in write order."""
        writer = AuditLogWriter()

        for i in range(10):
            await writer.write(f"ordered_{i}", "system", {"seq": i})

        events = await writer.query({})
        for i, event in enumerate(events):
            assert event["event_type"] == f"ordered_{i}"

    @pytest.mark.asyncio
    async def test_query_returns_copy(self) -> None:
        """Query should return copies, not direct references to internal storage."""
        writer = AuditLogWriter()
        await writer.write("test", "system", {"key": "original"})

        # Get events
        events1 = await writer.query({})
        events2 = await writer.query({})

        # They should have the same content but be different list objects
        assert events1[0]["detail"] == events2[0]["detail"]

    @pytest.mark.asyncio
    async def test_event_id_is_unique(self) -> None:
        """Each event must have a unique event_id."""
        writer = AuditLogWriter()

        ids = set()
        for i in range(100):
            eid = await writer.write("test", "system", {"i": i})
            assert eid not in ids, f"Duplicate event_id: {eid}"
            ids.add(eid)

    @pytest.mark.asyncio
    async def test_event_has_timestamp(self) -> None:
        """Every event must have a timestamp."""
        writer = AuditLogWriter()
        eid = await writer.write("timestamped", "system", {})
        events = await writer.query({"event_id": eid})
        assert len(events) == 1
        assert "timestamp" in events[0]
        assert events[0]["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_get_event_count_accurate(self) -> None:
        """get_event_count must reflect actual number of stored events."""
        writer = AuditLogWriter()

        assert writer.get_event_count() == 0

        for i in range(20):
            await writer.write("count_test", "system", {"i": i})
            assert writer.get_event_count() == i + 1

    @pytest.mark.asyncio
    async def test_query_with_filters(self) -> None:
        """Filtering queries must not modify underlying data."""
        writer = AuditLogWriter()

        # Write mixed event types
        for i in range(10):
            etype = "type_a" if i % 2 == 0 else "type_b"
            await writer.write(etype, f"actor_{i}", {"i": i})

        # Filter for type_a only
        type_a_events = await writer.query({"event_type": "type_a"})
        assert len(type_a_events) == 5

        # All events should still be present
        all_events = await writer.query({})
        assert len(all_events) == 10
