# M5: Core-Lab-Bridge 闭环集成

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 M1-M4 的所有组件集成到单一运行栈中，完成端到端四场景闭环验证。M5 完成后，五个闭环（§2.1-2.5）全部可运行、可测试、可验收。

**Architecture:** 五组件在单进程中运行，通过 Python 函数调用通信。FastAPI 暴露统一 REST API。四个端到端测试场景自动化运行，验证全链路正确性、性能、隔离有效性。

**Tech Stack:** Python 3.11+, FastAPI, PostgreSQL, httpx (test client)

**Spec reference:** §2.1-2.5 五闭环, §5 M5 验收

**Depends on:** M2 (Core), M3 (Lab), M4 (Bridge)

**Quality gate (M5-C1 ~ C4):**
- C1: 端到端闭环全程自动化 — 一键运行，无人工干预
- C2: 安全回落延迟 < 200ms — 从触发条件到回落指令
- C3: Bridge 输出更新延迟 < 1s — 从 Core 状态变化到新行动空间
- C4: 组件隔离有效 — Lab 向 Core 内部接口发请求 → 全部被拒绝

---

## File Structure

```
src/polytwin/api/
├── app.py                   # Task 1: FastAPI 应用 + 依赖注入
├── deps.py                  # Task 1: 组件实例化 + 注入
└── routes/
    ├── tom.py               # Task 2: TOM API 路由
    ├── core.py              # Task 3: Core API 路由
    ├── lab.py               # Task 4: Lab API 路由
    └── bridge.py            # Task 5: Bridge API 路由
tests/integration/
├── conftest.py              # Task 6: 集成测试配置（PostgreSQL + httpx client）
├── test_perception_loop.py  # Task 7: 感知闭环端到端
├── test_exploration_loop.py # Task 8: 探索闭环端到端
├── test_decision_loop.py   # Task 9: 决策闭环端到端
├── test_execution_loop.py  # Task 10: 执行闭环端到端
├── test_isolation.py        # Task 11: 组件隔离渗透测试（M5-C4）
└── test_performance.py      # Task 12: 性能基准测试（M5-C2, M5-C3）
```

---

## Task 1: FastAPI 应用 + 依赖注入

**Files:** `src/polytwin/api/app.py`, `src/polytwin/api/deps.py`

**依赖注入结构：**

```python
# deps.py
from polytwin.tom.store import PostgresTwinObjectStore
from polytwin.core.engine import ConstraintEngine
from polytwin.core.hardgate import HardGate
from polytwin.core.fallback import SafetyFallback
from polytwin.core.quarantine import SubmissionQuarantine
from polytwin.core.evidence import EvidenceAdmission
from polytwin.core.identity_monitor import IdentityMonitor
from polytwin.core.certification import ModelCertification
from polytwin.core.prescreen import PrescreenLibrary
from polytwin.core.audit import PostgresAuditWriter
from polytwin.lab.explorer import LabExplorer
from polytwin.lab.data_release import DataReleaseManager
from polytwin.bridge.orchestrator import BridgeOrchestrator
from polytwin.domainpack.registry import DomainPackRegistry

# 单例实例，生命周期与应用相同
_store = None
_engine = None
_registry = None
...

def get_store() -> TwinObjectStore: ...
def get_engine() -> ConstraintEngine: ...
def get_registry() -> DomainPackRegistry: ...
```

- [ ] **Step 1-5: TDD**

---

## Task 2-5: API 路由

每个 Task 实现一个路由模块，TDD 展开。

**Task 2: TOM 路由** — POST /objects, GET /objects/{id}, GET /objects/{id}/views/{type}, PATCH /objects/{id}, GET /objects/{id}/snapshots, POST /objects/{id}/snapshots

**Task 3: Core 路由** — POST /validate, POST /hardgate, POST /quarantine/submit, POST /fallback/execute, GET /audit, GET /identity/{id}

**Task 4: Lab 路由** — POST /explore/counterexample, POST /explore/hypothesis, POST /explore/correlation, POST /explore/counterfactual, GET /strategies, GET /data-release/{dp_id}

**Task 5: Bridge 路由** — POST /action-space, POST /decide, GET /roles, POST /human-response

- [ ] **每个 Task: Step 1-5 TDD**

---

## Task 6: 集成测试配置

**Files:** `tests/integration/conftest.py`

```python
@pytest_asyncio.fixture
async def api_client():
    """httpx AsyncClient 指向 FastAPI 应用，使用测试数据库。"""
    app = create_app(test_mode=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def loaded_domainpack():
    """加载 minimal-domain-pack.yaml 到 registry。"""
    ...
```

- [ ] **Step 1-5: TDD**

---

## Task 7: 感知闭环端到端

**Files:** `tests/integration/test_perception_loop.py`

**Spec §2.1 验收：**

```python
class TestPerceptionLoop:
    async def test_external_input_to_scene_match(self, api_client, loaded_domainpack):
        """外部输入 → TOM 创建对象 → 视图投影 → 场景匹配 → < 50ms"""
        # 1. 创建 TwinObject
        response = await api_client.post("/api/v1/tom/objects", json={
            "type": "device",
            "state_semantics": {
                "current_values": {"temperature": 150.0, "pressure": 25.0},
            },
        })
        assert response.status_code == 201
        obj_id = response.json()["id"]

        # 2. 获取视图
        response = await api_client.get(f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
            headers={"X-Caller-Component": "core_runtime", "X-Caller-Role": "engine"})
        assert response.status_code == 200
        assert "state_semantics" in response.json()
```

- [ ] **Step 1-5: TDD**

---

## Task 8: 探索闭环端到端

**Files:** `tests/integration/test_exploration_loop.py`

**Spec §2.2 验收：** Lab 从授权数据生成假设 → 假设带 falsification_tests → 假设带 reproducibility_manifest → 约束报告标注"预筛结果，非权威"

- [ ] **Step 1-5: TDD**

---

## Task 9: 决策闭环端到端

**Files:** `tests/integration/test_decision_loop.py`

**Spec §2.3 验收：** Lab 提交 → 检疫 → 证据准入 → HardGate → 写入 TwinObject → Bridge 构建行动空间 → 全链路可追溯

- [ ] **Step 1-5: TDD**

---

## Task 10: 执行闭环端到端

**Files:** `tests/integration/test_execution_loop.py`

**Spec §2.4 验收：** Bridge 行动 → 执行 → 状态更新 → Core 重新验证 → 约束违规触发安全回落 → 身份漂移触发 uncertain

- [ ] **Step 1-5: TDD**

---

## Task 11: 组件隔离渗透测试（M5-C4）

**Files:** `tests/integration/test_isolation.py`

```python
class TestComponentIsolation:
    async def test_lab_cannot_access_core_certification(self, api_client):
        """Lab 通过 API 尝试访问 Core 认证接口 → 被拒绝"""
        response = await api_client.post("/api/v1/core/certify",
            json={"model_id": "test"},
            headers={"X-Caller-Component": "lab", "X-Caller-Role": "explorer"})
        assert response.status_code == 403

    async def test_lab_cannot_see_core_runtime_view(self, api_client):
        """Lab 尝试获取 CoreRuntimeView → 被拒绝"""
        response = await api_client.get("/api/v1/tom/objects/test-obj/views/core_runtime",
            headers={"X-Caller-Component": "lab"})
        assert response.status_code == 403

    async def test_bridge_cannot_write_state(self, api_client):
        """Bridge 尝试直接修改 TwinObject 约束状态 → 被拒绝"""
        ...
```

- [ ] **Step 1-5: TDD**

---

## Task 12: 性能基准测试（M5-C2, M5-C3）

**Files:** `tests/integration/test_performance.py`

```python
class TestPerformance:
    async def test_safety_fallback_under_200ms(self, api_client):
        """M5-C2: safety_critical 违规到回落指令 < 200ms"""
        import time
        start = time.monotonic()
        response = await api_client.post("/api/v1/core/validate", json={
            "object_id": "test-obj",
            "domain_pack_id": "example.minimal_device_monitor",
            "state_values": {"temperature": 190.0},  # 超过 180 上限
        }, headers={"X-Caller-Component": "core_runtime"})
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 200

    async def test_bridge_update_under_1s(self, api_client):
        """M5-C3: Core 状态变化到 Bridge 新行动空间 < 1s"""
        ...
```

- [ ] **Step 1-5: TDD**

---

## M5 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M5-C1: 全程自动化** | `pytest tests/integration/ -v --tb=short` | 全部 PASSED，无人工干预 |
| **M5-C2: 安全回落 < 200ms** | `pytest tests/integration/test_performance.py::TestPerformance::test_safety_fallback_under_200ms -v` | PASSED |
| **M5-C3: Bridge 更新 < 1s** | `pytest tests/integration/test_performance.py::TestPerformance::test_bridge_update_under_1s -v` | PASSED |
| **M5-C4: 组件隔离** | `pytest tests/integration/test_isolation.py -v` | 全部被拒绝 |

---

## Jelly 集成任务 (Spec v2.1.0 §3.7)

> **详细设计**: `2026-05-08-jelly-mcp-client-integration.md §9`
> **Jelly Phase 依赖**: Phase 1-2 (Group 1/2/3)

### Jelly Task: 端到端集成测试含 Jelly mock + 可选真实连接

**Files:**
- Create: `tests/integration/test_jelly_integration.py`
- Modify: `src/polytwin/api/deps.py` — 注入 JellyClient

**目的:** 验证五闭环在 Jelly 数据源（mock 模式）下端到端可运行。可选：如果 Jelly MCP Server 可达，验证真实连接。

**测试场景:**

```python
# tests/integration/test_jelly_integration.py

async def test_perception_loop_with_jelly_domain_pack():
    """感知闭环：从 Jelly 获取 DomainPack → 创建 TwinObject → 场景匹配"""
    # JellyClient mock 模式返回本地 YAML
    # Registry.load_from_jelly("example.minimal_device_monitor") 成功
    # TwinObject 创建后正确匹配场景

async def test_exploration_loop_with_jelly_data():
    """探索闭环：Lab 从 Jelly 获取探索数据 → 生成假设 → 提交 Core"""
    # Lab 获取 Jelly mock 探索数据
    # 假设生成正常
    # Core 检疫和证据准入正常

async def test_jelly_graceful_degradation():
    """Jelly 不可达时系统完整降级"""
    # 强制 Jelly 连接失败
    # 所有五闭环仍可运行（使用本地数据）
    # 审计日志记录 jelly_mcp_call result="fallback_to_mock"

async def test_jelly_secondary_filter():
    """二次视图过滤兜底验证"""
    # Lab caller 获取 DomainPack → 不含 certifier.threshold
    # 即使 mock 返回了完整数据，view_filter 移除敏感字段
```

**deps.py 注入:**

```python
# src/polytwin/api/deps.py
def get_jelly_client() -> JellyClient:
    """从 EngineConfig 创建 JellyClient。mock 模式默认开启。"""
    return JellyClient(engine_config.jelly)
```
