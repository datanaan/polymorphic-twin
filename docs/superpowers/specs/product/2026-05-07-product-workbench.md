# Polymorphic-Twin 产品化设计规范：DomainPack Workbench

> **版本**: 1.0.0
> **日期**: 2026-05-07
> **状态**: 待审核
> **前置条件**: M8 SDK 完成打包
> **覆盖里程碑**: M9 (DomainPack Workbench)
> **关联 Spec**: `2026-05-07-product-overview-sdk.md` §3 (公共 API)

---

## 1. 设计决策

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 产品形态 | CLI 工具，通过 `ptw` 命令调用 | 最简单、最结实，域专家能用终端就能用 |
| 技术栈 | Python + Click/Typer + Rich | 与引擎同语言，Rich 提供终端美化输出 |
| 运行模式 | 直接调用 SDK，不需要 API 服务 | 独立于三波，减少复杂度 |
| 存储 | 内存模式为主，可选 SQLite 持久化 | Workbench 是临时工具，不需要生产数据库 |
| 扩展性 | 预留 Web UI 接口，但不实现 | 架构不堵死，但当前不加前端复杂度 |

---

## 2. CLI 命令设计

### 2.1 命令树

```
ptw
├── workbench
│   ├── init          从模板创建新 DomainPack
│   ├── validate      校验 DomainPack
│   ├── simulate      用模拟数据跑五闭环
│   ├── export        导出可部署的 DomainPack + 报告
│   └── templates     列出可用模板
├── domainpack
│   ├── load          加载 DomainPack 到引擎
│   ├── list          列出已加载的 DomainPack
│   ├── show          显示 DomainPack 详情
│   └── validate      独立校验（不启动引擎）
└── version           显示版本信息
```

### 2.2 命令详细规格

#### `ptw workbench init`

**用途**：域专家从模板开始编写 DomainPack。

```
ptw workbench init --template chemical-process --name my-reactor --output ./my-reactor.yaml
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--template` | 是 | 模板名称（chemical-process, robot, minimal） |
| `--name` | 是 | DomainPack 名称 |
| `--output` | 否 | 输出路径，默认 `./<name>.yaml` |

**行为**：
1. 读取模板文件
2. 替换模板中的占位符（名称、ID）
3. 生成 YAML 文件
4. 输出提示：下一步请编辑哪些字段

**验收**：生成的 YAML 通过 `ptw domainpack validate` 校验。

---

#### `ptw workbench validate`

**用途**：对 DomainPack 执行多层校验，输出详细报告。

```
ptw workbench validate ./my-reactor.yaml --level full --output report.md
```

| 参数 | 必填 | 说明 |
|------|------|------|
| 位置参数 | 是 | DomainPack 文件路径 |
| `--level` | 否 | `syntax` / `semantic` / `full`（默认 full） |
| `--output` | 否 | 报告输出路径，不指定则输出到终端 |

**校验级别**：

| 级别 | 检查内容 | 通过标准 |
|------|----------|----------|
| syntax | YAML/JSON 解析、schema 合规 | 无语法错误 |
| semantic | 引用完整性、状态变量类型一致、约束条件可求值 | 无语义冲突 |
| full | syntax + semantic + 刚性-关键性兼容 + 安全回落存在 + 适用域引用有效 | 全部通过 |

**输出格式**（终端）：

```
╭─ DomainPack 校验报告 ──────────────────────────────╮
│ 文件: ./my-reactor.yaml                            │
│ 级别: full                                         │
├────────────────────────────────────────────────────┤
│ ✓ Syntax       YAML 解析正确                        │
│ ✓ Schema       所有必填字段存在                      │
│ ✓ References   所有状态变量引用有效                   │
│ ✓ Compatibility 刚性-关键性兼容检查通过               │
│ ✗ Fallback     安全回落策略缺少 timeout_ms 字段       │
│   → 修复建议: 在 fallback_strategy 中添加 timeout_ms │
├────────────────────────────────────────────────────┤
│ 结果: FAIL (5/6 通过)                               │
╰────────────────────────────────────────────────────╯
```

**验收**：
- 合规 DomainPack 校验通过
- 5 种典型错误（刚性-关键性冲突、引用缺失、回落缺失、适用域无效、类型不匹配）各自能被检测并报告修复建议
- `--output report.md` 生成 Markdown 格式报告

---

#### `ptw workbench simulate`

**用途**：用模拟数据在引擎中运行 DomainPack，验证五闭环行为。

```
ptw workbench simulate ./my-reactor.yaml --scenario normal --duration 60 --output results.json
```

| 参数 | 必填 | 说明 |
|------|------|------|
| 位置参数 | 是 | DomainPack 文件路径 |
| `--scenario` | 否 | `normal` / `drift` / `emergency` / `full`（默认 full，运行全部） |
| `--duration` | 否 | 每个场景持续秒数（默认 30） |
| `--tick` | 否 | 模拟步长毫秒（默认 1000） |
| `--output` | 否 | 结果输出路径（JSON） |

**模拟场景**：

| 场景 | 行为 | 验证的闭环 |
|------|------|-----------|
| normal | 稳态运行，参数在安全范围内 | 感知、约束验证 |
| drift | 传感器逐渐漂移 | 感知、身份监控 |
| emergency | 触发 safety_critical 违规 | 感知、约束验证、安全回落、执行 |
| full | 正常→漂移→紧急→恢复 | 全部五个闭环 |

**模拟数据生成器**：

```python
class SimulationDataGenerator:
    """根据 DomainPack 的状态变量定义生成模拟数据"""

    def __init__(self, domain_pack: DomainPack) -> None:
        # 从 DomainPack 的 state_variables 获取变量定义
        # 从约束卡片获取安全边界
        # 从安全回落策略获取目标状态
        ...

    def normal_tick(self, current: dict) -> dict:
        """生成稳态噪声数据"""
        # 在当前值附近添加高斯噪声
        ...

    def drift_tick(self, current: dict, drift_variable: str, drift_rate: float) -> dict:
        """生成漂移数据"""
        # 指定变量逐渐偏离真实值
        ...

    def emergency_tick(self, current: dict, trigger_constraint: str) -> dict:
        """生成触发指定约束违反的数据"""
        # 推动指定变量突破约束边界
        ...
```

**输出格式**（终端）：

```
╭─ 模拟报告 ────────────────────────────────────────╮
│ DomainPack: my-reactor v1.0.0                       │
│ 场景: full                                          │
│ 时长: 150s (5 ticks/s)                              │
├────────────────────────────────────────────────────┤
│ 闭环验证:                                           │
│ ✓ 感知闭环     150 ticks 全部正常处理                │
│ ✓ 探索闭环     Lab 生成 3 个假设                     │
│ ✓ 决策闭环     Core 准入 2/3 假设，Bridge 生成行动空间│
│ ✓ 执行闭环     安全回落 187ms 触发                   │
│ ✓ 演化闭环     发现 1 个新约束模式                   │
├────────────────────────────────────────────────────┤
│ 约束行为:                                           │
│ max_temperature     passed→failed→fallback→passed    │
│ max_pressure        passed (全程)                    │
│ thermal_runaway     passed→uncertain→failed          │
│ mass_balance        passed (全程)                    │
│ reaction_efficiency passed→not_applicable→passed     │
├────────────────────────────────────────────────────┤
│ 性能指标:                                           │
│ 约束验证延迟 p50: 2ms  p99: 8ms                     │
│ 安全回落触发: 187ms                                 │
│ Lab 探索耗时: 4.2s                                  │
│ Bridge 行动空间生成: 12ms                            │
╰────────────────────────────────────────────────────╯
```

**验收**：
- `normal` 场景：所有约束 passed，无回落
- `drift` 场景：IdentityMonitor 检测到漂移，状态变为 uncertain
- `emergency` 场景：safety_critical 触发，安全回落 < 200ms
- `full` 场景：五个闭环全部走通

---

#### `ptw workbench export`

**用途**：将校验通过的 DomainPack 导出为可部署格式，附带验证报告。

```
ptw workbench export ./my-reactor.yaml --output ./dist/
```

| 参数 | 必填 | 说明 |
|------|------|------|
| 位置参数 | 是 | DomainPack 文件路径 |
| `--output` | 否 | 输出目录（默认 `./dist/`） |
| `--skip-validate` | 否 | 跳过校验（不推荐） |

**输出文件**：

```
dist/
├── my-reactor-v1.0.0.yaml          # DomainPack 本身
├── my-reactor-v1.0.0.validation.md # 校验报告
├── my-reactor-v1.0.0.simulation.json # 模拟结果
└── my-reactor-v1.0.0.manifest.json # 元数据清单
```

**manifest.json 格式**：

```json
{
  "domain_pack_id": "cstr.my_reactor",
  "version": "1.0.0",
  "author": "张三",
  "created_at": "2026-05-07T10:30:00Z",
  "validation_result": "PASS",
  "validation_timestamp": "2026-05-07T10:30:45Z",
  "simulation_scenarios": ["normal", "drift", "emergency", "full"],
  "simulation_pass_rate": 1.0,
  "constraints_count": 8,
  "state_variables_count": 8,
  "engine_version_compatibility": ">=0.1.0"
}
```

**验收**：
- 导出的 YAML 可被引擎加载
- manifest.json 包含完整元数据
- 未通过校验的 DomainPack 拒绝导出（除非 `--skip-validate`）

---

#### `ptw workbench templates`

**用途**：列出可用的 DomainPack 模板。

```
ptw workbench templates
```

**输出**：

```
可用模板:
  chemical-process    化学工艺优化（CSTR反应器）
  robot               机器人运动控制（6轴机械臂）
  minimal             最小示例（设备监控）
```

**验收**：至少列出 3 个模板，每个模板可通过 `init` 命令创建。

---

### 2.3 内置模板

| 模板名 | 场景 | 状态变量数 | 约束数 | 复杂度 |
|--------|------|-----------|--------|--------|
| `chemical-process` | CSTR 反应器（与 §6 演示场景相同） | 8 | 8 | 高 |
| `robot` | 6 轴机械臂 | 6 | 6 | 中 |
| `minimal` | 设备温度监控 | 3 | 3 | 低 |

模板存储位置：`polymorphic_twin/workbench/templates/`

---

## 3. 数据模型

### 3.1 校验结果模型

```python
class ValidationLevel(str, Enum):
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    FULL = "full"

class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"

class ValidationCheck(BaseModel):
    category: str                    # syntax, schema, reference, compatibility, fallback, domain_of_validity
    result: CheckResult
    message: str
    fix_suggestion: str | None = None

class ValidationReport(BaseModel):
    file_path: str
    level: ValidationLevel
    checks: list[ValidationCheck]
    overall_result: CheckResult
    passed_count: int
    failed_count: int
    timestamp: datetime
```

### 3.2 模拟结果模型

```python
class LoopResult(BaseModel):
    loop_name: str                   # perception, exploration, decision, execution, evolution
    passed: bool
    details: str
    metrics: dict[str, float]        # 延迟、次数等

class ConstraintTimeline(BaseModel):
    constraint_id: str
    states: list[tuple[float, str]]  # [(timestamp, state)]

class SimulationReport(BaseModel):
    domain_pack_id: str
    scenario: str
    duration_seconds: float
    tick_count: int
    loop_results: list[LoopResult]
    constraint_timelines: list[ConstraintTimeline]
    performance: dict[str, dict[str, float]]  # {"constraint_validation": {"p50": 2.0, "p99": 8.0}}
    timestamp: datetime
```

---

## 4. 测试要求

### 4.1 单元测试

| 测试类 | 测试点 | 数量要求 |
|--------|--------|----------|
| `TestValidationPipeline` | 语法校验（合法/非法 YAML）、schema 校验（缺字段/多字段）、语义校验（引用无效/类型冲突）、兼容性校验（5 种刚性-关键性冲突） | ≥ 20 |
| `TestSimulationDataGenerator` | normal_tick 噪声范围、drift_tick 漂移方向和速率、emergency_tick 约束突破 | ≥ 10 |
| `TestExportPipeline` | 导出文件完整性、manifest 格式正确、未校验拒绝导出 | ≥ 8 |
| `TestTemplateLoading` | 3 个模板均可 init、生成的 YAML 可 validate | ≥ 6 |

### 4.2 集成测试

| 测试场景 | 步骤 | 通过标准 |
|----------|------|----------|
| 端到端 init→validate→simulate→export | 从模板创建 → 校验 → 模拟 → 导出 | 全链路无报错，manifest 正确 |
| 化学工艺 full 模拟 | 加载 CSTR DomainPack → simulate --scenario full | 五闭环全部 passed |
| 错误 DomainPack 全流程 | 编写含 3 个错误的 DomainPack → validate → 尝试 simulate → 尝试 export | validate 报告 3 个错误，simulate 拒绝运行，export 拒绝导出 |
| 内存模式完整运行 | 不启动任何数据库，运行全流程 | 无报错 |

### 4.3 验收点

| 编号 | 类别 | 验收项 | 通过标准 |
|------|------|--------|----------|
| M9-V01 | 功能 | `ptw` 命令可用 | `ptw version` 输出版本号 |
| M9-V02 | 功能 | init 命令 | 从 3 个模板各创建一个 DomainPack，全部可校验通过 |
| M9-V03 | 功能 | validate 命令 | 合规 DomainPack PASS，5 种典型错误均能检测 |
| M9-V04 | 功能 | simulate 命令 | full 场景五闭环全部 passed |
| M9-V05 | 功能 | export 命令 | 导出文件可被引擎直接加载 |
| M9-F01 | 检查点 | Rich 输出格式 | 终端输出含表格、颜色、边框，可读性好 |
| M9-F02 | 检查点 | 错误提示可操作性 | 每个校验失败附带 fix_suggestion |
| M9-F03 | 检查点 | 无外部依赖 | 除引擎 SDK 外不引入新的重量级依赖 |
| M9-T01 | 测试 | 单元测试覆盖率 | ≥ 85% |
| M9-T02 | 测试 | 集成测试 | 4 个集成场景全部通过 |
| M9-T03 | 测试 | 模拟数据合理性 | normal_tick 数据在安全范围内，emergency_tick 能触发目标约束 |

---

## 5. 文件结构

```
polymorphic_twin/
├── workbench/
│   ├── __init__.py
│   ├── cli.py                    # CLI 入口 (Click/Typer)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── init.py               # workbench init
│   │   ├── validate.py           # workbench validate
│   │   ├── simulate.py           # workbench simulate
│   │   ├── export.py             # workbench export
│   │   └── templates.py          # workbench templates
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── pipeline.py           # 校验流水线
│   │   ├── syntax_checker.py
│   │   ├── semantic_checker.py
│   │   └── compatibility_checker.py
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── engine.py             # 模拟引擎
│   │   ├── data_generator.py     # 模拟数据生成器
│   │   └── scenarios.py          # 场景定义
│   ├── export/
│   │   ├── __init__.py
│   │   ├── exporter.py           # 导出逻辑
│   │   └── manifest.py           # manifest 生成
│   └── templates/                # 内置模板
│       ├── chemical-process.yaml
│       ├── robot.yaml
│       └── minimal.yaml
└── tests/
    └── workbench/
        ├── unit/
        │   ├── test_validation.py
        │   ├── test_simulation.py
        │   ├── test_export.py
        │   └── test_templates.py
        └── integration/
            ├── test_e2e_workflow.py
            ├── test_chemical_process.py
            ├── test_error_handling.py
            └── test_memory_mode.py
```

---

## 6. 审核记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-05-07 | 初始版本：CLI 设计、校验流水线、模拟引擎、导出功能 |
| v1.1.0 | 2026-05-08 | Jelly 集成：`ptw workbench init --from-jelly` 选项、`validate --check-alignment` 调用 Jelly 数据对齐 |
