# M10a: API 服务 — 应用框架与认证

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 FastAPI 应用骨架、健康检查端点、API Key 认证和 RBAC 授权，为后续 API 端点（M10b-M10d）奠定安全基础。

**Architecture:** FastAPI 单体应用，引擎作为 library 嵌入。认证采用 API Key + Bearer token 方案，RBAC 基于角色-操作权限矩阵。中间件层提取并验证 Key，依赖注入层执行权限检查，全局异常处理器将 PolymorphicTwinError 映射为标准 HTTP 响应。

**Spec reference:** `docs/superpowers/specs/2026-05-07-product-api-service.md` v1.0.0 §2.1, §3, §6

**Quality gate:** M10a 完成前：
- `GET /api/v1/health/` 返回 healthy 状态
- 无效/过期 Key 返回 401
- 越权操作返回 403
- 5 种角色权限与 Spec §3.3 矩阵完全一致
- 全部单元测试通过

---

## File Structure

```
polymorphic_twin/
├── api/
│   ├── __init__.py                                    # Task 1
│   ├── app.py                                         # Task 1
│   ├── config.py                                      # Task 1
│   ├── dependencies.py                                # Task 4
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                                    # Task 4
│   │   └── error_handler.py                           # Task 6
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py                                  # Task 2
│   └── auth/
│       ├── __init__.py
│       ├── models.py                                  # Task 3
│       ├── api_key.py                                 # Task 3
│       └── rbac.py                                    # Task 5
└── tests/
    └── api/
        └── unit/
            ├── test_health.py                         # Task 2
            ├── test_api_key.py                        # Task 3
            ├── test_auth.py                           # Task 4
            └── test_rbac.py                           # Task 5
```

---

## Task 1: FastAPI App Skeleton

**Files:**
- Create: `polymorphic_twin/api/__init__.py`
- Create: `polymorphic_twin/api/app.py`
- Create: `polymorphic_twin/api/config.py`
- Create: `polymorphic_twin/api/middleware/__init__.py`
- Create: `polymorphic_twin/api/routes/__init__.py`
- Create: `polymorphic_twin/api/auth/__init__.py`

**Purpose:** 创建 FastAPI 应用实例、CORS 中间件、环境变量配置加载、OpenAPI 文档配置。

- [ ] **Step 1: 创建 API 配置模型**

```python
# polymorphic_twin/api/config.py
"""API 服务配置 — 从环境变量加载。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class APIConfig(BaseModel):
    """API 服务配置。"""

    storage_backend: Literal["memory", "sqlite", "postgres"] = "memory"
    storage_url: str | None = None
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    admin_api_key: str = ""
    max_twins: int = 100
    cors_origins: str = ""  # 逗号分隔的允许来源

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
```

- [ ] **Step 2: 创建 FastAPI 应用**

```python
# polymorphic_twin/api/app.py
"""FastAPI 应用实例 — 中间件注册、路由挂载、生命周期管理。"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from polymorphic_twin.api.config import APIConfig
from polymorphic_twin.api.routes import health


def create_app(config: APIConfig | None = None) -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    if config is None:
        config = _config_from_env()

    app = FastAPI(
        title="Polymorphic-Twin API",
        description="数字孪生系统可信治理 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    if config.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 存储 app state
    app.state.config = config
    app.state.started_at = time.time()

    # 注册路由
    app.include_router(health.router)

    return app


def _config_from_env() -> APIConfig:
    """从环境变量构建 APIConfig。"""
    return APIConfig(
        storage_backend=os.getenv("PT_STORAGE_BACKEND", "memory"),
        storage_url=os.getenv("PT_STORAGE_URL"),
        log_level=os.getenv("PT_LOG_LEVEL", "INFO"),
        log_format=os.getenv("PT_LOG_FORMAT", "json"),
        admin_api_key=os.getenv("PT_ADMIN_API_KEY", ""),
        max_twins=int(os.getenv("PT_MAX_TWINS", "100")),
        cors_origins=os.getenv("PT_CORS_ORIGINS", ""),
    )


# uvicorn 入口用
app = create_app()
```

- [ ] **Step 3: 创建 __init__.py 文件**

```python
# polymorphic_twin/api/__init__.py
"""Polymorphic-Twin API 服务层。"""

from polymorphic_twin.api.app import app, create_app

__all__ = ["app", "create_app"]
```

空 `__init__.py` 文件:
- `polymorphic_twin/api/middleware/__init__.py`
- `polymorphic_twin/api/routes/__init__.py`
- `polymorphic_twin/api/auth/__init__.py`

- [ ] **Step 4: 验证应用启动**

```bash
pip install -e ".[dev]"
python -c "from polymorphic_twin.api import create_app; app = create_app(); print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/api/
git commit -m "feat(api): add FastAPI app skeleton with config and CORS"
```

---

## Task 2: Health Endpoint

**Files:**
- Create: `polymorphic_twin/api/routes/health.py`
- Create: `tests/api/unit/test_health.py`

**Purpose:** `GET /api/v1/health/` 返回服务健康状态。用于 Docker HEALTHCHECK 和负载均衡器探针。对应 Spec §6.4。

- [ ] **Step 1: 编写健康端点测试**

```python
# tests/api/unit/test_health.py
"""健康端点测试 — Spec §6.4。"""

from fastapi.testclient import TestClient

from polymorphic_twin.api.app import create_app
from polymorphic_twin.api.config import APIConfig


def _client() -> TestClient:
    config = APIConfig(storage_backend="memory")
    app = create_app(config)
    return TestClient(app)


def test_health_returns_200():
    client = _client()
    resp = client.get("/api/v1/health/")
    assert resp.status_code == 200


def test_health_response_structure():
    client = _client()
    resp = client.get("/api/v1/health/")
    body = resp.json()
    assert "status" in body
    assert "version" in body
    assert "storage" in body
    assert "active_twins" in body
    assert "uptime_seconds" in body


def test_health_status_is_healthy_for_memory():
    client = _client()
    resp = client.get("/api/v1/health/")
    body = resp.json()
    assert body["status"] in ("healthy", "degraded")
    assert body["version"] == "0.1.0"
    assert body["storage"] == "connected"
    assert body["active_twins"] == 0


def test_health_uptime_increases():
    client = _client()
    import time
    resp1 = client.get("/api/v1/health/")
    time.sleep(0.1)
    resp2 = client.get("/api/v1/health/")
    assert resp2.json()["uptime_seconds"] >= resp1.json()["uptime_seconds"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/api/unit/test_health.py -v
```

Expected: FAIL — 路由不存在

- [ ] **Step 3: 实现健康端点**

```python
# polymorphic_twin/api/routes/health.py
"""健康检查端点 — Spec §6.4。"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/")
async def health_check(request: Request) -> dict:
    """返回服务健康状态。"""
    app = request.app
    config = app.state.config
    started_at = app.state.started_at
    uptime = time.time() - started_at

    # 检查存储连接状态
    storage_status = _check_storage(config.storage_backend)

    status = "healthy"
    if storage_status != "connected":
        status = "degraded"

    return {
        "status": status,
        "version": "0.1.0",
        "storage": storage_status,
        "active_twins": 0,  # 后续 Task 从引擎获取
        "uptime_seconds": round(uptime, 1),
    }


def _check_storage(backend: str) -> str:
    """检查存储后端连接状态。"""
    if backend == "memory":
        return "connected"
    # sqlite / postgres 连接检查在后续 Task 实现
    return "connected"
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/api/unit/test_health.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/api/routes/health.py tests/api/unit/test_health.py
git commit -m "feat(api): add GET /api/v1/health/ endpoint"
```

---

## Task 3: API Key Model & Storage

**Files:**
- Create: `polymorphic_twin/api/auth/models.py`
- Create: `polymorphic_twin/api/auth/api_key.py`
- Create: `tests/api/unit/test_api_key.py`

**Purpose:** 定义 APIKey 数据模型、Key 生成（`ptw_` 前缀 + 32 字节随机数 base64）、哈希存储、验证逻辑。对应 Spec §3.1。

- [ ] **Step 1: 编写 API Key 测试**

```python
# tests/api/unit/test_api_key.py
"""API Key 生成与验证测试 — Spec §3.1。"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from polymorphic_twin.api.auth.api_key import (
    InMemoryAPIKeyStore,
    generate_api_key,
    hash_key,
)
from polymorphic_twin.api.auth.models import APIKey, Role


def test_generate_key_has_ptw_prefix():
    key, key_hash = generate_api_key("test", "user1", [Role.ADMIN])
    assert key.startswith("ptw_")


def test_generate_key_is_long_enough():
    key, key_hash = generate_api_key("test", "user1", [Role.ADMIN])
    # ptw_ (4) + base64(32 bytes) ~44 chars
    assert len(key) > 40


def test_key_hash_is_not_plaintext():
    key, key_hash = generate_api_key("test", "user1", [Role.ADMIN])
    assert key_hash != key
    assert key not in key_hash


def test_hash_key_deterministic():
    h1 = hash_key("ptw_testkey123")
    h2 = hash_key("ptw_testkey123")
    assert h1 == h2


def test_hash_key_different_inputs():
    h1 = hash_key("ptw_key1")
    h2 = hash_key("ptw_key2")
    assert h1 != h2


def test_apikey_model_defaults():
    api_key = APIKey(
        key_id="kid_001",
        key_hash="hashed",
        name="test-key",
        user_id="user1",
        roles=[Role.VIEWER],
        created_at=datetime.now(timezone.utc),
    )
    assert api_key.expires_at is None
    assert api_key.last_used_at is None
    assert api_key.is_expired is False


def test_apikey_model_expired():
    api_key = APIKey(
        key_id="kid_002",
        key_hash="hashed",
        name="expired-key",
        user_id="user1",
        roles=[Role.VIEWER],
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    assert api_key.is_expired is True


def test_store_add_and_lookup():
    store = InMemoryAPIKeyStore()
    key, key_hash = generate_api_key("test", "user1", [Role.OPERATOR])
    api_key = store.add(key_hash, "test", "user1", [Role.OPERATOR])
    assert api_key is not None
    assert api_key.key_id

    found = store.lookup_by_key(key)
    assert found is not None
    assert Role.OPERATOR in found.roles


def test_store_lookup_invalid_key():
    store = InMemoryAPIKeyStore()
    assert store.lookup_by_key("ptw_invalid") is None


def test_store_lookup_expired_key():
    store = InMemoryAPIKeyStore()
    key, key_hash = generate_api_key("test", "user1", [Role.VIEWER])
    api_key = store.add(
        key_hash, "test", "user1", [Role.VIEWER],
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    found = store.lookup_by_key(key)
    # 过期 Key 返回 None
    assert found is None


def test_all_five_roles_exist():
    roles = [Role.ADMIN, Role.OPERATOR, Role.VIEWER, Role.DOMAIN_EXPERT, Role.AUDITOR]
    assert len(roles) == 5
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/api/unit/test_api_key.py -v
```

- [ ] **Step 3: 实现 API Key 模型**

```python
# polymorphic_twin/api/auth/models.py
"""认证数据模型 — API Key、角色。Spec §3.1, §3.2。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    """RBAC 角色 — Spec §3.2。"""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    DOMAIN_EXPERT = "domain_expert"
    AUDITOR = "auditor"


class APIKey(BaseModel):
    """API Key 数据模型 — Spec §3.1。"""

    key_id: str
    key_hash: str
    name: str
    user_id: str
    roles: list[Role]
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = datetime.now(self.expires_at.tzinfo)
        return now > self.expires_at
```

- [ ] **Step 4: 实现 API Key 生成与存储**

```python
# polymorphic_twin/api/auth/api_key.py
"""API Key 生成、哈希、存储。Spec §3.1。"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timezone

from polymorphic_twin.api.auth.models import APIKey, Role


def hash_key(plaintext_key: str) -> str:
    """对 API Key 明文做 SHA-256 哈希。永存哈希，不存明文。"""
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()


def generate_api_key(
    name: str,
    user_id: str,
    roles: list[Role],
    expires_at: datetime | None = None,
) -> tuple[str, str]:
    """生成 API Key。

    返回 (明文 key, key_hash)。
    明文只在创建时显示一次，之后只存哈希。
    格式: ptw_ + base64(32 bytes random)
    """
    raw = secrets.token_bytes(32)
    plaintext = "ptw_" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    key_hash = hash_key(plaintext)
    return plaintext, key_hash


class InMemoryAPIKeyStore:
    """内存 API Key 存储（开发用，生产替换为数据库）。"""

    def __init__(self) -> None:
        # key_hash -> APIKey
        self._keys: dict[str, APIKey] = {}

    def add(
        self,
        key_hash: str,
        name: str,
        user_id: str,
        roles: list[Role],
        expires_at: datetime | None = None,
    ) -> APIKey:
        """添加 API Key 记录。"""
        api_key = APIKey(
            key_id=f"key_{uuid.uuid4().hex[:12]}",
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            roles=roles,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        self._keys[key_hash] = api_key
        return api_key

    def lookup_by_key(self, plaintext_key: str) -> APIKey | None:
        """根据明文 Key 查找。返回有效 Key 或 None（无效/过期）。"""
        key_hash = hash_key(plaintext_key)
        api_key = self._keys.get(key_hash)
        if api_key is None:
            return None
        if api_key.is_expired:
            return None
        # 更新 last_used_at
        api_key.last_used_at = datetime.now(timezone.utc)
        return api_key

    def get_by_key_id(self, key_id: str) -> APIKey | None:
        """根据 key_id 查找。"""
        for api_key in self._keys.values():
            if api_key.key_id == key_id:
                return api_key
        return None

    def delete(self, key_id: str) -> bool:
        """删除指定 key_id 的 Key。"""
        for key_hash, api_key in list(self._keys.items()):
            if api_key.key_id == key_id:
                del self._keys[key_hash]
                return True
        return False

    def list_by_user(self, user_id: str) -> list[APIKey]:
        """列出指定用户的所有 Key。"""
        return [k for k in self._keys.values() if k.user_id == user_id]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/api/unit/test_api_key.py -v
```

Expected: 12 passed

- [ ] **Step 6: Commit**

```bash
git add polymorphic_twin/api/auth/ tests/api/unit/test_api_key.py
git commit -m "feat(api): add API Key model, generation, hashing, and in-memory store"
```

---

## Task 4: Auth Middleware

**Files:**
- Create: `polymorphic_twin/api/middleware/auth.py`
- Create: `polymorphic_twin/api/dependencies.py`
- Create: `tests/api/unit/test_auth.py`

**Purpose:** 从 Authorization: Bearer <key> 提取 token，验证 Key 有效性，注入当前用户到请求上下文。无效/过期 Key 返回 401。对应 Spec §3.1, §3.4 AUTH-01/02/05。

- [ ] **Step 1: 编写认证中间件测试**

```python
# tests/api/unit/test_auth.py
"""认证中间件测试 — Spec §3.1, §3.4 AUTH-01/02/05。"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from polymorphic_twin.api.auth.api_key import (
    InMemoryAPIKeyStore,
    generate_api_key,
)
from polymorphic_twin.api.auth.models import Role
from polymorphic_twin.api.dependencies import (
    RequireAdmin,
    RequireOperator,
    RequireViewer,
    create_auth_dependency,
)
from polymorphic_twin.api.middleware.auth import AuthMiddleware


def _make_app(store: InMemoryAPIKeyStore) -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/test/public")
    async def public():
        return {"msg": "ok"}

    @app.get("/api/v1/test/protected")
    async def protected(user=Depends(create_auth_dependency(store))):
        return {"user_id": user.user_id, "roles": [r.value for r in user.roles]}

    @app.get("/api/v1/test/admin-only")
    async def admin_only(user=Depends(RequireAdmin(store))):
        return {"user_id": user.user_id}

    @app.get("/api/v1/test/viewer-ok")
    async def viewer_ok(user=Depends(RequireViewer(store))):
        return {"user_id": user.user_id}

    return app


@pytest.fixture
def store():
    return InMemoryAPIKeyStore()


@pytest.fixture
def admin_key(store):
    key, key_hash = generate_api_key("admin-key", "admin-user", [Role.ADMIN])
    store.add(key_hash, "admin-key", "admin-user", [Role.ADMIN])
    return key


@pytest.fixture
def viewer_key(store):
    key, key_hash = generate_api_key("viewer-key", "viewer-user", [Role.VIEWER])
    store.add(key_hash, "viewer-key", "viewer-user", [Role.VIEWER])
    return key


@pytest.fixture
def expired_key(store):
    key, key_hash = generate_api_key("expired-key", "expired-user", [Role.VIEWER])
    store.add(
        key_hash, "expired-key", "expired-user", [Role.VIEWER],
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    return key


def test_public_endpoint_no_auth_needed(store):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get("/api/v1/test/public")
    assert resp.status_code == 200


def test_protected_endpoint_with_valid_key(store, admin_key):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/test/protected",
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "admin-user"


def test_protected_endpoint_no_auth(store):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get("/api/v1/test/protected")
    assert resp.status_code == 401


def test_protected_endpoint_invalid_key(store):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/test/protected",
        headers={"Authorization": "Bearer ptw_invalidkey123"},
    )
    assert resp.status_code == 401


def test_protected_endpoint_expired_key(store, expired_key):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/test/protected",
        headers={"Authorization": f"Bearer {expired_key}"},
    )
    assert resp.status_code == 401


def test_admin_only_with_admin_key(store, admin_key):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    assert resp.status_code == 200


def test_admin_only_with_viewer_key(store, viewer_key):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {viewer_key}"},
    )
    assert resp.status_code == 403


def test_viewer_endpoint_with_viewer_key(store, viewer_key):
    app = _make_app(store)
    client = TestClient(app)
    resp = client.get(
        "/api/v1/test/viewer-ok",
        headers={"Authorization": f"Bearer {viewer_key}"},
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/api/unit/test_auth.py -v
```

- [ ] **Step 3: 实现认证中间件**

```python
# polymorphic_twin/api/middleware/auth.py
"""API Key 认证中间件 — Bearer token 提取与验证。"""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    """请求级认证中间件（可选，用于全局拦截）。"""

    # 不需要认证的路径前缀
    PUBLIC_PATHS = frozenset({
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health/",
    })

    async def dispatch(self, request: Request, call_next):
        # 认证逻辑在 dependencies 中处理，这里只放行
        response = await call_next(request)
        return response
```

- [ ] **Step 4: 实现认证依赖注入**

```python
# polymorphic_twin/api/dependencies.py
"""FastAPI 依赖注入 — 认证、角色检查。"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from polymorphic_twin.api.auth.api_key import InMemoryAPIKeyStore
from polymorphic_twin.api.auth.models import APIKey, Role
from polymorphic_twin.api.auth.rbac import has_permission

_bearer_scheme = HTTPBearer(auto_error=False)


def create_auth_dependency(store: InMemoryAPIKeyStore):
    """创建认证依赖 — 验证 Bearer token 并返回 APIKey。"""
    async def _auth(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> APIKey:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
            )
        api_key = store.lookup_by_key(credentials.credentials)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        return api_key
    return _auth


def create_role_dependency(store: InMemoryAPIKeyStore, *allowed_roles: Role):
    """创建角色检查依赖 — 验证 Key 且角色在 allowed_roles 中。"""
    async def _check(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> APIKey:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
            )
        api_key = store.lookup_by_key(credentials.credentials)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        if not any(role in allowed_roles for role in api_key.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {api_key.roles} not allowed. Required: {[r.value for r in allowed_roles]}",
            )
        return api_key
    return _check


def RequireAdmin(store: InMemoryAPIKeyStore):
    return create_role_dependency(store, Role.ADMIN)

def RequireOperator(store: InMemoryAPIKeyStore):
    return create_role_dependency(store, Role.ADMIN, Role.OPERATOR)

def RequireViewer(store: InMemoryAPIKeyStore):
    return create_role_dependency(store, Role.ADMIN, Role.OPERATOR, Role.VIEWER, Role.AUDITOR)

def RequireDomainExpert(store: InMemoryAPIKeyStore):
    return create_role_dependency(store, Role.ADMIN, Role.DOMAIN_EXPERT)

def RequireAuditor(store: InMemoryAPIKeyStore):
    return create_role_dependency(store, Role.ADMIN, Role.AUDITOR)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/api/unit/test_auth.py -v
```

Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add polymorphic_twin/api/middleware/auth.py polymorphic_twin/api/dependencies.py tests/api/unit/test_auth.py
git commit -m "feat(api): add Bearer token auth middleware and role-based dependencies"
```

---

## Task 5: RBAC Permission Checker

**Files:**
- Create: `polymorphic_twin/api/auth/rbac.py`
- Create: `tests/api/unit/test_rbac.py`

**Purpose:** 实现 5 角色 × 14 操作权限矩阵（Spec §3.3），提供 `require_permission(action)` 依赖和 `has_permission()` 查询函数。

- [ ] **Step 1: 编写 RBAC 测试**

```python
# tests/api/unit/test_rbac.py
"""RBAC 权限矩阵测试 — Spec §3.3。"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from polymorphic_twin.api.auth.api_key import (
    InMemoryAPIKeyStore,
    generate_api_key,
)
from polymorphic_twin.api.auth.models import Role
from polymorphic_twin.api.auth.rbac import Action, has_permission, require_permission
from polymorphic_twin.api.dependencies import create_auth_dependency


# --- has_permission 单元测试 ---

class TestHasPermission:
    def test_admin_can_do_everything(self):
        for action in Action:
            assert has_permission(Role.ADMIN, action) is True

    def test_viewer_can_only_view(self):
        assert has_permission(Role.VIEWER, Action.VIEW_TWIN) is True
        assert has_permission(Role.VIEWER, Action.CREATE_TWIN) is False
        assert has_permission(Role.VIEWER, Action.UPDATE_STATE) is False
        assert has_permission(Role.VIEWER, Action.UPLOAD_DOMAIN_PACK) is False
        assert has_permission(Role.VIEWER, Action.VIEW_AUDIT_LOG) is False

    def test_operator_permissions(self):
        assert has_permission(Role.OPERATOR, Action.UPDATE_STATE) is True
        assert has_permission(Role.OPERATOR, Action.TRIGGER_VALIDATION) is True
        assert has_permission(Role.OPERATOR, Action.GENERATE_ACTION_SPACE) is True
        assert has_permission(Role.OPERATOR, Action.RESPOND_ACTION) is True
        assert has_permission(Role.OPERATOR, Action.START_LAB_EXPLORATION) is True
        assert has_permission(Role.OPERATOR, Action.VIEW_TWIN) is True
        # 不能做管理操作
        assert has_permission(Role.OPERATOR, Action.MANAGE_API_KEYS) is False
        assert has_permission(Role.OPERATOR, Action.CREATE_TWIN) is False
        assert has_permission(Role.OPERATOR, Action.DELETE_TWIN) is False

    def test_domain_expert_permissions(self):
        assert has_permission(Role.DOMAIN_EXPERT, Action.UPLOAD_DOMAIN_PACK) is True
        assert has_permission(Role.DOMAIN_EXPERT, Action.VALIDATE_DOMAIN_PACK) is True
        assert has_permission(Role.DOMAIN_EXPERT, Action.ACTIVATE_DEACTIVATE) is True
        # 不能操作 TwinObject
        assert has_permission(Role.DOMAIN_EXPERT, Action.UPDATE_STATE) is False
        assert has_permission(Role.DOMAIN_EXPERT, Action.VIEW_TWIN) is False

    def test_auditor_permissions(self):
        assert has_permission(Role.AUDITOR, Action.VIEW_AUDIT_LOG) is True
        assert has_permission(Role.AUDITOR, Action.EXPORT_AUDIT_LOG) is True
        assert has_permission(Role.AUDITOR, Action.VIEW_TWIN) is True
        # 不能修改任何数据
        assert has_permission(Role.AUDITOR, Action.UPDATE_STATE) is False
        assert has_permission(Role.AUDITOR, Action.CREATE_TWIN) is False
        assert has_permission(Role.AUDITOR, Action.UPLOAD_DOMAIN_PACK) is False


# --- require_permission 集成测试 ---

def _make_app_with_permission(store: InMemoryAPIKeyStore, action: Action):
    app = FastAPI()
    auth_dep = create_auth_dependency(store)

    @app.get("/api/v1/test/action")
    async def do_action(user=Depends(require_permission(store, action))):
        return {"user_id": user.user_id}

    return app


@pytest.fixture
def store_with_keys():
    store = InMemoryAPIKeyStore()
    roles_and_keys = {}
    for role in Role:
        key, key_hash = generate_api_key(f"{role.value}-key", f"{role.value}-user", [role])
        store.add(key_hash, f"{role.value}-key", f"{role.value}-user", [role])
        roles_and_keys[role] = key
    return store, roles_and_keys


def test_viewer_forbidden_from_create_twin(store_with_keys):
    store, keys = store_with_keys
    app = _make_app_with_permission(store, Action.CREATE_TWIN)
    client = TestClient(app)

    resp = client.get(
        "/api/v1/test/action",
        headers={"Authorization": f"Bearer {keys[Role.VIEWER]}"},
    )
    assert resp.status_code == 403


def test_operator_allowed_to_update_state(store_with_keys):
    store, keys = store_with_keys
    app = _make_app_with_permission(store, Action.UPDATE_STATE)
    client = TestClient(app)

    resp = client.get(
        "/api/v1/test/action",
        headers={"Authorization": f"Bearer {keys[Role.OPERATOR]}"},
    )
    assert resp.status_code == 200


def test_all_14_actions_exist():
    assert len(Action) == 14


def test_permission_matrix_completeness():
    """验证每个角色×操作组合都有明确结果。"""
    for role in Role:
        for action in Action:
            result = has_permission(role, action)
            assert isinstance(result, bool)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/api/unit/test_rbac.py -v
```

- [ ] **Step 3: 实现 RBAC 权限矩阵**

```python
# polymorphic_twin/api/auth/rbac.py
"""RBAC 权限矩阵 — Spec §3.3 (5 角色 × 14 操作)。"""

from __future__ import annotations

from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from polymorphic_twin.api.auth.api_key import InMemoryAPIKeyStore
from polymorphic_twin.api.auth.models import APIKey, Role


class Action(str, Enum):
    """14 种 API 操作 — Spec §3.3 权限矩阵行。"""

    MANAGE_API_KEYS = "manage_api_keys"
    CREATE_TWIN = "create_twin"
    DELETE_TWIN = "delete_twin"
    UPDATE_STATE = "update_state"
    TRIGGER_VALIDATION = "trigger_validation"
    GENERATE_ACTION_SPACE = "generate_action_space"
    RESPOND_ACTION = "respond_action"
    START_LAB_EXPLORATION = "start_lab_exploration"
    VIEW_TWIN = "view_twin"
    UPLOAD_DOMAIN_PACK = "upload_domain_pack"
    VALIDATE_DOMAIN_PACK = "validate_domain_pack"
    ACTIVATE_DEACTIVATE = "activate_deactivate"
    VIEW_AUDIT_LOG = "view_audit_log"
    EXPORT_AUDIT_LOG = "export_audit_log"


# 权限矩阵: role -> set of allowed actions
# Spec §3.3
_PERMISSION_MATRIX: dict[Role, set[Action]] = {
    Role.ADMIN: set(Action),  # 全部
    Role.OPERATOR: {
        Action.UPDATE_STATE,
        Action.TRIGGER_VALIDATION,
        Action.GENERATE_ACTION_SPACE,
        Action.RESPOND_ACTION,
        Action.START_LAB_EXPLORATION,
        Action.VIEW_TWIN,
    },
    Role.VIEWER: {
        Action.VIEW_TWIN,
    },
    Role.DOMAIN_EXPERT: {
        Action.UPLOAD_DOMAIN_PACK,
        Action.VALIDATE_DOMAIN_PACK,
        Action.ACTIVATE_DEACTIVATE,
    },
    Role.AUDITOR: {
        Action.VIEW_TWIN,
        Action.VIEW_AUDIT_LOG,
        Action.EXPORT_AUDIT_LOG,
    },
}


def has_permission(role: Role, action: Action) -> bool:
    """检查指定角色是否有指定操作的权限。"""
    return action in _PERMISSION_MATRIX.get(role, set())


def check_permission(api_key: APIKey, action: Action) -> bool:
    """检查 API Key 的任意角色是否有权限。"""
    return any(has_permission(role, action) for role in api_key.roles)


_bearer_scheme = HTTPBearer(auto_error=False)


def require_permission(store: InMemoryAPIKeyStore, action: Action):
    """创建 FastAPI 依赖 — 验证 Key 且有指定操作权限。"""
    async def _check(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> APIKey:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
            )
        api_key = store.lookup_by_key(credentials.credentials)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        if not check_permission(api_key, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied for action '{action.value}'. "
                       f"Your roles: {[r.value for r in api_key.roles]}",
            )
        return api_key
    return _check
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/api/unit/test_rbac.py -v
```

Expected: 20+ passed

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/api/auth/rbac.py tests/api/unit/test_rbac.py
git commit -m "feat(api): add RBAC permission matrix (5 roles x 14 actions) per Spec §3.3"
```

---

## Task 6: Global Error Handler

**Files:**
- Create: `polymorphic_twin/api/middleware/error_handler.py`

**Purpose:** 将 PolymorphicTwinError 子类映射为 HTTP 状态码，统一 JSON 错误响应格式。对应 Spec §2.2 验收点中的 401/403/404/422 响应。

- [ ] **Step 1: 实现全局异常处理器**

```python
# polymorphic_twin/api/middleware/error_handler.py
"""全局异常处理器 — 将 PolymorphicTwinError 映射为 HTTP 响应。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from polymorphic_twin.exceptions import (
    PolymorphicTwinError,
    ValidationError,
    PermissionDeniedError,
    DomainPackNotFoundError,
    TwinObjectNotFoundError,
    InvalidStateError,
    ConstraintViolationError,
    SafetyFallbackTriggeredError,
)


def _error_body(error_code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {
        "error_code": error_code,
        "message": message,
    }
    if details:
        body["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    """在 FastAPI app 上注册全局异常处理器。"""

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content=_error_body(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_error_handler(request: Request, exc: PermissionDeniedError):
        return JSONResponse(
            status_code=403,
            content=_error_body(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(DomainPackNotFoundError)
    async def domain_pack_not_found_handler(request: Request, exc: DomainPackNotFoundError):
        return JSONResponse(
            status_code=404,
            content=_error_body(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(TwinObjectNotFoundError)
    async def twin_not_found_handler(request: Request, exc: TwinObjectNotFoundError):
        return JSONResponse(
            status_code=404,
            content=_error_body(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(InvalidStateError)
    async def invalid_state_handler(request: Request, exc: InvalidStateError):
        return JSONResponse(
            status_code=422,
            content=_error_body(
                exc.error_code, exc.message,
                {"variable": exc.variable_name, "expected_range": list(exc.expected_range)},
            ),
        )

    @app.exception_handler(ConstraintViolationError)
    async def constraint_violation_handler(request: Request, exc: ConstraintViolationError):
        return JSONResponse(
            status_code=409,
            content=_error_body(
                exc.error_code, exc.message,
                {"violated_constraints": exc.violated_constraints},
            ),
        )

    @app.exception_handler(SafetyFallbackTriggeredError)
    async def safety_fallback_handler(request: Request, exc: SafetyFallbackTriggeredError):
        return JSONResponse(
            status_code=200,  # 安全回落不是错误，返回 200 + 回落信息
            content=_error_body(
                exc.error_code, exc.message,
                {"fallback_action": exc.fallback_action, "reason": exc.reason},
            ),
        )

    @app.exception_handler(PolymorphicTwinError)
    async def generic_error_handler(request: Request, exc: PolymorphicTwinError):
        return JSONResponse(
            status_code=500,
            content=_error_body(exc.error_code, exc.message, exc.details),
        )
```

- [ ] **Step 2: 在 app.py 中注册异常处理器**

在 `polymorphic_twin/api/app.py` 的 `create_app` 函数中，路由注册之前添加:

```python
from polymorphic_twin.api.middleware.error_handler import register_error_handlers

# 在 create_app() 中，app.state 之后、路由注册之前:
register_error_handlers(app)
```

- [ ] **Step 3: 运行全部测试确认无回归**

```bash
pytest tests/api/ -v
```

Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add polymorphic_twin/api/middleware/error_handler.py polymorphic_twin/api/app.py
git commit -m "feat(api): add global error handler mapping PolymorphicTwinError to HTTP responses"
```

---

## Quality Gate Checklist

M10a 完成后，逐项验证:

- [ ] `GET /api/v1/health/` 返回 `{status: "healthy", version, storage, active_twins, uptime_seconds}`
- [ ] 无 Authorization header 返回 401
- [ ] 无效 Key 返回 401
- [ ] 过期 Key 返回 401 (AUTH-05)
- [ ] 有效 Key + 正确角色返回 200
- [ ] 有效 Key + 错误角色返回 403
- [ ] 5 种角色 × 14 操作权限与 Spec §3.3 矩阵完全一致 (AUTH-03, AUTH-04)
- [ ] PolymorphicTwinError 子类正确映射为 422/403/404/409/500
- [ ] `pytest tests/api/ -v` 全部通过
- [ ] OpenAPI 文档在 `/docs` 可访问
