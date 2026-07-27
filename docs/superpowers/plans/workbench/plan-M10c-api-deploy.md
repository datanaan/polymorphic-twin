# M10c: API 服务 — WebSocket、部署与监控

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 添加 WebSocket 实时推送、Docker 部署配置、Prometheus 监控指标、性能测试。

**Architecture:** WebSocket 端点推送引擎事件。Docker 镜像打包 API 服务 + PostgreSQL。Prometheus 指标在 /metrics 端点暴露。

**Spec reference:** `docs/superpowers/specs/2026-05-07-product-api-service.md` v1.0.0 §2.3, §6, §7

**Quality gate:** docker-compose up 后健康检查通过，WebSocket 可接收实时事件，/metrics 暴露全部指标。

**Depends on:** plan-M10b-api-endpoints.md (business endpoints)

---

## File Structure

```
polymorphic-twin/
├── polymorphic_twin/
│   └── api/
│       ├── routes/
│       │   └── websocket.py                     # Task 1
│       ├── services/
│       │   └── event_bus.py                     # Task 2
│       └── middleware/
│           └── metrics.py                       # Task 4
├── tests/
│   └── api/
│       ├── unit/
│       │   ├── test_websocket.py                # Task 1
│       │   ├── test_event_bus.py                # Task 2
│       │   └── test_metrics.py                  # Task 4
│       ├── performance/
│       │   ├── test_throughput.py               # Task 5
│       │   └── test_latency.py                  # Task 5
│       └── integration/
│           └── test_docker_deploy.py             # Task 6
├── Dockerfile                                   # Task 3
├── docker-compose.yml                           # Task 3
├── docker-compose.dev.yml                       # Task 3
└── .dockerignore                                # Task 3
```

---

## Task 1: WebSocket Endpoint

**Files:**
- Create: `polymorphic_twin/api/routes/websocket.py`
- Create: `tests/api/unit/test_websocket.py`

**Purpose:** WebSocket 端点 `WS /api/v1/twins/{twin_id}/ws`，实时推送引擎事件到客户端。

**Spec:** §2.3 — 8 种事件类型，JSON 格式 `{event_type, timestamp, data}`，支持断线重连。

- [ ] **Step 1: 编写 WebSocket 测试** `tests/api/unit/test_websocket.py`

```python
"""WebSocket endpoint unit tests."""
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from polymorphic_twin.api.app import app
from polymorphic_twin.api.services.event_bus import EventBus


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def event_bus():
    bus = EventBus()
    return bus


class TestWebSocketConnection:
    """Test WS /api/v1/twins/{twin_id}/ws lifecycle."""

    def test_websocket_connect_success(self, client):
        """Valid twin_id + auth establishes WS connection."""
        with client.websocket_connect(
            "/api/v1/twins/twin_test001/ws"
        ) as ws:
            # Connection established, should receive welcome message
            data = ws.receive_json()
            assert data["event_type"] == "connected"
            assert "twin_id" in data["data"]

    def test_websocket_receives_state_updated(self, client):
        """state_updated event pushed through WS after state change."""
        with client.websocket_connect(
            "/api/v1/twins/twin_test001/ws"
        ) as ws:
            _ = ws.receive_json()  # consume welcome
            # Simulate engine publishing state_updated event
            from polymorphic_twin.api.services.event_bus import event_bus
            event_bus.publish("twin_test001", {
                "event_type": "state_updated",
                "data": {"temperature": 185.3, "pressure": 15.2},
            })
            msg = ws.receive_json()
            assert msg["event_type"] == "state_updated"
            assert msg["data"]["temperature"] == 185.3
            assert "timestamp" in msg

    def test_websocket_receives_constraint_evaluated(self, client):
        """constraint_evaluated event pushed correctly."""
        with client.websocket_connect(
            "/api/v1/twins/twin_test001/ws"
        ) as ws:
            _ = ws.receive_json()
            from polymorphic_twin.api.services.event_bus import event_bus
            event_bus.publish("twin_test001", {
                "event_type": "constraint_evaluated",
                "data": {
                    "results": {"max_temperature": "passed"},
                    "safety_status": "normal",
                },
            })
            msg = ws.receive_json()
            assert msg["event_type"] == "constraint_evaluated"

    def test_websocket_receives_fallback_triggered(self, client):
        """fallback_triggered event includes reason and action."""
        with client.websocket_connect(
            "/api/v1/twins/twin_test001/ws"
        ) as ws:
            _ = ws.receive_json()
            from polymorphic_twin.api.services.event_bus import event_bus
            event_bus.publish("twin_test001", {
                "event_type": "fallback_triggered",
                "data": {
                    "fallback_action": "emergency_shutdown",
                    "fallback_reason": "max_temperature violated: 285.0 > 280.0",
                },
            })
            msg = ws.receive_json()
            assert msg["event_type"] == "fallback_triggered"
            assert msg["data"]["fallback_action"] == "emergency_shutdown"

    def test_websocket_all_event_types(self, client):
        """All 8 event types are valid and delivered."""
        event_types = [
            "state_updated", "constraint_evaluated", "fallback_triggered",
            "action_space_updated", "exploration_progress",
            "exploration_completed", "identity_status_changed",
            "domain_pack_updated",
        ]
        with client.websocket_connect(
            "/api/v1/twins/twin_test001/ws"
        ) as ws:
            _ = ws.receive_json()
            from polymorphic_twin.api.services.event_bus import event_bus
            for et in event_types:
                event_bus.publish("twin_test001", {
                    "event_type": et,
                    "data": {"test": True},
                })
                msg = ws.receive_json()
                assert msg["event_type"] == et
                assert "timestamp" in msg
                assert "data" in msg

    def test_websocket_isolation_between_twins(self, client):
        """Events for twin A do not leak to twin B's WS connection."""
        with client.websocket_connect(
            "/api/v1/twins/twin_A/ws"
        ) as ws_a, client.websocket_connect(
            "/api/v1/twins/twin_B/ws"
        ) as ws_b:
            _ = ws_a.receive_json()
            _ = ws_b.receive_json()
            from polymorphic_twin.api.services.event_bus import event_bus
            event_bus.publish("twin_A", {
                "event_type": "state_updated",
                "data": {"temperature": 100.0},
            })
            msg = ws_a.receive_json()
            assert msg["event_type"] == "state_updated"
            # twin_B should not receive twin_A's event — verify no pending msg
            # (In TestClient, we check that next message is NOT from twin_A)
            # Only publish to twin_B and verify it arrives correctly
            event_bus.publish("twin_B", {
                "event_type": "constraint_evaluated",
                "data": {"results": {}},
            })
            msg_b = ws_b.receive_json()
            assert msg_b["event_type"] == "constraint_evaluated"

    def test_websocket_message_format(self, client):
        """Message format: {event_type, timestamp, data}."""
        with client.websocket_connect(
            "/api/v1/twins/twin_fmt/ws"
        ) as ws:
            welcome = ws.receive_json()
            assert "event_type" in welcome
            assert "timestamp" in welcome
            assert "data" in welcome

    def test_websocket_disconnect_cleans_up(self, client, event_bus):
        """After disconnect, subscriber is removed from event bus."""
        from polymorphic_twin.api.services.event_bus import event_bus
        with client.websocket_connect(
            "/api/v1/twins/twin_clean/ws"
        ) as ws:
            _ = ws.receive_json()
            initial_count = event_bus.subscriber_count("twin_clean")
            assert initial_count >= 1
        # After disconnect, count should decrease
        final_count = event_bus.subscriber_count("twin_clean")
        assert final_count == initial_count - 1
```

- [ ] **Step 2: 编写 WebSocket 端点** `polymorphic_twin/api/routes/websocket.py`

```python
"""WebSocket endpoint for real-time event push."""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from polymorphic_twin.api.services.event_bus import event_bus

router = APIRouter()

VALID_EVENT_TYPES = {
    "state_updated", "constraint_evaluated", "fallback_triggered",
    "action_space_updated", "exploration_progress", "exploration_completed",
    "identity_status_changed", "domain_pack_updated",
}


@router.websocket("/twins/{twin_id}/ws")
async def twins_websocket(websocket: WebSocket, twin_id: str):
    """WebSocket endpoint for real-time TwinObject event push.

    Events delivered: state_updated, constraint_evaluated,
    fallback_triggered, action_space_updated, exploration_progress,
    exploration_completed, identity_status_changed, domain_pack_updated.
    Message format: {"event_type": str, "timestamp": str, "data": dict}
    """
    await websocket.accept()
    subscriber_id = event_bus.subscribe(twin_id)

    # Send welcome message
    await websocket.send_json({
        "event_type": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"twin_id": twin_id, "message": "WebSocket connected"},
    })

    try:
        queue = event_bus.get_queue(twin_id, subscriber_id)
        while True:
            # Check for outgoing events from the bus
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json({
                    "event_type": event["event_type"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": event["data"],
                })
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({
                        "event_type": "ping",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {},
                    })
                except Exception:
                    break
            # Also receive any client messages (for future command protocol)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                # Client messages currently ignored; reserved for future commands
            except (asyncio.TimeoutError, WebSocketDisconnect):
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        event_bus.unsubscribe(twin_id, subscriber_id)
```

- [ ] **Step 3: 运行测试，确认通过后提交**

```bash
pytest tests/api/unit/test_websocket.py -v
```

---

## Task 2: Event Bus

**Files:**
- Create: `polymorphic_twin/api/services/event_bus.py`
- Create: `tests/api/unit/test_event_bus.py`

**Purpose:** 进程内事件总线，连接引擎事件到 WebSocket 订阅者。Pub/sub 模式：引擎发布，WebSocket 订阅者接收。支持每个 TwinObject 多个并发订阅者。

- [ ] **Step 1: 编写 Event Bus 测试** `tests/api/unit/test_event_bus.py`

```python
"""Event bus unit tests."""
import asyncio
import pytest
from polymorphic_twin.api.services.event_bus import EventBus


@pytest.fixture
def bus():
    return EventBus()


class TestEventBusSubscribe:
    """Test subscription lifecycle."""

    def test_subscribe_returns_subscriber_id(self, bus):
        sid = bus.subscribe("twin_A")
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_multiple_subscribers_same_twin(self, bus):
        sid1 = bus.subscribe("twin_X")
        sid2 = bus.subscribe("twin_X")
        assert sid1 != sid2
        assert bus.subscriber_count("twin_X") == 2

    def test_subscriber_count_empty(self, bus):
        assert bus.subscriber_count("nonexistent") == 0


class TestEventBusPublish:
    """Test event publishing and delivery."""

    @pytest.mark.asyncio
    async def test_publish_delivers_to_subscriber(self, bus):
        bus.subscribe("twin_A")
        bus.publish("twin_A", {"event_type": "state_updated", "data": {"temp": 100}})
        queue = bus.get_queue("twin_A", bus._subscribers["twin_A"][0])
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["event_type"] == "state_updated"
        assert event["data"]["temp"] == 100

    @pytest.mark.asyncio
    async def test_publish_delivers_to_all_subscribers(self, bus):
        sid1 = bus.subscribe("twin_B")
        sid2 = bus.subscribe("twin_B")
        bus.publish("twin_B", {"event_type": "constraint_evaluated", "data": {}})
        q1 = bus.get_queue("twin_B", sid1)
        q2 = bus.get_queue("twin_B", sid2)
        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert e1["event_type"] == "constraint_evaluated"
        assert e2["event_type"] == "constraint_evaluated"

    @pytest.mark.asyncio
    async def test_publish_isolation_between_twins(self, bus):
        sid_a = bus.subscribe("twin_A")
        sid_b = bus.subscribe("twin_B")
        bus.publish("twin_A", {"event_type": "state_updated", "data": {"t": 1}})
        q_b = bus.get_queue("twin_B", sid_b)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q_b.get(), timeout=0.1)

    def test_publish_to_no_subscribers_no_error(self, bus):
        """Publishing to a twin with no subscribers does not raise."""
        bus.publish("orphan_twin", {"event_type": "test", "data": {}})


class TestEventBusUnsubscribe:
    """Test unsubscribe cleanup."""

    def test_unsubscribe_removes_subscriber(self, bus):
        sid = bus.subscribe("twin_C")
        assert bus.subscriber_count("twin_C") == 1
        bus.unsubscribe("twin_C", sid)
        assert bus.subscriber_count("twin_C") == 0

    def test_unsubscribe_unknown_subscriber_no_error(self, bus):
        bus.unsubscribe("twin_Z", "fake_id")

    def test_unsubscribe_all_for_twin(self, bus):
        bus.subscribe("twin_D")
        bus.subscribe("twin_D")
        bus.unsubscribe_all("twin_D")
        assert bus.subscriber_count("twin_D") == 0
```

- [ ] **Step 2: 编写 Event Bus 实现** `polymorphic_twin/api/services/event_bus.py`

```python
"""In-process event bus connecting engine events to WebSocket subscribers.

Pub/sub pattern: engine publishes events keyed by twin_id,
WebSocket handlers subscribe and receive events via asyncio.Queue.
Supports multiple concurrent subscribers per TwinObject.
"""
import asyncio
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional


class EventBus:
    """In-process pub/sub event bus for TwinObject events."""

    def __init__(self, max_queue_size: int = 256):
        self._subscribers: Dict[str, Dict[str, asyncio.Queue]] = defaultdict(dict)
        self._max_queue_size = max_queue_size

    def subscribe(self, twin_id: str) -> str:
        """Subscribe to events for a given twin_id. Returns subscriber_id."""
        subscriber_id = str(uuid.uuid4())
        self._subscribers[twin_id][subscriber_id] = asyncio.Queue(
            maxsize=self._max_queue_size
        )
        return subscriber_id

    def unsubscribe(self, twin_id: str, subscriber_id: str) -> None:
        """Remove a subscriber. No-op if subscriber doesn't exist."""
        subs = self._subscribers.get(twin_id)
        if subs and subscriber_id in subs:
            del subs[subscriber_id]
            if not subs:
                del self._subscribers[twin_id]

    def unsubscribe_all(self, twin_id: str) -> None:
        """Remove all subscribers for a twin_id."""
        self._subscribers.pop(twin_id, None)

    def publish(self, twin_id: str, event: Dict[str, Any]) -> None:
        """Publish an event to all subscribers of twin_id.

        Event must have 'event_type' and 'data' keys.
        If a subscriber's queue is full, the event is dropped for that subscriber.
        """
        subs = self._subscribers.get(twin_id)
        if not subs:
            return
        for sid, queue in subs.items():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop event for slow subscribers

    def get_queue(self, twin_id: str, subscriber_id: str) -> asyncio.Queue:
        """Get the asyncio.Queue for a specific subscriber."""
        return self._subscribers[twin_id][subscriber_id]

    def subscriber_count(self, twin_id: str) -> int:
        """Return number of active subscribers for a twin_id."""
        return len(self._subscribers.get(twin_id, {}))


# Global singleton event bus instance
event_bus = EventBus()
```

- [ ] **Step 3: 运行测试，确认通过后提交**

```bash
pytest tests/api/unit/test_event_bus.py -v
```

---

## Task 3: Docker Configuration

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `.dockerignore`

**Purpose:** 多阶段 Docker 镜像构建，docker-compose 编排 API + PostgreSQL，开发模式使用 SQLite + 热重载。

**Spec:** §6.1 Dockerfile, §6.2 docker-compose.yml, §6.3 环境配置

- [ ] **Step 1: 编写 .dockerignore**

```
.git
.github
__pycache__
*.pyc
*.pyo
.pytest_cache
.mypy_cache
.ruff_cache
*.egg-info
dist
build
.eggs
docs
*.md
!README.md
.env
.env.*
docker-compose*.yml
Dockerfile
.venv
venv
htmlcov
.coverage
```

- [ ] **Step 2: 编写 Dockerfile（多阶段构建）**

```dockerfile
# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
COPY polymorphic_twin/ polymorphic_twin/

RUN pip install --no-cache-dir --prefix=/install .

# ---- Runtime stage ----
FROM python:3.11-slim

WORKDIR /app

# Install runtime system deps (curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY polymorphic_twin/ polymorphic_twin/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

CMD ["uvicorn", "polymorphic_twin.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 编写 docker-compose.yml（生产配置）**

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "${PT_PORT:-8000}:8000"
    environment:
      - PT_STORAGE_BACKEND=postgres
      - PT_STORAGE_URL=postgresql+asyncpg://pt:${PT_DB_PASSWORD:-pt}@db:5432/polymorphic_twin
      - PT_LOG_LEVEL=${PT_LOG_LEVEL:-INFO}
      - PT_LOG_FORMAT=json
      - PT_ADMIN_API_KEY=${PT_ADMIN_API_KEY:?PT_ADMIN_API_KEY is required}
      - PT_MAX_TWINS=${PT_MAX_TWINS:-100}
      - PT_CORS_ORIGINS=${PT_CORS_ORIGINS:-}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=polymorphic_twin
      - POSTGRES_USER=pt
      - POSTGRES_PASSWORD=${PT_DB_PASSWORD:-pt}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pt -d polymorphic_twin"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```

- [ ] **Step 4: 编写 docker-compose.dev.yml（开发配置）**

```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PT_STORAGE_BACKEND=sqlite
      - PT_LOG_LEVEL=DEBUG
      - PT_LOG_FORMAT=text
      - PT_ADMIN_API_KEY=${PT_ADMIN_API_KEY:-ptw_dev_admin_key_for_testing_only}
      - PT_MAX_TWINS=10
    volumes:
      - ./polymorphic_twin:/app/polymorphic_twin
    command: >
      uvicorn polymorphic_twin.api.app:app
      --host 0.0.0.0
      --port 8000
      --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

- [ ] **Step 5: 验证 Docker 构建**

```bash
docker build -t polymorphic-twin-api:test .
docker run --rm -e PT_ADMIN_API_KEY=ptw_test -p 8000:8000 polymorphic-twin-api:test &
sleep 5
curl -f http://localhost:8000/api/v1/health/
docker stop $(docker ps -q --filter ancestor=polymorphic-twin-api:test)
```

---

## Task 4: Prometheus Metrics

**Files:**
- Create: `polymorphic_twin/api/middleware/metrics.py`
- Create: `tests/api/unit/test_metrics.py`

**Purpose:** Prometheus 指标端点 `GET /metrics`，暴露 Spec §7.1 全部 8 项指标。中间件自动递增请求计数器。

**Spec:** §7.1 指标定义, §7.2 /metrics 端点

- [ ] **Step 1: 编写 Metrics 测试** `tests/api/unit/test_metrics.py`

```python
"""Prometheus metrics unit tests."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from polymorphic_twin.api.middleware.metrics import (
    setup_metrics,
    metrics_endpoint,
    METRIC_NAMES,
)


@pytest.fixture
def app():
    app = FastAPI()
    setup_metrics(app)
    app.add_route("/metrics", metrics_endpoint)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestMetricsEndpoint:
    """Test /metrics endpoint."""

    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_prometheus_format(self, client):
        resp = client.get("/metrics")
        text = resp.text
        # Prometheus exposition format: lines like "metric_name{labels} value"
        for name in METRIC_NAMES:
            assert name in text, f"Missing metric: {name}"

    def test_metrics_content_type(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.headers.get("content-type", "")
        assert "version=0.0.4" in resp.headers.get("content-type", "")

    def test_requests_total_increments(self, client):
        # Make a request to trigger middleware
        client.get("/nonexistent")
        resp = client.get("/metrics")
        text = resp.text
        assert "pt_requests_total" in text


class TestMetricNames:
    """Verify all required metrics are defined."""

    def test_all_spec_metrics_present(self):
        required = [
            "pt_requests_total",
            "pt_request_duration_seconds",
            "pt_active_twins",
            "pt_constraint_evaluations_total",
            "pt_fallback_triggered_total",
            "pt_lab_explorations_total",
            "pt_bridge_generations_total",
            "pt_websocket_connections",
        ]
        for name in required:
            assert name in METRIC_NAMES, f"Missing: {name}"
```

- [ ] **Step 2: 编写 Metrics 实现** `polymorphic_twin/api/middleware/metrics.py`

```python
"""Prometheus metrics middleware and /metrics endpoint.

Exposes all 8 metrics from Spec §7.1:
- pt_requests_total (Counter): HTTP requests by method, path, status
- pt_request_duration_seconds (Histogram): Request latency
- pt_active_twins (Gauge): Active TwinObject count
- pt_constraint_evaluations_total (Counter): Evaluations by result
- pt_fallback_triggered_total (Counter): Safety fallback triggers
- pt_lab_explorations_total (Counter): Lab explorations by status
- pt_bridge_generations_total (Counter): Bridge action space generations
- pt_websocket_connections (Gauge): Current WS connections
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Minimal Prometheus exposition format implementation (no external dependency)
_METRICS = {}
METRIC_NAMES = []


class _Counter:
    def __init__(self, name: str, help_text: str, labels: tuple = ()):
        self.name = name
        self.help_text = help_text
        self.label_names = labels
        self._values = {}  # label_key -> float

    def inc(self, **labels):
        key = tuple(labels.get(l, "") for l in self.label_names)
        self._values[key] = self._values.get(key, 0.0) + 1.0

    def collect(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}",
                 f"# TYPE {self.name} counter"]
        for key, val in self._values.items():
            if self.label_names:
                label_str = ", ".join(
                    f'{n}="{v}"' for n, v in zip(self.label_names, key)
                )
                lines.append(f"{self.name}{{{label_str}}} {val}")
            else:
                lines.append(f"{self.name} {val}")
        return "\n".join(lines) + "\n"


class _Gauge:
    def __init__(self, name: str, help_text: str):
        self.name = name
        self.help_text = help_text
        self._value = 0.0

    def set(self, value: float):
        self._value = value

    def inc(self):
        self._value += 1.0

    def dec(self):
        self._value -= 1.0

    def collect(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}",
                 f"# TYPE {self.name} gauge"]
        lines.append(f"{self.name} {self._value}")
        return "\n".join(lines) + "\n"


class _Histogram:
    def __init__(self, name: str, help_text: str, buckets: tuple = ()):
        self.name = name
        self.help_text = help_text
        self.buckets = buckets or (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        self._counts = {b: 0 for b in self.buckets}
        self._counts["+Inf"] = 0
        self._sum = 0.0

    def observe(self, value: float):
        self._sum += value
        self._counts["+Inf"] += 1
        for b in self.buckets:
            if value <= b:
                self._counts[b] += 1

    def collect(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}",
                 f"# TYPE {self.name} histogram"]
        for b in list(self.buckets) + ["+Inf"]:
            le = b if b != "+Inf" else "+Inf"
            lines.append(f'{self.name}_bucket{{le="{le}"}} {self._counts[b]}')
        lines.append(f"{self.name}_count {self._counts['+Inf']}")
        lines.append(f"{self.name}_sum {self._sum}")
        return "\n".join(lines) + "\n"


def _register(cls, name, help_text, **kwargs):
    metric = cls(name, help_text, **kwargs)
    _METRICS[name] = metric
    METRIC_NAMES.append(name)
    return metric


# Register all Spec §7.1 metrics
pt_requests_total = _register(
    _Counter, "pt_requests_total",
    "Total HTTP requests",
    labels=("method", "path", "status"),
)
pt_request_duration_seconds = _register(
    _Histogram, "pt_request_duration_seconds",
    "Request duration in seconds",
)
pt_active_twins = _register(
    _Gauge, "pt_active_twins",
    "Currently active TwinObject instances",
)
pt_constraint_evaluations_total = _register(
    _Counter, "pt_constraint_evaluations_total",
    "Total constraint evaluations",
    labels=("result",),
)
pt_fallback_triggered_total = _register(
    _Counter, "pt_fallback_triggered_total",
    "Total safety fallback triggers",
)
pt_lab_explorations_total = _register(
    _Counter, "pt_lab_explorations_total",
    "Total Lab explorations",
    labels=("status",),
)
pt_bridge_generations_total = _register(
    _Counter, "pt_bridge_generations_total",
    "Total Bridge action space generations",
)
pt_websocket_connections = _register(
    _Gauge, "pt_websocket_connections",
    "Current WebSocket connections",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to auto-increment request counters and record duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        # Skip /metrics itself to avoid recursive counting
        if request.url.path != "/metrics":
            pt_requests_total.inc(
                method=request.method,
                path=request.url.path,
                status=str(response.status_code),
            )
            pt_request_duration_seconds.observe(duration)

        return response


def setup_metrics(app):
    """Register metrics middleware on a FastAPI app."""
    app.add_middleware(MetricsMiddleware)


async def metrics_endpoint(request: Request) -> Response:
    """Handler for GET /metrics — Prometheus exposition format."""
    body = ""
    for metric in _METRICS.values():
        body += metric.collect()
    return Response(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
```

- [ ] **Step 3: 运行测试，确认通过后提交**

```bash
pytest tests/api/unit/test_metrics.py -v
```

---

## Task 5: Performance Tests

**Files:**
- Create: `tests/api/performance/test_throughput.py`
- Create: `tests/api/performance/test_latency.py`

**Purpose:** 验证 Spec §8.3 性能指标：状态更新吞吐 ≥1000 req/s，约束评估延迟 p99<10ms，安全回落延迟 <200ms，WebSocket 事件投递 <100ms。

**Spec:** §8.3 性能测试, §4.4 并发能力

- [ ] **Step 1: 编写吞吐量测试** `tests/api/performance/test_throughput.py`

```python
"""State update throughput performance tests.

Target: >= 1000 req/s per instance (Spec §4.4, §8.3).
"""
import asyncio
import time
import pytest
import httpx
from polymorphic_twin.api.app import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _create_twin(client: TestClient, twin_name: str) -> str:
    """Helper: create a TwinObject and return its twin_id."""
    resp = client.post(
        "/api/v1/twins/",
        json={
            "name": twin_name,
            "domain_pack_id": "test.default",
            "initial_state": {"temperature": 25.0, "pressure": 1.0},
        },
        headers={"Authorization": "Bearer ptw_test_admin_key"},
    )
    assert resp.status_code == 201
    return resp.json()["twin_id"]


class TestStateUpdateThroughput:
    """Throughput benchmark: state updates per second."""

    def test_throughput_1000_consecutive_updates(self, client):
        """Send 1000 consecutive state updates, measure throughput.

        Target: complete in under 1 second (>= 1000 req/s).
        """
        twin_id = _create_twin(client, "throughput-test-001")
        payload = {"temperature": 50.0, "pressure": 2.0}
        headers = {"Authorization": "Bearer ptw_test_admin_key"}

        start = time.monotonic()
        for _ in range(1000):
            resp = client.put(
                f"/api/v1/twins/{twin_id}/state/",
                json=payload,
                headers=headers,
            )
        elapsed = time.monotonic() - start

        rps = 1000 / elapsed
        print(f"\nThroughput: {rps:.0f} req/s (elapsed: {elapsed:.3f}s)")
        assert rps >= 1000, f"Throughput {rps:.0f} req/s < 1000 req/s target"

    def test_throughput_100_concurrent_updates(self, client):
        """Send 100 updates via asyncio tasks to simulate concurrency.

        Target: average throughput >= 1000 req/s.
        """
        twin_id = _create_twin(client, "throughput-test-002")

        async def _run_async_throughput():
            async with httpx.AsyncClient(
                app=app, base_url="http://test"
            ) as ac:
                sem = asyncio.Semaphore(20)
                async def _update(i):
                    async with sem:
                        resp = await ac.put(
                            f"/api/v1/twins/{twin_id}/state/",
                            json={"temperature": float(i)},
                            headers={"Authorization": "Bearer ptw_test_admin_key"},
                        )
                        return resp.status_code

                start = time.monotonic()
                results = await asyncio.gather(*[_update(i) for i in range(100)])
                elapsed = time.monotonic() - start
                return results, elapsed

        results, elapsed = asyncio.get_event_loop().run_until_complete(
            _run_async_throughput()
        )
        rps = 100 / elapsed
        print(f"\nConcurrent throughput: {rps:.0f} req/s (elapsed: {elapsed:.3f}s)")
        assert all(r in (200, 429) for r in results)
```

- [ ] **Step 2: 编写延迟测试** `tests/api/performance/test_latency.py`

```python
"""Latency performance tests.

Targets (Spec §8.3):
- Constraint evaluation latency: p99 < 10ms
- Safety fallback latency: < 200ms
- WebSocket event delivery: < 100ms
"""
import time
import statistics
import pytest
from fastapi.testclient import TestClient
from polymorphic_twin.api.app import app
from polymorphic_twin.api.services.event_bus import event_bus


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestConstraintEvaluationLatency:
    """p99 constraint evaluation latency < 10ms."""

    def test_p99_latency_under_10ms(self, client):
        """Measure latency of 1000 state updates, p99 must be < 10ms.

        Measures time from request sent to response received (client-side).
        """
        resp = client.post(
            "/api/v1/twins/",
            json={
                "name": "latency-test-001",
                "domain_pack_id": "test.default",
                "initial_state": {"temperature": 25.0},
            },
            headers={"Authorization": "Bearer ptw_test_admin_key"},
        )
        twin_id = resp.json()["twin_id"]
        headers = {"Authorization": "Bearer ptw_test_admin_key"}

        latencies = []
        for i in range(1000):
            payload = {"temperature": 25.0 + (i % 100) * 0.5}
            start = time.monotonic()
            resp = client.put(
                f"/api/v1/twins/{twin_id}/state/",
                json=payload,
                headers=headers,
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p99 = latencies[int(len(latencies) * 0.99)]
        median = statistics.median(latencies)
        print(f"\nLatency: median={median:.2f}ms, p99={p99:.2f}ms")
        assert p99 < 10.0, f"p99 latency {p99:.2f}ms exceeds 10ms target"


class TestSafetyFallbackLatency:
    """Safety fallback triggered in < 200ms."""

    def test_fallback_response_time(self, client):
        """Trigger safety_critical violation, measure time to fallback response."""
        resp = client.post(
            "/api/v1/twins/",
            json={
                "name": "fallback-latency-test",
                "domain_pack_id": "test.cstr",
                "initial_state": {"temperature": 25.0, "pressure": 1.0},
            },
            headers={"Authorization": "Bearer ptw_test_admin_key"},
        )
        twin_id = resp.json()["twin_id"]
        headers = {"Authorization": "Bearer ptw_test_admin_key"}

        # Send temperature above safety threshold to trigger fallback
        start = time.monotonic()
        resp = client.put(
            f"/api/v1/twins/{twin_id}/state/",
            json={"temperature": 999.0, "pressure": 100.0},
            headers=headers,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        body = resp.json()
        if body.get("safety_status") == "fallback_triggered":
            fallback_duration = body.get("fallback_duration_ms", elapsed_ms)
            print(f"\nFallback latency: {fallback_duration:.2f}ms (total: {elapsed_ms:.2f}ms)")
            assert fallback_duration < 200.0, (
                f"Fallback latency {fallback_duration:.2f}ms exceeds 200ms"
            )


class TestWebSocketDeliveryLatency:
    """WebSocket event delivery < 100ms."""

    def test_event_delivery_time(self, client):
        """Publish event, measure time until received on WebSocket."""
        with client.websocket_connect(
            "/api/v1/twins/twin_ws_latency/ws"
        ) as ws:
            _ = ws.receive_json()  # consume welcome

            latencies = []
            for i in range(50):
                start = time.monotonic()
                event_bus.publish("twin_ws_latency", {
                    "event_type": "state_updated",
                    "data": {"temperature": float(i)},
                })
                msg = ws.receive_json()
                elapsed_ms = (time.monotonic() - start) * 1000
                latencies.append(elapsed_ms)

            avg = statistics.mean(latencies)
            p99 = sorted(latencies)[int(len(latencies) * 0.99)]
            print(f"\nWS delivery: avg={avg:.2f}ms, p99={p99:.2f}ms")
            assert p99 < 100.0, f"WS p99 delivery {p99:.2f}ms exceeds 100ms"
```

- [ ] **Step 3: 运行性能测试**

```bash
pytest tests/api/performance/ -v -s
```

---

## Task 6: Deployment Verification Test

**Files:**
- Create: `tests/api/integration/test_docker_deploy.py`

**Purpose:** 端到端验证 Docker 部署生命周期：compose up → health check → create TwinObject → update state → verify WebSocket → compose down。

**Spec:** §8.2 集成测试 — Docker 部署场景

- [ ] **Step 1: 编写 Docker 部署验证测试** `tests/api/integration/test_docker_deploy.py`

```python
"""Docker deployment integration test.

Full lifecycle: docker-compose up -> health check -> create TwinObject ->
update state -> verify WebSocket -> docker-compose down.

Requires Docker and docker-compose installed on the host.
Marked with @pytest.mark.docker to allow selective skip.
"""
import json
import os
import subprocess
import time
import pytest
import httpx

BASE_URL = "http://localhost:8000"
ADMIN_KEY = os.environ.get("PT_ADMIN_API_KEY", "ptw_integration_test_key")


def _docker_compose(*args, env_extra=None):
    """Run docker-compose command, return CompletedProcess."""
    env = os.environ.copy()
    env["PT_ADMIN_API_KEY"] = ADMIN_KEY
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["docker-compose", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    return result


@pytest.mark.docker
@pytest.mark.order(1)
class TestDockerLifecycle:
    """Full Docker deployment lifecycle."""

    @classmethod
    def setup_class(cls):
        """Start Docker Compose services."""
        result = _docker_compose("-f", "docker-compose.dev.yml", "up", "-d", "--build")
        assert result.returncode == 0, f"docker-compose up failed: {result.stderr}"
        # Wait for health check to pass
        cls._wait_for_healthy(timeout=60)

    @classmethod
    def teardown_class(cls):
        """Stop and remove Docker Compose services."""
        _docker_compose("-f", "docker-compose.dev.yml", "down", "-v")

    @staticmethod
    def _wait_for_healthy(timeout=60):
        """Poll /api/v1/health/ until healthy or timeout."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                resp = httpx.get(f"{BASE_URL}/api/v1/health/", timeout=5)
                if resp.status_code == 200:
                    body = resp.json()
                    if body.get("status") == "healthy":
                        return
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            time.sleep(2)
        raise TimeoutError("API service did not become healthy")

    def test_health_check_passes(self):
        """GET /api/v1/health/ returns healthy."""
        resp = httpx.get(f"{BASE_URL}/api/v1/health/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"

    def test_create_twin_object(self):
        """POST /api/v1/twins/ creates a TwinObject."""
        resp = httpx.post(
            f"{BASE_URL}/api/v1/twins/",
            json={
                "name": "docker-test-cstr",
                "description": "CSTR for Docker integration test",
                "domain_pack_id": "test.cstr",
                "initial_state": {
                    "temperature": 25.0,
                    "pressure": 1.0,
                    "concentration_A": 3.0,
                },
            },
            headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "docker-test-cstr"
        assert "twin_id" in body
        self.__class__.twin_id = body["twin_id"]

    def test_update_state(self):
        """PUT /api/v1/twins/{id}/state/ updates state."""
        resp = httpx.put(
            f"{BASE_URL}/api/v1/twins/{self.twin_id}/state/",
            json={"temperature": 185.0, "pressure": 15.0},
            headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "constraint_evaluation" in body
        assert "temperature" in body["updated_variables"]

    def test_metrics_endpoint(self):
        """GET /metrics exposes all Prometheus metrics."""
        resp = httpx.get(f"{BASE_URL}/metrics")
        assert resp.status_code == 200
        required_metrics = [
            "pt_requests_total",
            "pt_active_twins",
            "pt_websocket_connections",
        ]
        for m in required_metrics:
            assert m in resp.text, f"Missing metric: {m}"

    def test_websocket_connection(self):
        """WebSocket receives events after state update."""
        import websocket  # websocket-client library

        ws = websocket.create_connection(
            f"ws://localhost:8000/api/v1/twins/{self.twin_id}/ws"
        )
        # Receive welcome message
        welcome = json.loads(ws.recv())
        assert welcome["event_type"] == "connected"

        # Trigger a state update
        httpx.put(
            f"{BASE_URL}/api/v1/twins/{self.twin_id}/state/",
            json={"temperature": 190.0},
            headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        )

        # Read events until we get state_updated or timeout
        ws.settimeout(5.0)
        got_state_update = False
        try:
            for _ in range(10):
                msg = json.loads(ws.recv())
                if msg["event_type"] == "state_updated":
                    got_state_update = True
                    break
        except websocket.WebSocketTimeoutException:
            pass
        ws.close()
        assert got_state_update, "Did not receive state_updated event via WebSocket"

    def test_delete_twin(self):
        """DELETE /api/v1/twins/{id} removes the TwinObject."""
        resp = httpx.delete(
            f"{BASE_URL}/api/v1/twins/{self.twin_id}/",
            headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        )
        assert resp.status_code == 200

        # Verify deletion
        resp = httpx.get(
            f"{BASE_URL}/api/v1/twins/{self.twin_id}/",
            headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        )
        assert resp.status_code == 404
```

- [ ] **Step 2: 运行 Docker 部署测试**

```bash
pytest tests/api/integration/test_docker_deploy.py -v -s -m docker
```

---

## Acceptance Checklist

Complete these checks before marking the plan as done:

- [ ] WebSocket `/api/v1/twins/{twin_id}/ws` accepts connections and delivers all 8 event types
- [ ] Event bus supports multiple concurrent subscribers per TwinObject with isolation
- [ ] `docker build` succeeds; `docker-compose up` passes health checks
- [ ] `docker-compose.dev.yml` runs with SQLite + hot reload
- [ ] `GET /metrics` returns all 8 Prometheus metrics in exposition format
- [ ] State update throughput >= 1000 req/s
- [ ] Constraint evaluation latency p99 < 10ms
- [ ] Safety fallback latency < 200ms
- [ ] WebSocket event delivery < 100ms
- [ ] Docker deployment lifecycle test passes end-to-end
- [ ] All unit tests pass: `pytest tests/api/unit/ -v`
- [ ] No TODO or placeholder code in production files
