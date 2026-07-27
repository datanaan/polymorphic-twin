"""EventBus: async pub/sub with asyncio.Queue for real-time event distribution.

Supports typed subscriptions and a wildcard "*" channel that receives
every published event.
"""
from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict


class EventBus:
    """Async pub/sub event bus backed by per-subscriber queues.

    Usage::

        bus = EventBus()
        queue = bus.subscribe("validation")
        await bus.publish("validation", {"constraint_id": "cc-1", "result": "passed"})
        event = await queue.get()
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, event_type: str) -> asyncio.Queue:
        """Subscribe to events of *event_type*.

        Returns an asyncio.Queue that will receive matching events.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[event_type].append(queue)
        return queue

    async def publish(self, event_type: str, data: dict) -> None:
        """Publish an event to all subscribers of *event_type* and wildcard."""
        payload = {"type": event_type, **data}
        for queue in self._subscribers.get(event_type, []):
            await queue.put(payload)
        # Wildcard subscribers receive every event
        for queue in self._subscribers.get("*", []):
            await queue.put(payload)

    def unsubscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        """Remove a previously subscribed queue from an event type."""
        if event_type in self._subscribers:
            with contextlib.suppress(ValueError):
                self._subscribers[event_type].remove(queue)

    def subscriber_count(self, event_type: str) -> int:
        """Return the number of active subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))


# Module-level singleton
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the shared EventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the EventBus singleton. Used between test sessions."""
    global _event_bus
    _event_bus = None
