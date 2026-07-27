"""Tests for AuditLogWriter: append-only audit trail.

Test cases:
1. Write event -> event stored with UUID
2. Query returns events
3. Events are append-only -- no delete method exists
4. Query with filter returns matching events only
"""
import pytest

from polytwin.core.audit import AuditLogWriter

# ── Test 1: Write event -> stored with UUID ─────────────────────────


class TestWrite:
    @pytest.mark.asyncio
    async def test_write_returns_uuid(self):
        """Write event -> returns a valid UUID string."""
        writer = AuditLogWriter()
        event_id = await writer.write("validation", "core", {"key": "value"})
        assert isinstance(event_id, str)
        assert len(event_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_write_stores_event(self):
        """Write event -> event is stored with all fields."""
        writer = AuditLogWriter()
        await writer.write("validation", "core_engine", {"status": "passed"})
        assert writer.get_event_count() == 1

    @pytest.mark.asyncio
    async def test_event_has_required_fields(self):
        """Written event has event_id, event_type, timestamp, actor, detail."""
        writer = AuditLogWriter()
        event_id = await writer.write("fallback", "safety_sys", {"strategy": "shutdown"})
        events = await writer.query()
        assert len(events) == 1
        event = events[0]
        assert event["event_id"] == event_id
        assert event["event_type"] == "fallback"
        assert event["actor"] == "safety_sys"
        assert event["detail"]["strategy"] == "shutdown"
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_write_without_detail(self):
        """Write with no detail -> defaults to empty dict."""
        writer = AuditLogWriter()
        await writer.write("startup", "system")
        events = await writer.query()
        assert events[0]["detail"] == {}


# ── Test 2: Query returns events ────────────────────────────────────


class TestQuery:
    @pytest.mark.asyncio
    async def test_query_returns_all_events(self):
        """Query with no filters returns all events."""
        writer = AuditLogWriter()
        await writer.write("type_a", "actor1", {"x": 1})
        await writer.write("type_b", "actor2", {"y": 2})
        events = await writer.query()
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_query_empty_log(self):
        """Query on empty log returns empty list."""
        writer = AuditLogWriter()
        events = await writer.query()
        assert events == []


# ── Test 3: Append-only (no delete) ─────────────────────────────────


class TestAppendOnly:
    @pytest.mark.asyncio
    async def test_no_delete_method(self):
        """AuditLogWriter has no delete/remove method."""
        writer = AuditLogWriter()
        assert not hasattr(writer, "delete")
        assert not hasattr(writer, "remove")
        assert not hasattr(writer, "update")

    @pytest.mark.asyncio
    async def test_events_accumulate(self):
        """Multiple writes accumulate; get_event_count reflects total."""
        writer = AuditLogWriter()
        for i in range(5):
            await writer.write("batch", "actor", {"i": i})
        assert writer.get_event_count() == 5


# ── Test 4: Query with filter ───────────────────────────────────────


class TestQueryFiltered:
    @pytest.mark.asyncio
    async def test_filter_by_event_type(self):
        """Query with event_type filter returns matching events only."""
        writer = AuditLogWriter()
        await writer.write("validation", "core", {"status": "passed"})
        await writer.write("fallback", "safety", {"strategy": "shutdown"})
        await writer.write("validation", "core", {"status": "failed"})

        results = await writer.query({"event_type": "validation"})
        assert len(results) == 2
        for r in results:
            assert r["event_type"] == "validation"

    @pytest.mark.asyncio
    async def test_filter_by_actor(self):
        """Query with actor filter returns matching events only."""
        writer = AuditLogWriter()
        await writer.write("validation", "core_engine", {})
        await writer.write("validation", "lab_engine", {})

        results = await writer.query({"actor": "core_engine"})
        assert len(results) == 1
        assert results[0]["actor"] == "core_engine"

    @pytest.mark.asyncio
    async def test_filter_no_match_returns_empty(self):
        """Query with non-matching filter returns empty list."""
        writer = AuditLogWriter()
        await writer.write("validation", "core", {})
        results = await writer.query({"event_type": "nonexistent"})
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_filters(self):
        """Query with multiple filter keys narrows results."""
        writer = AuditLogWriter()
        await writer.write("validation", "core", {"status": "passed"})
        await writer.write("validation", "core", {"status": "failed"})
        await writer.write("fallback", "core", {"status": "passed"})

        results = await writer.query({"event_type": "validation", "actor": "core"})
        assert len(results) == 2
