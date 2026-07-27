# Polymorphic-Twin 产品化设计规范：总览与 SDK

> **版本**: 1.0.0
> **日期**: 2026-05-07
> **状态**: 待审核
> **前置条件**: 引擎 Spec v2.0.0 (`2026-05-06-python-monolith-design.md`) 全部实施完成
> **覆盖里程碑**: M8 (SDK 打包)

---

## 1. 产品化设计决策

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 产品形态 | 三波叠加：SDK → API 服务 → 管理平台 | 每层复用下层全部能力，不重复造轮子 |
| DomainPack Workbench | 独立线，不绑入三波 | 减少系统复杂度，Workbench 直接调用 SDK |
| 技术栈 | Python 3.11+ 单体保持，CLI 优先，Web UI 后置 | 与引擎同语言，降低上手成本 |
| 演示场景 | 化学工艺优化（主），机器人开发（备） | 约束类型丰富、直觉强、五闭环完整 |
| 设计原则 | 结实基础 + 可演示 + 允许迭代 | 不求一步到位，但架构不能欠债 |
| 与引擎的关系 | 产品化层引用引擎公共 API，不修改引擎内部 | 引擎是独立层，产品化是叠加层 |
| 商业路径 | C(域专家) → B(企业IT) → A(平台商) | 不影响开发顺序，开发按技术依赖走 |

---

## 2. 产品化里程碑总览

| 里程碑 | 交付物 | 核心价值 | 依赖 | 独立 Spec |
|--------|--------|----------|------|-----------|
| **M8 SDK** | pip 包 + API 文档 + 集成示例 | 引擎可被外部使用 | M0-M7 完成 | 本文档 §3-§5 |
| **M9 Workbench** | CLI 工具：编辑、校验、模拟、导出 | 域专家能独立工作 | M8 完成 | `product-workbench.md` |
| **M10 API 服务** | FastAPI + 认证 + 多实例 + Docker | 可独立部署 | M8 完成 | `product-api-service.md` |
| **M11 演示层** | 端到端演示 + 简单可视化 | 可给外部人看 | M10 完成 | `product-demo.md` |

**并行关系**：M9 和 M10 都只依赖 M8，可并行开发。M11 依赖 M10。

---

## 3. 引擎公共 API 边界定义

### 3.1 设计原则

引擎实施（M0-M7）中必须有意区分两种 API：

| 类别 | 用途 | 可见性 | 稳定性要求 |
|------|------|--------|-----------|
| **Internal API** | 组件间调用（Core↔Lab, Core↔Bridge 等） | 仅包内可见 (`_` 前缀或 `internal` 子包) | 可随重构变化 |
| **Public API** | 外部调用者（SDK 用户、CLI 工具、API 服务） | 公开导出 | 必须向后兼容 |

### 3.2 Public API Surface（M8 暴露的接口）

#### 3.2.1 引擎入口

```python
# polymorphic_twin.engine
class PolymorphicTwinEngine:
    """引擎主入口 — 管理所有组件的生命周期"""

    def __init__(self, config: EngineConfig) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    # 组件访问
    @property
    def tom(self) -> TOMFacade: ...
    @property
    def core(self) -> CoreFacade: ...
    @property
    def lab(self) -> LabFacade: ...
    @property
    def bridge(self) -> BridgeFacade: ...
    @property
    def domain_pack_registry(self) -> DomainPackRegistry: ...
```

#### 3.2.2 TOM 公共接口

```python
# polymorphic_twin.tom
class TOMFacade:
    async def create_twin(self, spec: TwinObjectSpec) -> str: ...
    async def get_twin(self, twin_id: str) -> TwinObject: ...
    async def update_state(self, twin_id: str, values: dict[str, Any]) -> None: ...
    async def get_view(self, twin_id: str, view_type: ViewType, caller: CallerIdentity) -> ViewSnapshot: ...
    async def create_snapshot(self, twin_id: str) -> str: ...
    async def get_snapshot(self, snapshot_id: str) -> TwinObject: ...
    async def list_twins(self, filters: TwinFilters | None = None) -> list[TwinSummary]: ...
```

#### 3.2.3 Core 公共接口

```python
# polymorphic_twin.core
class CoreFacade:
    async def validate_constraints(self, twin_id: str) -> ConstraintEvaluationResult: ...
    async def submit_lab_result(self, submission: LabSubmission) -> QuarantineResult: ...
    async def get_constraint_status(self, twin_id: str) -> ConstraintStatus: ...
    async def trigger_fallback(self, twin_id: str, reason: str) -> FallbackResult: ...
    async def get_prescreen_library(self) -> PrescreenLibrary: ...
```

#### 3.2.4 Lab 公共接口

```python
# polymorphic_twin.lab
class LabFacade:
    async def run_exploration(self, task_type: str, data_release_id: str, budget: ExplorationBudget) -> ExplorationResult: ...
    async def get_strategies(self) -> list[StrategyManifest]: ...
    async def submit_to_core(self, submission: LabSubmission) -> QuarantineResult: ...
```

#### 3.2.5 Bridge 公共接口

```python
# polymorphic_twin.bridge
class BridgeFacade:
    async def generate_action_space(self, twin_id: str) -> BridgeOutput: ...
    async def validate_action_response(self, twin_id: str, action_id: str, response: HumanActionResponse) -> ActionResult: ...
    async def get_action_space(self, twin_id: str) -> BridgeOutput | None: ...
    async def request_exception(self, twin_id: str, action_id: str, justification: str) -> ExceptionResult: ...
```

#### 3.2.6 DomainPack 公共接口

```python
# polymorphic_twin.domainpack
class DomainPackRegistry:
    async def load(self, path: str | Path) -> str: ...        # 返回 domain_pack_id
    async def load_from_dict(self, data: dict) -> str: ...
    async def get(self, domain_pack_id: str) -> DomainPack: ...
    async def list_packs(self) -> list[DomainPackSummary]: ...
    async def activate(self, domain_pack_id: str, twin_id: str) -> None: ...
    async def deactivate(self, domain_pack_id: str, twin_id: str) -> None: ...
    async def get_lifecycle(self, domain_pack_id: str) -> LifecycleStatus: ...
    async def validate(self, path: str | Path) -> ValidationResult: ...
```

#### 3.2.7 数据模型（公共）

```python
# polymorphic_twin.models
# 以下数据类必须作为公共 API 导出，供 SDK 用户直接使用

class TwinObjectSpec(BaseModel): ...       # 创建 TwinObject 的规格
class TwinObject(BaseModel): ...           # 完整 TwinObject（只读视图）
class TwinSummary(BaseModel): ...          # 列表视图的摘要
class ViewSnapshot(BaseModel): ...         # 不可变视图快照
class ConstraintEvaluationResult(BaseModel): ...
class ConstraintStatus(BaseModel): ...
class BridgeOutput(BaseModel): ...
class ExplorationResult(BaseModel): ...
class LabSubmission(BaseModel): ...
class QuarantineResult(BaseModel): ...
class ValidationResult(BaseModel): ...
class DomainPack(BaseModel): ...
class DomainPackSummary(BaseModel): ...
class CallerIdentity(BaseModel): ...
class ViewType(str, Enum): ...             # core_full, bridge_decision, lab_exploration, audit, core_certification
class EngineConfig(BaseModel): ...
class ExplorationBudget(BaseModel): ...
class HumanActionResponse(BaseModel): ...
class FallbackResult(BaseModel): ...
class ActionResult(BaseModel): ...
```

### 3.3 Internal API 隔离规则

| 规则 | 实现方式 |
|------|----------|
| Internal 模块不可被外部 import | 使用 `__all__` 白名单 + `py.typed` 标记 |
| 产品化层只通过 Public API 调用引擎 | 代码审查 + CI import 扫描 |
| Internal API 变更不需通知产品化层 | 版本号 minor bump 即可 |
| Public API 变更必须经过 deprecation 周期 | 至少保留一个版本的双支持 |

### 3.4 验收点

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| API-01 | Public API 完整导出 | `from polymorphic_twin import *` 只导出 §3.2 列出的符号 |
| API-02 | Internal API 不可访问 | `from polymorphic_twin.core._runtime import ...` 触发 ImportError |
| API-03 | 类型标注完整 | 所有 Public API 函数和类有完整类型标注，`py.typed` 存在 |
| API-04 | 向后兼容测试 | Public API 的签名在 minor 版本间不变 |

---

## 4. M8 SDK 打包设计

### 4.1 包结构

```
polymorphic-twin/                         # 项目根
├── pyproject.toml                        # 包定义
├── src/
│   └── polymorphic_twin/
│       ├── __init__.py                   # Public API 白名单导出
│       ├── py.typed                      # PEP 561 标记
│       ├── engine.py                     # PolymorphicTwinEngine 入口
│       ├── models/                       # 公共数据模型
│       │   ├── __init__.py
│       │   ├── twin_object.py
│       │   ├── constraints.py
│       │   ├── bridge.py
│       │   ├── domain_pack.py
│       │   ├── lab.py
│       │   └── config.py
│       ├── tom/                          # TOM 组件（internal 用 _ 前缀）
│       ├── core/
│       ├── lab/
│       ├── bridge/
│       ├── domainpack/
│       └── internal/                     # 明确标记为 internal
│           └── __init__.py
├── docs/
│   ├── api/                              # API 参考文档（从 docstring 生成）
│   ├── guides/                           # 集成指南
│   │   ├── getting-started.md
│   │   ├── creating-domainpack.md
│   │   ├── embedding-in-your-system.md
│   │   ├── chemical-process-example.md
│   │   └── custom-exploration-strategy.md
│   └── examples/                         # 可运行的示例代码
│       ├── minimal_example.py
│       ├── chemical_process_demo.py
│       ├── custom_domainpack.py
│       └── lab_exploration.py
└── tests/
    └── sdk/
        ├── test_imports.py               # Public API 可导入性测试
        ├── test_api_surface.py           # API 签名稳定性测试
        ├── test_engine_lifecycle.py      # 引擎启停测试
        └── test_integration_examples.py  # 示例代码可运行性测试
```

### 4.2 pyproject.toml 关键配置

```toml
[project]
name = "polymorphic-twin"
version = "0.1.0"
description = "Trusted governance infrastructure for digital twin systems"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "pyyaml>=6.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "pytest-cov", "mypy", "ruff"]
postgres = ["asyncpg>=0.28"]
sqlite = ["aiosqlite>=0.19"]

[project.scripts]
# CLI 入口（M9 Workbench 使用）
ptw = "polymorphic_twin.cli:main"

[tool.ruff]
# 禁止从 internal 模块导入
[tool.ruff.flake8-banned-api]
# 在 CI 中检查违规 import
```

### 4.3 集成示例设计

#### 示例 1: 最小示例 (`minimal_example.py`)

**目标**：5 分钟内跑通。用户 pip install 后第一个运行的文件。

**流程**：
1. 创建引擎实例（内存模式，不需要 PostgreSQL）
2. 加载一个内置的示例 DomainPack
3. 创建 TwinObject
4. 更新状态 → 自动触发约束验证
5. 打印约束验证结果

**验收**：`python minimal_example.py` 无报错，输出约束验证结果。

#### 示例 2: 化学工艺演示 (`chemical_process_demo.py`)

**目标**：展示完整五闭环在化学工艺场景下的运行。

**流程**：
1. 加载化学工艺 DomainPack
2. 创建 CSTR TwinObject
3. 模拟正常工况 → 感知闭环
4. 触发 Lab 探索 → 探索闭环
5. Core 审判 + Bridge 生成行动空间 → 决策闭环
6. 执行行动 → 执行闭环
7. 从结果中学习 → 演化闭环

**验收**：全闭环无报错，每步输出可读的状态摘要。

#### 示例 3: 自定义 DomainPack (`custom_domainpack.py`)

**目标**：域专家视角。展示如何从零编写 DomainPack 并加载。

**流程**：
1. 用 Python dict 构建 DomainPack
2. 校验 DomainPack（刚性-关键性兼容）
3. 加载到引擎
4. 创建 TwinObject 并验证

**验收**：校验通过，加载成功。

#### 示例 4: Lab 探索 (`lab_exploration.py`)

**目标**：展示 Lab 的隔离探索能力。

**流程**：
1. 准备探索数据
2. 配置探索预算
3. 运行探索
4. 提交结果到 Core
5. 查看检疫结果

**验收**：探索完成，提交链路通畅。

### 4.4 文档要求

| 文档类型 | 内容 | 生成方式 |
|----------|------|----------|
| API 参考 | 所有 Public API 的参数、返回值、示例 | 从 docstring 自动生成（Sphinx/mkdocs） |
| 入门指南 | 30 分钟快速上手 | 手写 Markdown |
| 集成指南 | 如何嵌入外部系统 | 手写 Markdown |
| DomainPack 指南 | 域专家如何编写 DomainPack | 手写 Markdown |
| 变更日志 | 版本间 API 变更 | 从 git log + manual 整理 |

### 4.5 M8 验收点

| 编号 | 类别 | 验收项 | 通过标准 |
|------|------|--------|----------|
| M8-V01 | 功能 | pip install 成功 | `pip install -e .` 无错误 |
| M8-V02 | 功能 | import 成功 | `import polymorphic_twin` 无错误，导出 §3.2 全部符号 |
| M8-V03 | 功能 | 引擎可启动/停止 | 内存模式下引擎 start/stop 无报错 |
| M8-F01 | 检查点 | 内存模式运行 | 无需 PostgreSQL 即可运行全部示例 |
| M8-F02 | 检查点 | 示例可运行 | 4 个集成示例全部 `python xxx.py` 通过 |
| M8-F03 | 检查点 | API 文档生成 | `make docs` 成功生成 API 参考文档 |
| M8-T01 | 测试 | Import 测试 | `test_imports.py` 全部通过 |
| M8-T02 | 测试 | API 签名测试 | 所有 Public API 签名与 Spec 一致 |
| M8-T03 | 测试 | 引擎生命周期测试 | start → 操作 → stop 全流程无泄漏 |
| M8-T04 | 测试 | Internal 隔离测试 | 尝试 import internal 模块全部失败 |
| M8-T05 | 测试 | 示例代码测试 | 4 个示例作为集成测试运行通过 |
| M8-T06 | 测试 | 类型检查 | `mypy --strict` 对 Public API 无错误 |

---

## 5. 跨切关注点

### 5.1 内存模式

产品化层必须支持**无数据库的内存运行模式**。这是 SDK 和 Workbench 的基础需求。

| 模式 | 存储后端 | 适用场景 |
|------|----------|----------|
| memory | 内存 dict | SDK 示例、Workbench 模拟、测试 |
| sqlite | 本地 SQLite 文件 | 单机演示、开发调试 |
| postgres | PostgreSQL | 生产部署（M10） |

**实现方式**：通过 `EngineConfig.storage_backend` 选择。所有存储操作通过抽象 Repository 接口，memory 模式提供纯内存实现。

**验收**：`EngineConfig(storage_backend="memory")` 模式下全部引擎功能可用。

### 5.2 可观测性

产品化层需要统一的可观测性基础，从 M8 开始内置：

```python
# polymorphic_twin.models.config
class ObservabilityConfig(BaseModel):
    log_level: str = "INFO"                    # DEBUG, INFO, WARNING, ERROR
    log_format: str = "json"                   # json, text
    trace_enabled: bool = False                # 分布式追踪
    metrics_enabled: bool = False              # Prometheus 指标
    audit_log_enabled: bool = True             # 审计日志（默认开启）
```

**日志规范**：
- 所有 Public API 调用记录 INFO 级日志（函数名、参数摘要、耗时）
- 约束验证结果记录 WARNING/ERROR 级日志
- 审计事件使用独立的 audit logger，输出到 `audit.log`
- 结构化 JSON 日志，包含 `trace_id`, `twin_id`, `component`, `action`

### 5.3 错误处理

产品化层的错误必须清晰、可操作：

```python
# polymorphic_twin.exceptions
class PolymorphicTwinError(Exception):
    """基异常"""
    error_code: str
    message: str
    details: dict | None

class ValidationError(PolymorphicTwinError):
    """DomainPack 或数据验证失败"""

class ConstraintViolationError(PolymorphicTwinError):
    """约束违反 — 包含 violated_constraints 列表"""

class SafetyFallbackTriggeredError(PolymorphicTwinError):
    """安全回落已触发 — 包含 fallback_action 和 reason"""

class PermissionDeniedError(PolymorphicTwinError):
    """视图或操作权限不足"""

class DomainPackNotFoundError(PolymorphicTwinError):
    """DomainPack 不存在"""

class TwinObjectNotFoundError(PolymorphicTwinError):
    """TwinObject 不存在"""

class InvalidStateError(PolymorphicTwinError):
    """状态值不合法 — 包含 variable_name 和 expected_range"""
```

**验收**：所有 Public API 的异常类型都继承自 `PolymorphicTwinError`，不暴露 Python 内建异常。

### 5.4 配置管理

```python
class EngineConfig(BaseModel):
    storage_backend: Literal["memory", "sqlite", "postgres"] = "memory"
    storage_url: str | None = None                # sqlite: path, postgres: connection string
    observability: ObservabilityConfig = ObservabilityConfig()
    domain_pack_paths: list[str] = []             # 启动时自动加载的 DomainPack 路径
    jelly: JellyConfig = JellyConfig()            # Jelly MCP 集成配置（默认关闭/mock）
    max_concurrent_twins: int = 100               # 最大并行 TwinObject 实例数
    safety_fallback_timeout_ms: int = 200         # 安全回落超时
```

**Jelly MCP 集成配置（`EngineConfig.jelly`）：**

```python
class JellyConfig(BaseModel):
    """详见 `2026-05-08-jelly-mcp-client-integration.md`"""
    enabled: bool = False                    # 默认关闭，显式启用
    base_url: str = "http://localhost:9091"   # Jelly MCP Server 地址
    mock_mode: bool = True                   # 默认 mock，连接失败自动降级
    mock_data_dir: str = "configs/examples"  # 本地 DomainPack 目录
    timeout_seconds: float = 5.0
    max_retries: int = 3
```

**双源加载策略：**
1. 本地 YAML 文件始终加载（开箱即用）
2. 如果 `jelly.enabled=True` 且可达，从 Jelly 获取 DomainPack 并覆盖同名本地条目
3. 如果 Jelly 不可达，使用本地 YAML 兜底，记录告警日志

**配置加载优先级**：代码传入 > 环境变量 > 配置文件 > 默认值

---

## 6. 演示场景定义：化学工艺优化（CSTR）

本节定义 M9-M11 共用的主演示场景。

### 6.1 场景描述

**连续搅拌釜式反应器（CSTR）** — 化工行业最常见的反应器类型。

一个容积 1000L 的 CSTR，进行放热反应。原料以恒定流量进入，产物以相同流量流出。反应器内温度由夹套冷却水控制，压力由排气阀控制。

**核心治理问题**：如何在保证安全的前提下，通过调整操作参数（冷却水流量、进料速率、搅拌速度）来优化收率？

### 6.2 状态变量

| 变量名 | 单位 | 范围 | 可观测 | 可控 | 物理含义 |
|--------|------|------|--------|------|----------|
| `temperature` | °C | [20, 350] | ✓ | ✓（间接，通过冷却水） | 反应器内部温度 |
| `pressure` | atm | [0.5, 50] | ✓ | ✓（间接，通过排气阀） | 反应器内部压力 |
| `concentration_A` | mol/L | [0, 5] | ✓ | ✗ | 反应物 A 浓度 |
| `concentration_B` | mol/L | [0, 5] | ✓ | ✗ | 产物 B 浓度 |
| `flow_rate_in` | L/min | [0, 100] | ✓ | ✓ | 进料流量 |
| `coolant_flow` | L/min | [0, 200] | ✓ | ✓ | 冷却水流量 |
| `agitator_speed` | RPM | [0, 500] | ✓ | ✓ | 搅拌速度 |
| `reaction_rate` | mol/(L·min) | [0, 10] | ✓ | ✗ | 当前反应速率 |

### 6.3 约束卡片

| 约束 ID | 关键性 | 刚性 | 适用域 | 条件 |
|---------|--------|------|--------|------|
| `max_temperature` | safety_critical | absolute | 始终 | temperature ≤ 280°C |
| `max_pressure` | safety_critical | absolute | 始终 | pressure ≤ 45 atm |
| `min_coolant_flow` | safety_critical | absolute | temperature > 150°C | coolant_flow ≥ 20 L/min |
| `mass_balance` | identity_critical | absolute | 始终 | \|Δmass\| < 0.5% |
| `thermal_runaway_warning` | safety_critical | absolute | temperature > 200°C 且 rising | dT/dt < 5°C/min |
| `reaction_efficiency` | operational | soft | 正常工况 | concentration_B / (concentration_A + concentration_B) > 0.7 |
| `yield_optimization` | operational | learnable | 正常工况 | 最优 flow_rate_in 和 coolant_flow 组合 |
| `agitator_integrity` | operational | absolute | 始终 | agitator_speed ≤ 450 RPM |

### 6.4 安全回落策略

```yaml
fallback_strategy:
  name: "emergency_shutdown"
  trigger: "any safety_critical constraint violation"
  steps:
    - action: "close_feed_valve"
      target: "flow_rate_in"
      set_value: 0
    - action: "max_coolant"
      target: "coolant_flow"
      set_value: 200
    - action: "open_vent"
      target: "pressure"
      set_value: 1.0
    - action: "stop_agitator"
      target: "agitator_speed"
      set_value: 0
  target_state:
    temperature: 50
    pressure: 1.0
    flow_rate_in: 0
    coolant_flow: 200
  timeout_ms: 200
```

### 6.5 行动模板

| 模板 ID | 类型 | 参数 | 前置条件 | 角色 |
|---------|------|------|----------|------|
| `adjust_coolant` | continuous | coolant_flow: [0, 200] | 无 | operator |
| `adjust_feed_rate` | continuous | flow_rate_in: [0, 100] | 无 | operator |
| `adjust_agitator` | continuous | agitator_speed: [0, 450] | 无 | operator |
| `emergency_shutdown` | discrete | 无 | safety_critical violation | system (auto) |
| `scheduled_maintenance` | discrete | duration: min | temperature < 50, pressure < 5 | maintenance |
| `exception_override` | discrete | justification: str | 人类审批 | supervisor |

### 6.6 人类角色

| 角色 | 权限 |
|------|------|
| `operator` | 调整操作参数（coolant, feed, agitator），查看约束状态 |
| `supervisor` | 审批 exception_request，查看审计日志 |
| `domain_expert` | 修改 DomainPack（需走 draft → review → active 流程） |
| `auditor` | 只读访问全部数据，导出审计日志 |

### 6.7 演示数据特征

为演示目的，需要模拟以下工况序列：

| 阶段 | 持续 | 描述 | 预期引擎行为 |
|------|------|------|-------------|
| 启动 | 30s | 温度从 25°C 升至 180°C，压力从 1atm 升至 15atm | 正常，约束全部 passed |
| 稳态运行 | 60s | 温度 180-200°C，收率稳定 | 正常，yield_optimization 学习中 |
| 传感器漂移 | 30s | temperature 传感器读数逐渐偏离实际值 | IdentityMonitor 检测到漂移 |
| 温度飙升 | 20s | 冷却水故障，温度快速升至 260°C | thermal_runaway_warning 触发，Lab 探索新策略 |
| 紧急工况 | 10s | 温度突破 280°C | safety_critical 触发，自动回落 |
| 恢复 | 30s | 回落后系统稳定在安全状态 | Bridge 生成恢复行动空间 |

---

## 7. 版本与兼容性

### 7.1 版本策略

| 版本号 | 含义 | 兼容性 |
|--------|------|--------|
| 0.x.y | 引擎开发期 | Public API 可能变化 |
| 1.0.0 | 产品化就绪 | Public API 承诺向后兼容 |
| 1.x.y | 功能增加 | 新增 API，不删除已有 API |
| 2.0.0 | 架构变更 | 允许破坏性变更，需迁移指南 |

### 7.2 引擎 Spec 与产品化 Spec 的版本对应

| 引擎 Spec | 产品化 Spec | 说明 |
|-----------|------------|------|
| v2.0.0 完成 | M8-M11 可开始 | 引擎 Spec 是前置条件 |
| v2.x 变更 | 产品化 Spec 需评估影响 | Minor 变更不阻塞 |
| v3.0 变更 | 产品化 Spec 需全面修订 | 破坏性变更 |

---

## 8. 审核记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-05-07 | 初始版本：设计决策、公共 API 边界、M8 SDK 设计、演示场景定义 |
| v1.1.0 | 2026-05-08 | Jelly 集成：新增 JellyConfig 公开配置、EngineConfig.jelly 字段、双源 DomainPack 加载 |
