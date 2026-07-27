# Jelly Twin Provider：Polymorphic-Twin 外部数据服务需求规格

> **版本**: 1.0.0
> **日期**: 2026-05-08
> **状态**: 待 Jelly 团队评审
> **需求方**: Polymorphic-Twin 项目组
> **交付方**: Jelly 开发团队
> **文档性质**: 完整 PRD + 架构建议 + 初始数据集定义

---

## 0. 关系定义

```
┌──────────────────────────────────────────────────────────────┐
│                   Polymorphic-Twin                           │
│                                                              │
│   Core (约束治理)  Lab (探索引擎)  Bridge (决策接口)          │
│   TOM (对象模型)   DomainPack (场景配置)                      │
│                                                              │
│   完全自治。没有 Jelly 也能运行。                              │
│   Jelly 提供外部数据，Polymorphic-Twin 按需获取。              │
└──────────────────────────┬───────────────────────────────────┘
                           │ MCP 协议
                           │ (Polymorphic-Twin = MCP Client)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   jelly_twin_provider (新项目)                │
│                                                              │
│   MCP Server 暴露 15 个工具                                   │
│   独立存储，独立进程                                          │
│   Jelly 生态内的自治服务                                      │
│                                                              │
│   职责：从 Jelly 知识库提取/生成 Polymorphic-Twin 可消费的    │
│   数据（DomainPack、验证数据集、探索数据、领域知识）            │
│   如何生产数据由 Jelly 团队全权决定。                          │
└──────────────────────────────────────────────────────────────┘
```

**核心原则：**
- Polymorphic-Twin 是 MCP Client，按需调用获取数据
- jelly_twin_provider 是 MCP Server，提供结构化数据
- 不存在"推送"关系，全部是 Polymorphic-Twin 主动拉取
- Polymorphic-Twin 没有也能运行，Jelly 数据是增强不是依赖

---

## 1. 四类数据需求

Polymorphic-Twin 需要外部系统提供四类数据服务：

### 1.1 DomainPack 服务

Polymorphic-Twin 需要获取完整的、已通过加载时验证的 DomainPack 配置。

**需求：**
- 提供指定场景的 DomainPack 完整 YAML/JSON 结构
- 结构必须符合刚性-关键性兼容规则（safety_critical 必须为 absolute）
- 包含完整的状态变量定义、约束卡片、安全回落、行动模板、人类角色
- 支持版本管理和继承链查询
- DomainPack 可按 domain_id 精确查询，也可按场景关键词模糊匹配

### 1.2 验证数据集服务

Core 的模型认证和 Lab 的探索需要验证数据。

**需求：**
- 提供 public_eval_set（公开评估集，Lab 可见）
- 提供 audit_benchmark（审计基准，仅 Audit 可见）
- 提供 production_acceptance_set（生产验收集，仅 Core 可见）
- 每个数据集含结构化的状态-标签对（输入状态 → 期望约束满足状态）
- 数据集必须与 DomainPack 中定义的状态变量对齐（单位、范围一致）

### 1.3 探索数据服务

Lab 的假设探索需要授权数据空间。

**需求：**
- 提供脱敏历史运行数据（按 DataReleasePackage 授权）
- 提供失效日志（FailureLogReleasePackage）
- 数据以 LabExplorationView 投影后的格式提供（不含敏感字段）
- 支持按时间范围、状态变量、设备类型等维度筛选
- 数据中的状态变量必须与 DomainPack 定义对齐

### 1.4 领域知识查询服务

约束演化、假设生成时需要查询领域知识。

**需求：**
- 查询特定物理量（如温度、压力）的安全极限和物理约束
- 查询设备规格（额定参数、工作范围）
- 查询法规标准中的强制阈值
- 查询历史模式（"设备 X 在工况 Y 下通常表现如何"）
- 混合检索能力（关键词 + 语义 + 关联图）

---

## 2. MCP 工具接口定义

共 15 个 MCP 工具，分 5 组。Polymorphic-Twin 作为 MCP Client 调用。

### 2.1 DomainPack 服务（4 个工具）

#### `twin.get_domain_pack`

按 ID 精确获取完整 DomainPack。

```yaml
输入:
  domain_id: str          # 如 "cstr.standard"

输出:
  domain_pack:
    domain_id: str
    domain_name: str
    domain_version: str
    description: str
    state_variables: list[{name, unit, physical_range, observable, controllable, description}]
    constraints: list[{id, description, criticality, rigidity, certifier, domain_of_validity}]
    fallback_strategy: {name, steps, target_state, timeout_ms}
    action_templates: list[{id, name, type, target_variable, parameter_range, required_role}]
    human_roles: list[{id, name, permissions}]
    identity_invariants: list[{name, expected, tolerance, unit}]
    inheritance_policy: dict
    metadata: dict
```

#### `twin.search_domain_packs`

按关键词模糊搜索场景。

```yaml
输入:
  keywords: list[str]           # 如 ["chemical", "reactor"]
  industry: str | null          # 如 "chemical", "energy", "knowledge"
  equipment_type: str | null    # 如 "CSTR", "wind_turbine"

输出:
  results: list[{
    domain_id: str,
    domain_name: str,
    domain_version: str,
    description: str,
    constraint_count: int,
    state_variable_count: int
  }]
```

#### `twin.list_domain_pack_versions`

查询 DomainPack 版本历史。

```yaml
输入:
  domain_id: str

输出:
  versions: list[{
    version: str,
    status: "draft" | "active" | "deprecated" | "archived",
    created_at: str,           # ISO 8601
    constraint_count: int,
    change_summary: str
  }]
```

#### `twin.get_domain_pack_lineage`

查询 DomainPack 继承链。

```yaml
输入:
  domain_id: str

输出:
  lineage: {
    parents: list[{domain_id, version, inherited_constraints}],
    children: list[{domain_id, version}],
    inheritance_chain: list[{domain_id, depth, relationship}]
  }
```

### 2.2 验证数据集服务（2 个工具）

#### `twin.get_validation_set`

获取指定类型的验证数据集。

```yaml
输入:
  domain_id: str
  set_type: "public_eval" | "audit_benchmark" | "production_acceptance"

输出:
  validation_set: {
    domain_id: str,
    set_type: str,
    description: str,
    total_cases: int,
    cases: list[{
      case_id: str,
      input_state: dict[str, float],      # 状态变量值
      expected_result: dict[str, str],     # 约束ID → "passed"|"failed"|"not_applicable"
      tags: list[str]                      # 如 ["boundary", "safety_critical", "normal"]
    }]
  }
```

#### `twin.query_validation_data`

按条件筛选验证数据。

```yaml
输入:
  domain_id: str
  filters:
    set_type: str
    variable_ranges: dict[str, {min, max}] | null
    tags: list[str] | null
    limit: int             # 默认 100，最大 1000

输出:
  filtered_cases: list[{同上}]
  total_matching: int
```

### 2.3 探索数据服务（3 个工具）

#### `twin.get_exploration_data`

获取 Lab 授权的探索数据。

```yaml
输入:
  domain_id: str
  data_release_id: str      # 数据发布授权 ID
  view: "lab_exploration"   # 固定为 lab_exploration

输出:
  exploration_data: {
    domain_id: str,
    data_release_id: str,
    view_applied: "lab_exploration",
    records: list[{
      timestamp: str,                    # ISO 8601
      values: dict[str, float],          # 状态变量值（已过滤）
      labels: dict[str, str] | null      # 工况标签
    }],
    metadata: {
      total_records: int,
      time_range: {from, to},
      variables_included: list[str]
    }
  }
```

**视图过滤规则：** 返回数据中移除以下字段：
- Core 的隐藏验证集信息
- 安全回落策略细节
- 完整的判定逻辑和阈值
- 角色权限配置

#### `twin.get_failure_logs`

获取失效日志包。

```yaml
输入:
  domain_id: str
  time_range: {from: str, to: str}     # ISO 8601
  severity: list[str] | null           # "safety_critical" | "identity_critical" | "operational"

输出:
  failure_log_package: {
    domain_id: str,
    entries: list[{
      timestamp: str,
      failure_type: str,                # "constraint_violation" | "sensor_fault" | "identity_drift"
      constraint_id: str | null,
      severity: str,
      state_at_failure: dict[str, float],
      root_cause_category: str | null,
      duration_seconds: float,
      resolution: str
    }],
    total_entries: int
  }
```

#### `twin.query_operational_history`

查询历史运行数据。

```yaml
输入:
  domain_id: str
  variables: list[str]                 # 要查询的变量名
  time_range: {from: str, to: str}
  aggregation: "raw" | "stats"         # raw=原始值, stats=统计聚合

输出（aggregation="raw"）:
  records: list[{timestamp, values: dict[str, float]}]

输出（aggregation="stats"）:
  stats: dict[variable_name, {
    count: int,
    mean: float,
    std: float,
    min: float,
    max: float,
    p5: float,
    p95: float
  }]
```

### 2.4 领域知识查询（4 个工具）

#### `twin.query_domain_knowledge`

自然语言 + 结构化混合查询。

```yaml
输入:
  domain_id: str
  query: str                          # 如 "CSTR 反应器温度安全极限是多少"
  context: dict | null                # 可选的补充上下文

输出:
  answer: str                         # 结构化回答
  sources: list[{entry_id, type, relevance_score}]
  confidence: float                   # 0-1
```

#### `twin.get_physical_limits`

查询特定物理量的极限值。

```yaml
输入:
  domain_id: str
  variable: str                       # 如 "temperature"

输出:
  limits: list[{
    limit_type: "material_max" | "equipment_rated" | "regulatory" | "empirical",
    value: float,
    unit: str,
    source: str,                      # 如 "ASTM A36", "manufacturer_spec"
    confidence: float,
    conditions: dict | null           # 适用条件
  }]
```

#### `twin.get_equipment_spec`

查询设备规格参数。

```yaml
输入:
  domain_id: str
  equipment_id: str

输出:
  spec: {
    equipment_id: str,
    equipment_type: str,
    parameters: list[{name, value, unit}],
    rated_limits: list[{parameter, value, unit, standard}],
    operating_ranges: list[{parameter, min, max, unit}]
  }
```

#### `twin.get_safety_standards`

查询法规安全标准。

```yaml
输入:
  domain_id: str
  standard_ref: str                   # 如 "IEC 61511"

输出:
  standard: {
    standard_ref: str,
    title: str,
    requirements: list[{description, threshold, unit | null, applicable_conditions}],
    effective_date: str
  }
```

### 2.5 数据对齐与元数据（2 个工具）

#### `twin.get_state_variable_schema`

获取 DomainPack 的状态变量定义。

```yaml
输入:
  domain_id: str

输出:
  schema: list[{
    name: str,
    unit: str,
    physical_range: {min: float, max: float},
    observable: bool,
    controllable: bool,
    description: str
  }]
```

#### `twin.validate_data_alignment`

验证数据与 DomainPack 是否对齐。

```yaml
输入:
  domain_id: str
  data: dict[str, Any]                # 待验证的数据

输出:
  alignment_result: {
    aligned: bool,
    mismatches: list[{
      variable: str,
      issue: "name_mismatch" | "unit_mismatch" | "type_mismatch" | "out_of_range" | "missing",
      expected: str,
      actual: str
    }]
  }
```

---

## 3. 初始数据集定义

共 13 个数据集，按优先级排序。Jelly 团队按此顺序交付。

### 数据集 1：最小设备监控 DomainPack

**用途：** M0 里程碑加载验证。
**规模：** 单个 YAML，~200 行。

| 要素 | 内容 |
|------|------|
| 状态变量 | temperature, pressure, operating_mode, vibration_freq, output_quality（5个） |
| 约束 | 4 absolute（2 safety_critical + 1 identity_critical + 1 operational）+ 1 soft |
| domain_of_validity | 覆盖 5 种条件类型：state_range, state_enum, sensor_status, composite, identity_confidence |
| 安全回落 | 完整 target_state + trajectory_constraints |
| 行动模板 | 2 immediate + 1 conditional + 2 forbidden |
| 人类角色 | operator + supervisor |

### 数据集 2：CSTR 标准场景 DomainPack

**用途：** M11 六阶段演示配置基础。
**规模：** 单个 YAML，~300 行。

| 要素 | 内容 |
|------|------|
| 状态变量 | temperature, pressure, concentration_A, concentration_B, flow_rate_in, coolant_flow, agitator_speed, reaction_rate（8个） |
| 约束 | 4 safety_critical + 1 identity_critical + 2 operational + 1 learnable（8个） |
| 安全回落 | emergency_shutdown 四步（关进料→开冷却→排压→停搅拌），timeout 200ms |
| 行动模板 | 3 continuous + 3 discrete（6个） |
| 人类角色 | operator, supervisor, domain_expert, maintenance, auditor（5个） |
| 身份不变量 | thermal_capacity(4186 J/(kg·K)), reactor_volume(1000 L) |
| 安全标准 | IEC 61511, ISO 45001 |

### 数据集 3：CSTR 工况时序数据

**用途：** Lab 探索 + Core 验证。
**规模：** 600+ 条记录。

格式：
```json
{
  "domain_id": "cstr.standard",
  "data_type": "operational_timeseries",
  "unit_system": "SI",
  "records": [
    {
      "timestamp": "2026-01-15T08:00:00Z",
      "values": {
        "temperature": 180.5,
        "pressure": 12.3,
        "concentration_A": 1.82,
        "concentration_B": 1.18,
        "flow_rate_in": 50.1,
        "coolant_flow": 99.8,
        "agitator_speed": 301.0,
        "reaction_rate": 1.95
      },
      "labels": {
        "operating_phase": "steady_state",
        "safety_status": "normal"
      }
    }
  ]
}
```

六种工况覆盖：

| 工况 | 特征 | 最小条数 | 标签 |
|------|------|----------|------|
| 正常稳态 | 温度 175-185°C，高斯噪声 σ=2 | 100 | `steady_state`, `normal` |
| 启动升温 | 温度 25→180°C 线性 | 100 | `startup`, `normal` |
| 传感器漂移 | 温度读数偏移 +0.5°C/周期 | 100 | `steady_state`, `sensor_drift` |
| 冷却失效 | coolant 下降，温度升至 250-260°C | 100 | `emergency`, `near_miss` |
| 安全回落 | 温度突破 280°C | 100 | `emergency`, `fallback_triggered` |
| 恢复 | 从回落逐步恢复 | 100 | `recovery`, `normal` |

### 数据集 4：失效日志

**用途：** Lab 反例发现、约束假设生成。
**规模：** 50+ 条。

格式：
```json
{
  "domain_id": "cstr.standard",
  "data_type": "failure_log",
  "entries": [
    {
      "timestamp": "2026-01-15T10:23:15Z",
      "failure_type": "constraint_violation",
      "constraint_id": "max_temperature",
      "severity": "safety_critical",
      "state_at_failure": {
        "temperature": 283.5,
        "coolant_flow": 8.2,
        "pressure": 22.1
      },
      "root_cause_category": "equipment_fault",
      "duration_seconds": 47,
      "resolution": "auto_fallback"
    }
  ]
}
```

覆盖分布：

| 失效类型 | 最小条数 |
|----------|----------|
| safety_critical 违规 | 15 |
| identity_critical 违规 | 10 |
| operational 违规 | 15 |
| 传感器故障 | 10 |

### 数据集 5：验证基准集

**用途：** Core 模型认证、Lab 公开评估。
**规模：** 三种集合共计 180+ cases。

格式：
```json
{
  "domain_id": "cstr.standard",
  "set_type": "public_eval",
  "description": "CSTR公开评估集",
  "cases": [
    {
      "case_id": "pe_001",
      "input_state": {"temperature": 150.0, "pressure": 10.0, "coolant_flow": 100.0},
      "expected_result": {
        "max_temperature": "passed",
        "min_coolant_flow": "not_applicable",
        "thermal_runaway_warning": "not_applicable"
      },
      "tags": ["normal", "all_passed"]
    },
    {
      "case_id": "pe_050",
      "input_state": {"temperature": 290.0, "pressure": 30.0, "coolant_flow": 5.0},
      "expected_result": {
        "max_temperature": "failed",
        "min_coolant_flow": "failed",
        "thermal_runaway_warning": "failed"
      },
      "tags": ["emergency", "safety_critical_failed"]
    }
  ]
}
```

三种集合：

| 集合类型 | 可见性 | 最小规模 | 必须覆盖 |
|----------|--------|----------|----------|
| public_eval | Lab + Core | 100 cases | 全 passed、部分 failed、not_applicable |
| audit_benchmark | Audit only | 50 cases | 含边界值 case |
| production_acceptance | Core only | 30 cases | 含极端工况 case |

### 数据集 6：领域知识条目

**用途：** 知识查询服务测试数据。
**规模：** 30+ 条。

格式：
```json
{
  "domain_id": "cstr.standard",
  "knowledge_entries": [
    {
      "entry_id": "phys_limit_temp_steel",
      "type": "physical_limit",
      "variable": "temperature",
      "value": {"unit": "°C", "max": 350.0, "source": "ASTM A36 steel specification"},
      "confidence": 0.98
    },
    {
      "entry_id": "equip_reactor_volume",
      "type": "equipment_spec",
      "equipment_id": "cstr_001",
      "parameters": [
        {"name": "volume", "value": 1000.0, "unit": "L"},
        {"name": "material", "value": "SS316L", "unit": null},
        {"name": "max_working_pressure", "value": 50.0, "unit": "atm"},
        {"name": "thermal_capacity", "value": 4186.0, "unit": "J/(kg·K)"}
      ]
    },
    {
      "entry_id": "safety_iec61511_sil",
      "type": "safety_standard",
      "standard_ref": "IEC 61511",
      "requirements": [
        {"description": "SIL 2 安全完整性等级要求", "threshold": "PFDavg ≤ 10⁻²"}
      ]
    },
    {
      "entry_id": "kinetics_arrhenius",
      "type": "domain_knowledge",
      "description": "反应速率遵循 Arrhenius 方程: k = A·exp(-Ea/RT)",
      "parameters": {"A": "pre-exponential factor", "Ea": "activation energy", "R": "gas constant"},
      "confidence": 0.99
    }
  ]
}
```

四种类型各至少 7 条。

### 数据集 7：风机轴承退化监测

**用途：** M6 多场景验证（场景二）。
**规模：** DomainPack YAML + 600 条时序 + 30 条失效日志 + 80 cases 验证集。

| 要素 | 内容 |
|------|------|
| 状态变量 | vibration_freq(Hz), bearing_temp(°C), rotor_speed(RPM), power_output(kW), oil_quality_index(0-1) |
| 约束 | safety_critical: vibration_freq ≤ 2500 Hz; identity_critical: 温度-转速耦合; operational: 功率范围; soft: 油质量 ≥ 0.7 |
| 安全回落 | 降速停机 |
| 时序数据工况 | 正常运行(200) + 轴承退化(200,振动渐增) + 过速工况(100) + 低温启动(100) |

### 数据集 8：个人知识管理

**用途：** M6 多场景验证（场景三，非物理场景）。
**规模：** DomainPack YAML + 300 条使用日志 + 20 条失效日志 + 30 cases 验证集。

| 要素 | 内容 |
|------|------|
| 状态变量 | knowledge_nodes_count, avg_connection_depth, search_recall_rate, duplicate_ratio, stale_ratio |
| 约束 | identity_critical: 语义一致性; operational: 检索召回率 ≥ 0.8; soft: stale_ratio ≤ 0.1 |
| 使用日志 | 添加笔记、搜索查询、发现关联、知识老化（300条） |

### 数据集 9：大规模性能压测数据

**用途：** M7 生产就绪性能基准。
**规模：** 15,000+ 条。

| 数据 | 规模 |
|------|------|
| CSTR 稳态时序 | 10,000 条连续传感器读数（含正常和边界值） |
| 多变量组合状态 | 5,000 条（覆盖 domain_of_validity 各种边界组合） |

### 数据集 10：边界与异常数据

**用途：** M2-M7 通用约束求值器边界测试。
**规模：** 每种边界场景 50+ 条，共 350+ 条。

| 场景 | 数据特征 |
|------|----------|
| domain_of_validity 精确边界 | 恰好等于 min/max 的状态值（±ε），覆盖 5 种条件类型 |
| 传感器离线 | sensor_status = "offline" 的时序数据 |
| 身份漂移 | invariant 值逐步偏离 expected 的序列 |
| 多约束同时违规 | safety + identity + operational 同时 failed |
| 数据缺失 | 部分变量值为 null/NaN |
| 载荷超限 | > 10MB 的 Lab 提交包（检疫扫描测试用） |
| 敏感信息注入 | 含 "hidden_challenge_set" 字符串的提交 |

### 数据集 11：DomainPack 继承测试数据

**用途：** M6 演化闭环验证。
**规模：** 5 个关联 DomainPack + 配套数据。

| 内容 | 要求 |
|------|------|
| base_equipment | 通用设备基础配置（3 状态变量，2 约束） |
| strict_monitoring | 继承 base_equipment，约束升级，新增 2 约束 |
| high_precision | 继承 strict_monitoring，新增 learnable 约束 |
| deprecated_version | 一个已弃用的版本 |
| conflict_test | 两个父场景约束冲突的组合（测试 stricter_wins 仲裁） |

### 数据集 12：SDK 示例 Fixture

**用途：** M8 pip 包发布后的快速上手。
**规模：** 4 个示例。

| 示例 | 内容 |
|------|------|
| 5 分钟入门 | 最小 DP（3 变量 2 约束）+ 10 条时序 + 预期输出 |
| CSTR 完整 | cstr-standard DP + 50 条稳态 + 预期约束状态 |
| 风机示例 | wind-turbine DP + 50 条退化数据 |
| API 文档 | 每个公共 API 方法的输入/输出数据对 |

### 数据集 13：API 服务多实例数据

**用途：** M10 多租户和并发测试。
**规模：** 3 用户 × 2 TwinObject + 并发数据。

| 内容 | 要求 |
|------|------|
| 多用户 | 3 个不同用户，各有独立 TwinObject |
| 多场景并行 | 同一用户同时运行 CSTR 和风机两个 TwinObject |
| 认证凭据 | admin/operator/viewer 三种角色 |
| 竞争写入 | 两个客户端同时更新同一 TwinObject |

---

## 4. 数据契约与质量保障

### 4.1 数据对齐契约

**核心约束：外部数据必须与 DomainPack 定义对齐。**

```
DomainPack 定义:
  state_variables:
    - name: "temperature", unit: "°C", physical_range: [20, 350]

Jelly 返回的数据必须:
  ✅ key = "temperature"（名称精确匹配）
  ✅ value = 180.5（数值类型 float，非字符串 "180.5"）
  ✅ unit = °C（非 K 或 °F）
  ✅ 20 ≤ value ≤ 350（在物理范围内）

  ❌ key = "temp"（名称不匹配）
  ❌ value = "180.5"（类型错误）
  ❌ 单位混用（K 与 °C 混在同一数据集）
```

**对齐验证：** Polymorphic-Twin 在加载时调用 `twin.validate_data_alignment`，不对齐的数据拒绝加载。

### 4.2 视图隔离契约

Jelly 必须根据调用者身份（`caller` 参数）过滤返回数据：

| caller | 可获取 | 禁止获取 |
|--------|--------|----------|
| `lab` | public_eval, LabExplorationView 投影的时序, 脱敏失效日志 | audit_benchmark, production_acceptance, 安全回落策略细节, 隐藏验证集 |
| `core` | 全部验证集, 完整约束数据, 隐藏验证集 | — |
| `bridge` | 约束摘要(无判定逻辑), 行动模板, 角色定义 | 验证器逻辑, 隐藏验证集, 审计字段 |
| `audit` | 全部数据 + 变更历史 | — |

**Jelly 的责任：** 在数据返回前按 caller 执行过滤。Polymorphic-Twin 信任 Jelly 的过滤结果，不做二次校验。

### 4.3 数据质量保障

| 保障项 | 要求 | 说明 |
|--------|------|------|
| 数值精度 | 浮点数至少 2 位小数 | Core 求值器内置 tolerance 但不依赖 |
| 时间戳 | ISO 8601 格式，同一数据集内时区统一 | UTC 优先 |
| 空值处理 | 必填变量不得为 null/NaN（传感器离线场景除外） | 含 null 时 Polymorphic-Twin 按保守策略处理 |
| 单位一致 | 同一 DomainPack 内同一变量单位始终相同 | 加载时校验，不一致则拒绝 |
| 范围合理 | 数值在 physical_range 内（边界数据集除外） | 超范围触发告警 |
| 时序递增 | 时序数据按 timestamp 严格递增 | 乱序丢弃并记录 |
| 响应时间 | 单次 MCP 调用 < 100ms (p95) | Phase 4 达标 |

### 4.4 错误处理约定

| 场景 | 错误码 | Polymorphic-Twin 行为 |
|------|--------|---------------------|
| DomainPack 不存在 | `domain_pack_not_found` | 降级运行，使用内置默认配置 |
| 服务暂时不可用 | `service_unavailable` | 重试 3 次（1s/2s/4s 指数退避） |
| 数据格式错误 | `data_alignment_error` + mismatch 详情 | 拒绝加载，记录审计日志 |
| 权限不足 | `permission_denied` | 标记操作失败，通知 Bridge |
| 数据量超限 | `payload_too_large` | 自动分页请求 |
| 查询无结果 | `no_data_found` | 返回空集，不报错 |

### 4.5 MCP 调用频率预估

| 场景 | 频率 | 单次数据量 |
|------|------|-----------|
| 获取 DomainPack | 系统启动 + 场景切换 | ~5KB |
| 获取验证数据集 | Core 认证时 | ~100KB |
| 获取探索数据 | Lab 探索启动 | 1-10MB |
| 获取失效日志 | Lab 分析时 | 100KB-1MB |
| 领域知识查询 | Lab 假设生成 | 1-10KB |
| CSTR 演示实时 | ~1 tick/s | ~1KB/tick |

**峰值：** CSTR 六阶段演示，3 分钟内约 180 次 MCP 调用。

---

## 5. 项目架构建议

### 5.1 项目信息

| 项 | 值 |
|----|-----|
| 项目名 | `jelly_twin_provider` |
| 类型 | MCP Server（stdio） |
| 语言 | Python 3.11+（建议） |
| 框架 | FastAPI（建议，Jelly 标准） |
| 存储 | 独立存储（Jelly 团队自选，推荐 SQLite dev + PostgreSQL prod） |

### 5.2 目录结构

```
jelly_twin_provider/
├── server/
│   ├── mcp_server.py          # MCP Server 入口，注册 15 个工具
│   ├── domain_pack_service.py # DomainPack 存储与检索
│   ├── dataset_service.py     # 验证数据集管理
│   ├── exploration_service.py # 探索数据服务（含视图过滤）
│   ├── knowledge_service.py   # 领域知识查询
│   └── alignment_service.py   # 数据对齐校验
├── models/
│   ├── domain_pack.py         # DomainPack 数据模型
│   ├── timeseries.py          # 时序数据模型
│   ├── failure_log.py         # 失效日志模型
│   ├── validation_set.py      # 验证集模型
│   └── knowledge_entry.py     # 领域知识模型
├── storage/
│   ├── base.py                # 存储抽象层
│   ├── sqlite_storage.py      # SQLite 实现（开发用）
│   └── postgres_storage.py    # PostgreSQL 实现（生产用）
├── view_filter/
│   └── filters.py             # 按 caller 返回不同数据范围
├── data/
│   └── seed/                  # 13 个初始数据集的种子文件
│       ├── 01-minimal-device-monitor/
│       ├── 02-cstr-standard/
│       ├── 03-cstr-timeseries/
│       ├── 04-cstr-failure-logs/
│       ├── 05-cstr-validation-sets/
│       ├── 06-cstr-domain-knowledge/
│       ├── 07-wind-turbine-bearing/
│       ├── 08-knowledge-management/
│       ├── 09-performance-stress/
│       ├── 10-boundary-anomaly/
│       ├── 11-dp-inheritance/
│       ├── 12-sdk-fixtures/
│       └── 13-api-multi-instance/
├── tests/
│   ├── test_mcp_tools.py      # MCP 工具接口测试
│   ├── test_view_filters.py   # 视图隔离测试
│   ├── test_data_alignment.py # 数据对齐测试
│   └── test_seed_data.py      # 种子数据完整性测试
└── scripts/
    └── seed.py                # 数据导入脚本
```

### 5.3 核心设计约束

1. **无状态 MCP 调用** — 每次调用携带 domain_id + caller，不依赖会话
2. **视图过滤在 Jelly 侧执行** — 按 caller 过滤后返回
3. **数据预加载** — 种子数据部署时导入，运行时直接查询
4. **独立存储** — 不依赖 Jelly 的 PG/Redis/Typesense/Qdrant
5. **种子数据可验证** — 每个种子文件有对应的完整性校验脚本

---

## 6. 分阶段交付计划

### Phase 1：基础可用（第 1-2 周）

**目标：** Polymorphic-Twin M0-M2 可以对接。

| 交付项 | 验收标准 |
|--------|----------|
| MCP Server 骨架 + 15 个工具注册 | 调用任意工具不报 501 |
| DomainPack 存储 + 检索 | `twin.get_domain_pack("minimal_device_monitor")` 返回完整 YAML |
| DomainPack 搜索 | `twin.search_domain_packs(keywords=["chemical"])` 返回 CSTR |
| 数据对齐校验 | 错误单位/名称/范围的数据被拒绝 |
| 数据集 1 导入 | minimal_device_monitor 可查询 |
| 数据集 2 导入 | cstr.standard 可查询 |
| 数据集 5 导入 | 三种验证集可按 set_type 获取 |
| 数据集 10 导入 | 边界数据可查询 |
| 集成验证 | Polymorphic-Twin 能拿到 DomainPack 并通过加载验证 |

### Phase 2：探索支持（第 3-4 周）

**目标：** M3 Lab 探索闭环可运行。

| 交付项 | 验收标准 |
|--------|----------|
| 探索数据服务 | `twin.get_exploration_data` 返回 LabExplorationView 过滤后数据 |
| 失效日志服务 | `twin.get_failure_logs` 按时间范围和严重级别筛选 |
| 历史数据查询 | `twin.query_operational_history` 支持 raw 和 stats 两种聚合 |
| 视图过滤实现 | Lab caller 获取不到 audit_benchmark 和 production_acceptance |
| 数据集 3 导入 | CSTR 六工况 600+ 条可查询 |
| 数据集 4 导入 | CSTR 失效日志 50+ 条可查询 |
| 数据集 7 导入 | 风机轴承完整场景可查询 |
| 数据集 8 导入 | 知识管理场景可查询 |
| 数据集 11 导入 | 继承链可查询 |
| 集成验证 | Polymorphic-Twin Lab 能拿到授权数据并生成假设 |

### Phase 3：知识与压测（第 5-6 周）

**目标：** M6-M7 多场景验证和生产就绪。

| 交付项 | 验收标准 |
|--------|----------|
| 领域知识查询 | `twin.query_domain_knowledge` 自然语言查询返回结构化结果 |
| 物理极限查询 | `twin.get_physical_limits("cstr.standard", "temperature")` 返回多个来源的极限值 |
| 设备规格查询 | `twin.get_equipment_spec` 返回完整参数列表 |
| 安全标准查询 | `twin.get_safety_standards("cstr.standard", "IEC 61511")` 返回要求清单 |
| 数据集 6 导入 | 30+ 条领域知识可查询 |
| 数据集 9 导入 | 15,000+ 条压测数据可查询 |
| 数据集 12 导入 | SDK 4 个示例 fixture 可用 |
| 数据集 13 导入 | 多租户数据可查询 |
| 性能达标 | 单次 MCP 调用 < 100ms (p95) |
| 集成验证 | M6 三个场景零代码修改通过 |

### Phase 4：生产加固（第 7-8 周）

**目标：** M10-M11 演示就绪。

| 交付项 | 验收标准 |
|--------|----------|
| 错误处理完善 | 6 种错误场景全部有规范返回 |
| 数据新鲜度 | 时序数据严格递增校验 |
| CSTR 演示全流程 | M11 demo_runner 通过 Jelly 拿数据完整跑通六阶段 |
| 文档交付 | MCP 工具 API 文档 + 种子数据说明 + 部署指南 |
| 容错验证 | Jelly 重启后 Polymorphic-Twin 自动重连恢复 |

---

## 附录 A：验收检查清单

### MCP 工具验收

| # | 工具 | 验收条件 |
|---|------|----------|
| 1 | twin.get_domain_pack | 传入已有 domain_id 返回完整配置；传入不存在 ID 返回 domain_pack_not_found |
| 2 | twin.search_domain_packs | 传入 "chemical" 返回 CSTR；传入 "xyz" 返回空列表 |
| 3 | twin.list_domain_pack_versions | 返回至少 1 个版本记录 |
| 4 | twin.get_domain_pack_lineage | 返回继承关系（含 parent/children） |
| 5 | twin.get_validation_set | public_eval 返回 100+ cases；audit_benchmark 不对 lab caller 返回 |
| 6 | twin.query_validation_data | 按 variable_ranges 筛选后条数 < 总条数 |
| 7 | twin.get_exploration_data | 返回数据不含隐藏验证集信息 |
| 8 | twin.get_failure_logs | 按时间范围筛选有效；severity 筛选有效 |
| 9 | twin.query_operational_history | raw 返回原始值；stats 返回 mean/std/min/max |
| 10 | twin.query_domain_knowledge | 查询 "温度极限" 返回含 280°C 的结果 |
| 11 | twin.get_physical_limits | 返回多个来源的极限值 |
| 12 | twin.get_equipment_spec | 返回设备参数列表 |
| 13 | twin.get_safety_standards | 返回标准要求 |
| 14 | twin.get_state_variable_schema | 返回与 DomainPack 一致的变量定义 |
| 15 | twin.validate_data_alignment | 错误数据返回 aligned=false + mismatch 列表 |

### 数据集验收

| # | 数据集 | 验收条件 |
|---|--------|----------|
| 1 | 最小设备监控 DP | 通过 Polymorphic-Twin 加载验证 |
| 2 | CSTR DP | 通过 Polymorphic-Twin 加载验证，8 约束全部可执行 |
| 3 | CSTR 时序数据 | 600+ 条，6 种工况标签完整，变量与 DP 对齐 |
| 4 | CSTR 失效日志 | 50+ 条，4 种类型覆盖，constraint_id 与 DP 对齐 |
| 5 | 验证基准集 | 三种集合共 180+ cases，三种状态(passed/failed/NA)覆盖 |
| 6 | 领域知识 | 30+ 条，4 种类型各 7+ |
| 7 | 风机轴承 | 完整 DP + 600 时序 + 30 日志 + 80 验证集 |
| 8 | 知识管理 | 完整 DP + 300 日志 + 20 日志 + 30 验证集 |
| 9 | 压测数据 | 15,000+ 条 |
| 10 | 边界数据 | 350+ 条，7 种场景各 50+ |
| 11 | DP 继承 | 5 个关联 DP + 继承链正确 |
| 12 | SDK Fixture | 4 个示例可运行 |
| 13 | 多实例数据 | 3 用户 × 2 Twin 并行 |

---

## 附录 B：参考文档

| 文档 | 位置 |
|------|------|
| Polymorphic-Twin 理论框架 | `docs/framework/` (8 份) |
| Python 单体设计规范 v2.0.0 | `docs/superpowers/specs/2026-05-06-python-monolith-design.md` |
| CSTR 演示设计规范 | `docs/superpowers/specs/2026-05-07-product-demo.md` |
| M0 DomainPack 计划 | `docs/superpowers/plans/plan-M0-domainpack-design.md` |
| M2 Core 引擎计划 | `docs/superpowers/plans/plan-M2-core-engine.md` |
| M6 多场景计划 | `docs/superpowers/plans/plan-M6-multiscene.md` |
| M11a 演示数据计划 | `docs/superpowers/plans/plan-M11a-demo-data.md` |
| Jelly 平台架构 | `docs/jelly-platform-architecture.md` |
