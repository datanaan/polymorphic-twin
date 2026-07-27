"""AuditLogWriter: append-only audit trail for the Core engine.

Records governance events (validations, fallback triggers, certifications,
etc.) in an append-only log.  Events cannot be deleted or modified — only
queried.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime


class AuditLogWriter:
    """Append-only audit event log.

    Events are stored in memory with a unique event_id and timestamp.
    The log supports write and query operations only — no delete or update.
    """

    def __init__(self) -> None:
        self._events: list[dict] = []

    async def write(
        self, event_type: str, actor: str, detail: dict | None = None
    ) -> str:
        """Write an audit event. Append-only — cannot delete or modify.

        Args:
            event_type: Category of event (e.g. "constraint_validation").
            actor: Component or role that triggered the event.
            detail: Event-specific details.

        Returns:
            The unique event_id assigned to this event.
        """
        if detail is None:
            detail = {}
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor,
            "detail": detail,
        }
        self._events.append(event)
        return str(event["event_id"])

    async def query(self, filters: dict | None = None) -> list[dict]:
        """Query audit events (read-only).

        Args:
            filters: Optional key-value pairs to filter events.
                     Events must match all filter keys exactly.

        Returns:
            List of matching event dicts.
        """
        if not filters:
            return list(self._events)
        results = self._events
        for key, value in filters.items():
            results = [e for e in results if e.get(key) == value]
        return results

    def get_event_count(self) -> int:
        """Return the total number of events in the log."""
        return len(self._events)
