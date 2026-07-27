# M7: 系统化与生产就绪

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从 alpha 推进到可外部部署的 beta 状态。完成性能优化、安全渗透测试、完整文档。

**Architecture:** 无新架构。优化现有组件性能，加固安全边界，完善文档和运维手册。

**Spec reference:** §5 M7 验收

**Depends on:** M6 (多场景验证通过)

**Quality gate (M7-C1 ~ C3):**
- C1: 安全渗透测试 — 渗透尝试全部被检测并阻止
- C2: 性能基准达标 — Core 约束验证 < 10ms, Bridge 行动空间生成 < 500ms, 视图投影 < 50ms
- C3: 文档完整性 — 所有文档无缺失，所有示例可运行

---

## File Structure

```
tests/
├── performance/
│   ├── test_core_performance.py       # Task 1
│   ├── test_bridge_performance.py     # Task 1
│   └── test_tom_performance.py        # Task 1
├── security/
│   ├── test_view_isolation_pentest.py # Task 2
│   ├── test_lab_quarantine_pentest.py # Task 3
│   ├── test_audit_immutability.py     # Task 4
│   └── test_constraint_boundary.py   # Task 5
docker/
├── Dockerfile                         # Task 6
└── docker-compose.yml                 # Task 6
docs/
├── api/                               # Task 7: API 文档（自动生成 + 人工审核）
├── ops/                               # Task 8: 运维手册
└── developer/                         # Task 9: 开发者文档
```

---

## Task 1: 性能基准与优化

**Files:** `tests/performance/test_core_performance.py`, `test_bridge_performance.py`, `test_tom_performance.py`

**M7-C2 目标：**

| 接口 | p50 | p95 | p99 | 测试方法 |
|------|-----|-----|-----|----------|
| Core 约束验证（≤10 条约束） | < 5ms | < 8ms | < 10ms | 构造 TwinObject + 10 条约束卡片，运行 1000 次 |
| Bridge 行动空间生成 | < 200ms | < 350ms | < 500ms | 构造 BridgeDecisionView + 5 个行动模板，运行 100 次 |
| TOM 视图投影 | < 10ms | < 30ms | < 50ms | get_view 五种视图各 1000 次 |
| TOM 创建对象 | < 20ms | < 40ms | < 50ms | POST + 写入 PostgreSQL，运行 500 次 |
| 快照创建 | < 30ms | < 50ms | < 80ms | 深拷贝 + hash + 写入 PostgreSQL |

**优化策略（按需）：**
- Core evaluator: 缓存已解析的 domain_of_validity 条件
- TOM 视图投影: 预编译投影规则
- Bridge: 缓存 DomainPack 查询结果

- [ ] **Step 1-5: TDD — 每个基准测试跑 100+ 次取 p50/p95/p99**

---

## Task 2: 视图隔离渗透测试

**Files:** `tests/security/test_view_isolation_pentest.py`

**M7-C1: 未参与开发的人员尝试绕过视图投影**

```python
class TestViewIsolationPentest:
    async def test_lab_forge_caller_identity(self, api_client):
        """伪造 CallerIdentity 尝试访问 CoreRuntimeView"""
        response = await api_client.get("/api/v1/tom/objects/{id}/views/core_runtime",
            headers={"X-Caller-Component": "lab", "X-Caller-Role": "explorer"})
        assert response.status_code == 403

    async def test_lab_modify_view_type_param(self, api_client):
        """尝试通过参数注入获取其他视图"""
        for view in ["core_runtime", "core_certification", "audit"]:
            response = await api_client.get(f"/api/v1/tom/objects/{id}/views/{view}",
                headers={"X-Caller-Component": "lab"})
            assert response.status_code == 403

    async def test_bridge_access_lab_view(self, api_client):
        """Bridge 尝试获取 LabExplorationView"""
        response = await api_client.get("/api/v1/tom/objects/{id}/views/lab_exploration",
            headers={"X-Caller-Component": "bridge"})
        assert response.status_code == 403

    async def test_direct_internal_access_via_api(self, api_client):
        """尝试通过 API 直接访问 TwinObject 内部数据（非视图接口）"""
        response = await api_client.get("/api/v1/tom/objects/{id}/internal")
        assert response.status_code == 404  # 此接口不存在
```

- [ ] **Step 1-5: TDD**

---

## Task 3: Lab 检疫渗透测试

**Files:** `tests/security/test_lab_quarantine_pentest.py`

```python
class TestLabQuarantinePentest:
    async def test_submit_payload_with_hidden_set_trace(self, api_client):
        """提交包含隐藏验证集痕迹的载荷"""
        response = await api_client.post("/api/v1/core/quarantine/submit",
            json={"items": [{"constraint_violation_report": "hidden_challenge_set matched"}]},
            headers={"X-Caller-Component": "lab"})
        assert response.status_code == 400  # sensitive_info_detected

    async def test_submit_oversized_payload(self, api_client):
        """提交超过 10MB 的载荷"""
        big_payload = "x" * (11 * 1024 * 1024)
        response = await api_client.post("/api/v1/core/quarantine/submit",
            json={"items": [{"data": big_payload}]},
            headers={"X-Caller-Component": "lab"})
        assert response.status_code == 400  # payload_too_large
```

- [ ] **Step 1-5: TDD**

---

## Task 4: 审计日志不可篡改测试

**Files:** `tests/security/test_audit_immutability.py`

```python
class TestAuditImmutability:
    async def test_audit_records_cannot_be_deleted(self, db_session):
        """尝试删除审计记录 → 被拒绝"""
        ...

    async def test_audit_records_cannot_be_modified(self, db_session):
        """尝试修改审计记录 → 被拒绝"""
        ...

    async def test_change_history_append_only(self, db_session):
        """变更历史只能追加"""
        ...
```

- [ ] **Step 1-5: TDD**

---

## Task 5: 约束边界测试

**Files:** `tests/security/test_constraint_boundary.py`

测试约束求值器在边界条件下的行为：
- domain_of_validity 变量缺失时的保守求值
- safety_critical 约束在 not_applicable 状态下不触发回落
- HardGate 在不确定情况下的保守拒绝

- [ ] **Step 1-5: TDD**

---

## Task 6: Docker 部署配置

**Files:** `docker/Dockerfile`, `docker/docker-compose.yml`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[lab-ml,dev]"
COPY src/ src/
COPY configs/ configs/
COPY migrations/ migrations/
CMD ["uvicorn", "polytwin.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  api:
    build: ..
    ports: ["8000:8000"]
    depends_on: [postgres]
    environment:
      DATABASE_URL: postgresql+asyncpg://polytwin:polytwin@postgres:5432/polytwin
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: polytwin
      POSTGRES_USER: polytwin
      POSTGRES_PASSWORD: polytwin
    volumes: [pgdata:/var/lib/postgresql/data]
volumes:
  pgdata:
```

- [ ] **Step 1: 编写 Dockerfile 和 docker-compose.yml**
- [ ] **Step 2: docker-compose up 验证**
- [ ] **Step 3: Commit**

---

## Task 7: API 文档

**Files:** `docs/api/` — 由 FastAPI 自动生成 OpenAPI spec，人工审核确认与实现一致。

- [ ] **Step 1: 确认 FastAPI 自动文档可访问** `http://localhost:8000/docs`
- [ ] **Step 2: 导出 OpenAPI spec** → `docs/api/openapi.json`
- [ ] **Step 3: 人工审核确认一致性**

---

## Task 8: 运维手册

**Files:** `docs/ops/README.md`

**内容：**
- 部署架构和依赖
- 启动/停止/重启流程
- 监控指标和告警阈值
- DomainPack 热更新流程
- 身份分叉/重建的人工审批流程
- 故障恢复流程

- [ ] **Step 1: 编写运维手册**

---

## Task 9: 开发者文档

**Files:** `docs/developer/`

**内容：**
- 架构设计文档（本文档的工程化版本）
- DomainPack 创建指南（面向领域专家）
- 约束卡片 certifier 开发指南
- Lab 策略开发指南
- 集成测试指南

- [ ] **Step 1: 编写开发者文档**

---

## M7 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M7-C1: 渗透测试** | `pytest tests/security/ -v` | 全部被阻止 |
| **M7-C2: 性能达标** | `pytest tests/performance/ -v` | p99 全部在目标内 |
| **M7-C3: 文档完整** | 人工检查 | 无缺失，示例可运行 |

---

## 全项目交付清单

| 产物 | 位置 | 状态 |
|------|------|------|
| 理论框架文档 | `docs/framework/` | M0 前完成 |
| 系统设计规范 | `docs/superpowers/specs/` | M0 前完成 |
| 实施计划（8 个） | `docs/superpowers/plans/` | M0 前完成 |
| 首个 DomainPack | `configs/examples/` | M0 |
| TOM 数据模型 + 视图投影 | `src/polytwin/tom/` | M1 |
| Core 约束引擎 | `src/polytwin/core/` | M2 |
| Lab 探索引擎 | `src/polytwin/lab/` | M3 |
| Bridge 决策接口 | `src/polytwin/bridge/` | M4 |
| 集成 API | `src/polytwin/api/` | M5 |
| 三个额外 DomainPack | `configs/examples/` | M6 |
| 性能基准 + 安全测试 | `tests/performance/`, `tests/security/` | M7 |
| Docker 部署 | `docker/` | M7 |
| 文档 | `docs/api/`, `docs/ops/`, `docs/developer/` | M7 |
| Jelly MCP Client | `src/polytwin/jelly/` | M0-M7 渐进集成 |

---

## Jelly 集成任务 (Spec v2.1.0 §3.7)

> **详细设计**: `2026-05-08-jelly-mcp-client-integration.md §9`
> **Jelly Phase 依赖**: Phase 3-4

### Jelly Task: Jelly MCP 安全测试 + 性能基准

**Files:**
- Create: `tests/security/test_jelly_security.py`
- Modify: `tests/performance/` — 新增 Jelly 调用延迟基准

**目的:** 验证 Jelly MCP 集成的安全性和性能。

**安全测试:**

```python
# tests/security/test_jelly_security.py

def test_lab_cannot_access_production_acceptance_via_jelly():
    """Lab caller 无法通过 Jelly 获取 production_acceptance_set"""
    result = jelly_client.get_validation_set("cstr.standard", "production_acceptance", caller="lab")
    assert result is None  # permission_denied

def test_lab_cannot_access_audit_benchmark_via_jelly():
    """Lab caller 无法获取 audit_benchmark"""
    result = jelly_client.get_validation_set("cstr.standard", "audit_benchmark", caller="lab")
    assert result is None

def test_secondary_filter_removes_hidden_fields():
    """二次视图过滤兜底：即使 Jelly 返回了完整数据，PT 侧移除敏感字段"""
    raw = jelly_client.get_domain_pack("cstr.standard", caller="lab")
    for c in raw.constraints:
        assert "threshold" not in str(c.get("certifier", {}))

def test_jelly_injection_attack_blocked():
    """敏感信息注入检测：含 hidden_challenge_set 字符串的数据被拒绝"""
    malicious = {"data": "hidden_challenge_set reference"}
    with pytest.raises(JellyDataAlignmentError):
        jelly_client.validate_data_alignment("cstr.standard", malicious)
```

**性能基准:**

```python
# tests/performance/test_jelly_performance.py

def test_jelly_get_domain_pack_under_100ms_p95():
    """单次 MCP 调用 < 100ms (p95) — Phase 4 目标"""
    # 如果 Jelly 不可达，跳过（mock 模式不计入性能）

def test_jelly_graceful_degradation_under_load():
    """高负载下 Jelly 断连不影响 PT 核心延迟"""
    # 模拟 Jelly 断连
    # Core 约束验证延迟仍在 SLA 内
```
