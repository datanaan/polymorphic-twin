"""Tests for EventBus pub/sub with asyncio.Queue."""
from __future__ import annotations

import asyncio

import pytest

from polytwin.api.events import EventBus, get_event_bus, reset_event_bus


class TestEventBusSubscribe:
    """EventBus.subscribe returns a queue that receives events."""

    @pytest.mark.asyncio
    async def test_subscriber_receives_published_event(self) -> None:
        bus = EventBus()
        q = bus.subscribe("validation")
        await bus.publish("validation", {"result": "passed"})
        event = await asyncio.wait_for(q.get(), timeout=1.0)
        assert event["type"] == "validation"
        assert event["result"] == "passed"

    @pytest.mark.asyncio
    async def test_subscriber_does_not_receive_other_events(self) -> None:
        bus = EventBus()
        q = bus.subscribe("validation")
        await bus.publish("tick", {"value": 1})
        # Queue should be empty
        assert q.empty()

    @pytest.mark.asyncio
    async def test_multiple_events_in_order(self) -> None:
        bus = EventBus()
        q = bus.subscribe("tick")
        await bus.publish("tick", {"seq": 1})
        await bus.publish("tick", {"seq": 2})
        await bus.publish("tick", {"seq": 3})

        e1 = await asyncio.wait_for(q.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q.get(), timeout=1.0)
        e3 = await asyncio.wait_for(q.get(), timeout=1.0)
        assert e1["seq"] == 1
        assert e2["seq"] == 2
        assert e3["seq"] == 3


class TestEventBusUnsubscribe:
    """EventBus.unsubscribe stops event delivery."""

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_receiving(self) -> None:
        bus = EventBus()
        q = bus.subscribe("audit")
        await bus.publish("audit", {"event": "before"})
        _ = await asyncio.wait_for(q.get(), timeout=1.0)

        bus.unsubscribe("audit", q)
        await bus.publish("audit", {"event": "after"})
        assert q.empty()

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_queue_no_error(self) -> None:
        bus = EventBus()
        q = asyncio.Queue()
        # Should not raise
        bus.unsubscribe("validation", q)


class TestEventBusWildcard:
    """Wildcard subscribers receive all events."""

    @pytest.mark.asyncio
    async def test_wildcard_receives_all_events(self) -> None:
        bus = EventBus()
        q = bus.subscribe("*")
        await bus.publish("tick", {"value": 1})
        await bus.publish("validation", {"result": "passed"})

        e1 = await asyncio.wait_for(q.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q.get(), timeout=1.0)
        assert e1["type"] == "tick"
        assert e2["type"] == "validation"

    @pytest.mark.asyncio
    async def test_typed_and_wildcard_both_receive(self) -> None:
        bus = EventBus()
        typed_q = bus.subscribe("audit")
        wildcard_q = bus.subscribe("*")
        await bus.publish("audit", {"detail": "test"})

        typed_event = await asyncio.wait_for(typed_q.get(), timeout=1.0)
        wildcard_event = await asyncio.wait_for(wildcard_q.get(), timeout=1.0)
        assert typed_event["detail"] == "test"
        assert wildcard_event["detail"] == "test"


class TestEventBusMultipleSubscribers:
    """Multiple subscribers all receive the same events."""

    @pytest.mark.asyncio
    async def test_all_subscribers_receive(self) -> None:
        bus = EventBus()
        q1 = bus.subscribe("fallback")
        q2 = bus.subscribe("fallback")
        q3 = bus.subscribe("fallback")

        await bus.publish("fallback", {"strategy": "safe_state"})

        for q in [q1, q2, q3]:
            event = await asyncio.wait_for(q.get(), timeout=1.0)
            assert event["strategy"] == "safe_state"

    @pytest.mark.asyncio
    async def test_subscriber_count(self) -> None:
        bus = EventBus()
        assert bus.subscriber_count("tick") == 0
        bus.subscribe("tick")
        assert bus.subscriber_count("tick") == 1
        bus.subscribe("tick")
        assert bus.subscriber_count("tick") == 2


class TestEventBusSingleton:
    """Module-level singleton management."""

    def test_get_event_bus_returns_instance(self) -> None:
        reset_event_bus()
        bus = get_event_bus()
        assert isinstance(bus, EventBus)

    def test_get_event_bus_returns_same_instance(self) -> None:
        reset_event_bus()
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_reset_clears_singleton(self) -> None:
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        assert bus1 is not bus2
