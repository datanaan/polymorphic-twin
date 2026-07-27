# Polymorphic-Twin Jelly MCP 客户端集成规范

> **版本**: 1.0.0
> **日期**: 2026-05-08
> **状态**: 待审核
> **前置文档**: `2026-05-08-jelly-twin-provider-contract.md` (已生效契约)
> **被修改文档**: `2026-05-06-python-monolith-design.md` v2.0.0

---

## 0. 定位与边界

本文档定义 Polymorphic-Twin 内部的 Jelly MCP Client 集成层。它是 PT 与 Jelly 之间的**本地适配器**，职责是：

1. 封装 MCP 协议细节（HTTP/SSE 连接、序列化、重试）
2. 将 Jelly 15 个 MCP 工具映射为 PT 内部 Python 接口
3. 提供 mock 模式用于开发和测试（Jelly 不可用时 PT 仍可运行）
4. 实现 caller 身份注入和二次视图过滤兜底

**边界声明：**
- PT 完全独立运行，没有 Jelly 也能工作（mock 模式或本地文件模式）
- Jelly 是增强，不是依赖
- 本文档不定义 jelly_twin_provider 的内部实现（那是 Jelly 团队的职责）

---

## 1. 架构位置

```
┌──────────────────────────────────────────────────────────────────┐
│                    Polymorphic-Twin 内部                         │
│                                                                  │
│  Core ──┐  Lab ──┐  Bridge ──┐  DomainPack.Registry ──┐        │
│         │        │           │                         │        │
│         ▼        ▼           ▼                         ▼        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              JellyMCPClient (基础设施层)                  │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │ MCPProtocol │  │ CallerAuth   │  │ ViewFilter    │  │   │
│  │  │ (HTTP/SSE)  │  │ (身份注入)    │  │ (二次兜底)    │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │ RetryPolicy │  │ MockProvider │  │ Config        │  │   │
│  │  │ (指数退避)   │  │ (本地回退)   │  │ (连接配置)    │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                              │ MCP (HTTP/SSE :9091)            │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
                 ┌──────────────────────────┐
                 │  jelly_twin_provider      │
                 │  (Jelly 团队开发运维)      │
                 └──────────────────────────┘
```

**关键设计决策：**

| 决策 | 结论 | 理由 |
|------|------|------|
| 集成层位置 | 独立模块 `polytwin/jelly/` | 不侵入现有 Core/Lab/Bridge 代码 |
| 调用方式 | 同步函数（内部可异步） | 上层组件使用同步接口 |
| Mock 策略 | 本地文件 + 合成数据 | Jelly 不可用时 PT 完整可运行 |
| 视图过滤 | Jelly 侧过滤 + PT 侧二次兜底 | 契约 Q10 确认的双层保障 |

---

## 2. 模块结构

```
src/polytwin/jelly/
├── __init__.py              # 公开 API: JellyClient, JellyConfig
├── client.py                # JellyClient 主类 — 15 个工具的 Python 封装
├── config.py                # JellyConfig 数据模型
├── protocol.py              # MCP HTTP/SSE 协议层
├── caller.py                # CallerIdentity 注入 + 权限断言
├── view_filter.py           # 二次视图过滤兜底
├── retry.py                 # 重试策略（指数退避）
├── mock.py                  # MockProvider — 从本地文件提供数据
├── exceptions.py            # JellyError 层次结构
└── types.py                 # Jelly 数据类型定义（Pydantic 模型）
```

---

## 3. 配置模型

```python
# src/polytwin/jelly/config.py

class JellyConfig(BaseModel):
    """Jelly MCP 连接配置。"""

    # 连接
    enabled: bool = False                    # 默认关闭，显式启用
    base_url: str = "http://localhost:9091"   # MCP Server 地址
    timeout_seconds: float = 5.0             # 单次调用超时

    # 认证（Phase 1 信任传入值）
    auth_token: str | None = None            # Phase 2 启用

    # 重试
    max_retries: int = 3
    retry_backoff: list[float] = [1.0, 2.0, 4.0]  # 指数退避

    # Mock 模式
    mock_mode: bool = True                   # 默认 mock，连接失败自动降级
    mock_data_dir: str = "configs/examples"  # 本地 DomainPack 目录

    # 二次过滤
    enable_secondary_filter: bool = True     # PT 侧兜底视图过滤
```

**配置来源优先级：**

1. 环境变量 `PT_JELLY_*`（生产部署）
2. `EngineConfig.jelly` 字段（SDK/API 使用）
3. 默认值（mock 模式）

---

## 4. 核心接口

### 4.1 JellyClient

```python
# src/polytwin/jelly/client.py

class JellyClient:
    """Jelly MCP 工具的 Python 封装。

    所有方法返回 Pydantic 模型或 None（不可用时）。
    Jelly 不可用时自动降级到 MockProvider。
    """

    def __init__(self, config: JellyConfig): ...

    # ── DomainPack 服务 (Group 1) ──

    def get_domain_pack(
        self, domain_id: str, caller: str = "core"
    ) -> JellyDomainPack | None:
        """映射: twin.get_domain_pack
        简短格式 domain_id 自动转换为 Jelly 内部格式。
        """

    def search_domain_packs(
        self, keywords: list[str], *,
        industry: str | None = None,
        equipment_type: str | None = None,
    ) -> list[JellyDomainPackSummary]:
        """映射: twin.search_domain_packs"""

    def list_domain_pack_versions(
        self, domain_id: str
    ) -> list[JellyDomainPackVersion]:
        """映射: twin.list_domain_pack_versions
        状态枚举: draft | review | active | deprecated | archived
        """

    def get_domain_pack_lineage(
        self, domain_id: str
    ) -> JellyDomainPackLineage:
        """映射: twin.get_domain_pack_lineage"""

    # ── 验证数据集服务 (Group 2) ──

    def get_validation_set(
        self, domain_id: str, set_type: str, caller: str = "core"
    ) -> JellyValidationSet | None:
        """映射: twin.get_validation_set
        caller=lab 时只允许 public_eval；
        caller=audit 时允许全部。
        """

    def query_validation_data(
        self, domain_id: str, *,
        set_type: str | None = None,
        variable_ranges: dict | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> JellyValidationSet:
        """映射: twin.query_validation_data"""

    # ── 探索数据服务 (Group 3) ──

    def get_exploration_data(
        self, domain_id: str, data_release_id: str,
        caller: str = "lab",
    ) -> JellyExplorationData:
        """映射: twin.get_exploration_data"""

    def get_failure_logs(
        self, domain_id: str, *,
        time_range: tuple[str, str],
        severity: list[str] | None = None,
        caller: str = "lab",
    ) -> JellyFailureLogPackage:
        """映射: twin.get_failure_logs"""

    def query_operational_history(
        self, domain_id: str, *,
        variables: list[str],
        time_range: tuple[str, str],
        aggregation: str = "raw",
    ) -> JellyOperationalHistory:
        """映射: twin.query_operational_history"""

    # ── 领域知识查询 (Group 4) ──

    def query_domain_knowledge(
        self, domain_id: str, query: str,
        context: dict | None = None,
    ) -> JellyKnowledgeAnswer:
        """映射: twin.query_domain_knowledge"""

    def get_physical_limits(
        self, domain_id: str, variable: str,
    ) -> list[JellyPhysicalLimit]:
        """映射: twin.get_physical_limits"""

    def get_equipment_spec(
        self, domain_id: str, equipment_id: str,
    ) -> JellyEquipmentSpec:
        """映射: twin.get_equipment_spec"""

    def get_safety_standards(
        self, domain_id: str, standard_ref: str,
    ) -> JellySafetyStandard:
        """映射: twin.get_safety_standards"""

    # ── 数据对齐 (Group 5) ──

    def get_state_variable_schema(
        self, domain_id: str,
    ) -> list[JellyVariableSchema]:
        """映射: twin.get_state_variable_schema"""

    def validate_data_alignment(
        self, domain_id: str, data: dict,
    ) -> JellyAlignmentResult:
        """映射: twin.validate_data_alignment"""

    # ── 生命周期 ──

    def health_check(self) -> bool:
        """检查 Jelly MCP Server 是否可达。"""

    def close(self) -> None:
        """关闭连接，释放资源。"""
```

### 4.2 返回类型定义

```python
# src/polytwin/jelly/types.py

# ── DomainPack ──

class JellyDomainPackSummary(BaseModel):
    domain_id: str
    domain_name: str
    domain_version: str
    description: str
    constraint_count: int
    state_variable_count: int

class JellyDomainPackVersion(BaseModel):
    version: str
    status: Literal["draft", "review", "active", "deprecated", "archived"]
    created_at: str
    constraint_count: int
    change_summary: str

class JellyDomainPackLineage(BaseModel):
    parents: list[dict]
    children: list[dict]
    inheritance_chain: list[dict]

class JellyDomainPack(BaseModel):
    """完整 DomainPack — 格式与 jelly-twin-provider-design §2.1 一致。"""
    domain_id: str
    domain_name: str
    domain_version: str
    description: str
    state_variables: list[dict]
    constraints: list[dict]
    fallback_strategy: dict
    action_templates: list[dict]
    human_roles: list[dict]
    identity_invariants: list[dict]
    inheritance_policy: dict
    metadata: dict

# ── 验证数据集 ──

class JellyValidationCase(BaseModel):
    case_id: str
    input_state: dict[str, float]
    expected_result: dict[str, str]
    tags: list[str]

class JellyValidationSet(BaseModel):
    domain_id: str
    set_type: str
    description: str
    total_cases: int
    cases: list[JellyValidationCase]

# ── 探索数据 ──

class JellyExplorationRecord(BaseModel):
    timestamp: str
    values: dict[str, float]
    labels: dict[str, str] | None

class JellyExplorationData(BaseModel):
    domain_id: str
    data_release_id: str
    view_applied: str
    records: list[JellyExplorationRecord]
    metadata: dict

class JellyFailureLogEntry(BaseModel):
    timestamp: str
    failure_type: str
    constraint_id: str | None
    severity: str
    state_at_failure: dict[str, float]
    root_cause_category: str | None
    duration_seconds: float
    resolution: str

class JellyFailureLogPackage(BaseModel):
    domain_id: str
    entries: list[JellyFailureLogEntry]
    total_entries: int

class JellyOperationalHistory(BaseModel):
    records: list[dict] | None = None       # aggregation="raw"
    stats: dict | None = None               # aggregation="stats"

# ── 领域知识 ──

class JellyKnowledgeAnswer(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float

class JellyPhysicalLimit(BaseModel):
    limit_type: str
    value: float
    unit: str
    source: str
    confidence: float
    conditions: dict | None

class JellyEquipmentSpec(BaseModel):
    equipment_id: str
    equipment_type: str
    parameters: list[dict]
    rated_limits: list[dict]
    operating_ranges: list[dict]

class JellySafetyStandard(BaseModel):
    standard_ref: str
    title: str
    requirements: list[dict]
    effective_date: str

# ── 数据对齐 ──

class JellyVariableSchema(BaseModel):
    name: str
    unit: str
    physical_range: dict
    observable: bool
    controllable: bool
    description: str

class JellyAlignmentMismatch(BaseModel):
    variable: str
    issue: str
    expected: str
    actual: str

class JellyAlignmentResult(BaseModel):
    aligned: bool
    mismatches: list[JellyAlignmentMismatch]
```

---

## 5. DomainPack 注册表集成

### 5.1 双源加载策略

DomainPack.Registry 从两个源加载：

```
EngineConfig.domain_pack_paths  →  本地 YAML 文件  →  注册到 Registry
                                        ↓
EngineConfig.jelly.enabled=True  →  JellyClient.get_domain_pack()  →  注册到 Registry
```

**优先级规则：**
1. 本地 YAML 文件始终可用（开箱即用）
2. 如果 Jelly 启用且可达，从 Jelly 获取 DomainPack 并覆盖本地同名条目
3. 如果 Jelly 不可达，使用本地 YAML 兜底，记录告警日志

### 5.2 Registry 接口扩展

```python
class DomainPackRegistry:
    def __init__(self, jelly_client: JellyClient | None = None): ...

    def load_from_directory(self, path: str) -> list[str]:
        """从本地 YAML 目录加载。返回加载成功的 domain_id 列表。"""

    def load_from_jelly(self, domain_id: str) -> bool:
        """从 Jelly MCP 获取 DomainPack 并注册。"""

    def search_jelly(self, keywords: list[str]) -> list[JellyDomainPackSummary]:
        """搜索 Jelly 上的 DomainPack（仅 Jelly 可用时）。"""

    def get(self, domain_id: str) -> DomainPack:
        """获取已注册的 DomainPack（本地或 Jelly 来源）。"""
```

### 5.3 Jelly DomainPack → PT DomainPack 转换

```python
def _convert_jelly_domain_pack(jdp: JellyDomainPack) -> DomainPack:
    """将 Jelly 返回的 DomainPack 结构转换为 PT 内部 DomainPack 模型。

    关键转换：
    - state_variables: Jelly 格式 → PT StateSemanticsTemplate.variables 格式
    - constraints: Jelly 扁平列表 → PT constraint_cards 分桶（absolute/soft/learnable）
    - domain_id: 保持简短格式（Jelly MCP 层已做双向映射）
    - fallback_strategy: Jelly 格式 → PT safe_fallback 格式
    - action_templates: Jelly 格式 → PT 格式
    - human_roles: 直接映射
    - identity_invariants: 直接映射
    """
```

---

## 6. 各组件集成点

### 6.1 Core 集成

```python
# Core 使用 Jelly 的场景
class CoreEngine:
    def __init__(self, registry: DomainPackRegistry, jelly: JellyClient | None):
        self.jelly = jelly

    def load_validation_sets(self, domain_id: str) -> None:
        """从 Jelly 加载验证数据集。

        - Core 全权 caller → 可获取所有 set_type
        - production_acceptance_set 用于 HardGate 隐藏验证集
        - audit_benchmark 用于审计对比
        """

    def enrich_constraint_evaluation(self, domain_id: str, variable: str) -> list[JellyPhysicalLimit]:
        """查询物理极限，用于约束求值器的不确定性传播计算。"""

    def run_certification(self, domain_id: str, hidden_set: list[dict]) -> CertificationResult:
        """HardGate 使用隐藏验证集时，可从 Jelly 获取 production_acceptance 数据。"""
```

### 6.2 Lab 集成

```python
# Lab 使用 Jelly 的场景
class LabExplorer:
    def __init__(self, jelly: JellyClient | None):
        self.jelly = jelly

    def get_exploration_data(self, domain_id: str, data_release_id: str) -> ExplorationData:
        """从 Jelly 获取 LabExplorationView 投影的探索数据。

        caller="lab" → Jelly 侧自动过滤敏感字段。
        """

    def get_failure_logs(self, domain_id: str, time_range: tuple) -> FailureLogPackage:
        """从 Jelly 获取脱敏失效日志。"""

    def query_domain_knowledge(self, domain_id: str, hypothesis: str) -> KnowledgeAnswer:
        """Lab 假设生成时查询领域知识。"""
```

### 6.3 Bridge 集成

Bridge 是无状态推导层，**不直接调用 Jelly**。它通过以下方式间接受益：
- Core 加载 Jelly 的 DomainPack 后，Bridge 通过 TwinObject 的视图获取约束摘要
- Bridge 的 action_templates 来自 DomainPack（可能由 Jelly 提供）
- 未来扩展：Bridge 的领域知识查询面板（M10+）

### 6.4 Workbench 集成

```python
# Workbench 使用 Jelly 的场景
class WorkbenchCLI:
    def cmd_init(self, domain_id: str | None, from_jelly: bool = False):
        """ptw workbench init --from-jelly 化学反应器
        从 Jelly 搜索并下载 DomainPack 模板。
        """

    def cmd_validate(self, domain_pack_path: str, check_alignment: bool = False):
        """ptw workbench validate --check-alignment
        调用 twin.validate_data_alignment 验证与 Jelly 数据对齐。
        """
```

---

## 7. domain_id 双格式映射

```python
# src/polytwin/jelly/caller.py

DOMAIN_ID_MAP: dict[str, str] = {
    "cstr.standard": "twin.chemical.cstr_standard",
    "example.minimal_device_monitor": "twin.example.minimal_device_monitor",
    "chemical-reactor-thermal": "twin.chemical.reactor_thermal",
    "wind-turbine-bearing": "twin.energy.wind_turbine_bearing",
    "knowledge-management": "twin.software.knowledge_management",
}

def to_jelly_format(pt_domain_id: str) -> str:
    """PT 简短格式 → Jelly 内部格式。未知 ID 原样传递。"""
    return DOMAIN_ID_MAP.get(pt_domain_id, pt_domain_id)

def to_pt_format(jelly_domain_id: str) -> str:
    """Jelly 内部格式 → PT 简短格式。"""
    reverse = {v: k for k, v in DOMAIN_ID_MAP.items()}
    return reverse.get(jelly_domain_id, jelly_domain_id)
```

---

## 8. 错误处理与降级

### 8.1 错误层次

```python
class JellyError(Exception):
    """Jelly 集成错误基类。"""

class JellyConnectionError(JellyError):
    """连接失败（网络、超时）。"""

class JellyDomainPackNotFoundError(JellyError):
    """DomainPack 不存在。domain_pack_not_found"""

class JellyPermissionDeniedError(JellyError):
    """权限不足。permission_denied"""

class JellyDataAlignmentError(JellyError):
    """数据对齐失败。data_alignment_error"""

class JellyServiceUnavailableError(JellyError):
    """服务不可用。service_unavailable"""
```

### 8.2 降级策略

| 场景 | 降级行为 |
|------|----------|
| Jelly 启动时不可达 | 记录告警，使用本地 YAML + mock 数据 |
| 运行中 Jelly 断连 | 重试 3 次（1s/2s/4s），失败后降级到 mock |
| 请求的 domain_id 在 Jelly 不存在 | 返回 None，上层使用本地版本 |
| 数据对齐失败 | 拒绝加载该条数据，记录审计日志，继续加载其他数据 |
| 单个工具超时 | 不影响其他工具调用 |

### 8.3 审计追踪

所有 Jelly 调用（成功和失败）写入审计日志：

```python
{
    "event_type": "jelly_mcp_call",
    "tool": "twin.get_domain_pack",
    "domain_id": "cstr.standard",
    "caller": "core",
    "result": "success" | "fallback_to_mock" | "error",
    "latency_ms": 42,
    "error_detail": None | "connection_timeout",
    "timestamp": "2026-05-08T10:23:15Z"
}
```

---

## 9. 测试策略

### 9.1 Mock 模式测试

所有 M0-M7 测试在 Jelly 不可用时必须通过（mock 模式）。Mock 数据来自：
- `configs/examples/*.yaml` — 本地 DomainPack
- `tests/fixtures/jelly_mocks/` — 合成的验证集、时序数据、失效日志

### 9.2 集成测试（Jelly 可用时）

| 测试场景 | 对应检查点 |
|----------|-----------|
| 连接 Jelly 并获取 DomainPack | TP-C2 |
| Lab caller 获取探索数据（无敏感字段） | TP-C6 |
| Core caller 获取 production_acceptance | TP-C3 |
| domain_id 双向映射正确 | TP-C4 |
| Jelly 不可达时自动降级 | — |
| 重连后恢复正常 | TP-C8 |

### 9.3 二次过滤验证

```python
def test_secondary_filter_removes_hidden_fields():
    """即使 Jelly 返回了不应有的字段，PT 侧二次过滤也能移除。"""
    raw = client.get_domain_pack("cstr.standard", caller="lab")
    # lab 不应看到 certifier.threshold
    for c in raw.constraints:
        assert "certifier" not in c or "threshold" not in c.get("certifier", {})
```

---

## 10. 里程碑对齐

| 里程碑 | Jelly 集成内容 | Jelly Phase 依赖 |
|--------|---------------|-----------------|
| M0 | JellyConfig 模型 + client 骨架 + mock provider | 无（mock 模式） |
| M1 | DomainPack.Registry 双源加载 + JellyClient 基础工具 | 无（mock 模式） |
| M2 | Core 从 Jelly 加载验证集（set_type 过滤） | Phase 1 (Group 2) |
| M3 | Lab 从 Jelly 获取探索数据 + 失效日志 | Phase 2 (Group 3) |
| M5 | 端到端集成测试含 Jelly mock + 可选真实连接 | Phase 1-2 |
| M6 | 多场景 DomainPack 从 Jelly 搜索和加载 | Phase 1-3 |
| M7 | Jelly MCP 安全测试 + 性能基准 | Phase 3-4 |
| M8 | SDK 公开 JellyConfig + 使用示例 | Phase 3 |
| M9 | Workbench --from-jelly 选项 | Phase 3 |
| M10 | API 端点暴露 Jelly 能力 | Phase 3-4 |
| M11 | CSTR 演示全流程走 Jelly | Phase 4 |

---

## 11. 对 python-monolith-design.md 的修正

以下修正需合并到 `2026-05-06-python-monolith-design.md` v2.0.0：

### 11.1 §1 设计决策表新增行

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 外部知识来源 | 可选 Jelly MCP 集成 | Jelly 提供领域数据增强，但 PT 核心不依赖外部系统 |

### 11.2 §2.1 感知闭环新增步骤

在 DomainPack.Registry 场景匹配之后新增：
```
  → 如果 Jelly 可达：Registry 优先使用 Jelly 提供的 DomainPack
  → 如果 Jelly 不可达：Registry 使用本地 YAML 兜底
```

### 11.3 §2.2 探索闭环数据来源扩展

```
Core → DataReleaseManager：释放脱敏历史数据
  → 数据来源：
    1. 本地运行时累积数据（首选）
    2. Jelly twin.get_exploration_data（历史数据增强）
    3. Jelly twin.get_failure_logs（失效模式补充）
```

### 11.4 §2.3 决策闭环验证集来源扩展

```
Core.Evidence：证据准入
  → 验证数据来源：
    1. DomainPack 内嵌引用（本地）
    2. Jelly twin.get_validation_set (set_type="production_acceptance")
  → Core 使用 Jelly 数据前做二次视图过滤
```

### 11.5 §2.5 演化闭环知识来源扩展

```
Lab.ConstraintHypothesis：从累积失败日志中发现新约束假设
  → 知识来源：
    1. 累积失败日志（内部）
    2. Jelly twin.query_domain_knowledge（领域知识增强）
    3. Jelly twin.get_physical_limits（物理极限验证）
```

### 11.6 §3 组件职责新增 §3.7

```markdown
### 3.7 JellyMCPClient (可选外部数据集成层)

**职责**：
- 封装 Jelly 15 个 MCP 工具为 Python 接口
- 管理 HTTP/SSE 连接和重试策略
- 提供 mock 模式用于开发测试
- 注入 caller 身份，执行二次视图过滤兜底

**接口契约**：

| 接口 | 输入 | 输出 | 权限 |
|------|------|------|------|
| get_domain_pack | (domain_id, caller) | JellyDomainPack or None | 所有组件 |
| get_validation_set | (domain_id, set_type, caller) | JellyValidationSet or None | core, audit |
| get_exploration_data | (domain_id, data_release_id, caller) | JellyExplorationData | lab |
| get_failure_logs | (domain_id, time_range, caller) | JellyFailureLogPackage | lab, core |
| query_domain_knowledge | (domain_id, query) | JellyKnowledgeAnswer | 所有组件 |
| get_physical_limits | (domain_id, variable) | list[JellyPhysicalLimit] | 所有组件 |

**降级规则**：Jelly 不可用时自动降级到 MockProvider，不影响 PT 核心功能。

**详细设计**：见 `2026-05-08-jelly-mcp-client-integration.md`
```

### 11.7 §5 里程碑对齐表更新

在 M0 行新增 Jelly 列内容：
```
| M0 | §3.7 | JellyConfig + client 骨架 + mock provider | mock 模式通过 |
```

---

## 附录 A：契约链参考

本集成规范基于以下已生效契约链：

| 文档 | 性质 |
|------|------|
| `2026-05-08-jelly-twin-provider-design.md` | PT 原始需求（993行，15工具+13数据集） |
| `2026-05-08-jelly-team-reply.md` | Jelly 回复（10个问题+交付计划） |
| `2026-05-08-jelly-twin-provider-contract.md` | PT 契约确认（逐条回复10个问题） |
| `2026-05-08-jelly-team-confirmation.md` | Jelly 最终确认（契约生效） |
| 本文档 | PT 内部集成层设计 |

---

*最后更新: 2026-05-08*
