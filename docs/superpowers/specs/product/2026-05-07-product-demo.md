# Polymorphic-Twin 产品化设计规范：演示层

> **版本**: 1.0.0
> **日期**: 2026-05-07
> **状态**: 待审核
> **前置条件**: M10 API 服务完成
> **覆盖里程碑**: M11 (演示层)
> **关联 Spec**: `2026-05-07-product-overview-sdk.md` §6 (演示场景定义), `2026-05-07-product-api-service.md` §2 (API 端点)

---

## 1. 设计决策

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 演示形式 | 单页 Web 应用 + API 驱动脚本 | 最大化演示效果，最小化前端复杂度 |
| 前端技术 | 纯 HTML + CSS + JS（无框架） | 不引入构建工具链，任何人可维护 |
| 数据来源 | 脚本模拟，不需要真实设备 | 可重复演示，无外部依赖 |
| 可视化 | Chart.js 图表 + 自定义约束状态面板 | 轻量级，CDN 引入即可 |
| 目标观众 | 技术评估者 + 决策者 | 既要展示技术深度，又要直观易懂 |

---

## 2. 演示脚本设计

### 2.1 演示数据生成器

独立 Python 脚本，通过 API 推送模拟数据，驱动整个演示流程。

```
demos/
├── chemical_process/
│   ├── demo_runner.py             # 演示主脚本
│   ├── data_generator.py          # 模拟数据生成
│   ├── scenarios/                 # 预定义演示场景
│   │   ├── 01_startup.json
│   │   ├── 02_steady_state.json
│   │   ├── 03_sensor_drift.json
│   │   ├── 04_temperature_spike.json
│   │   ├── 05_emergency.json
│   │   └── 06_recovery.json
│   └── README.md                  # 演示操作说明
```

### 2.2 模拟数据规格

**CSTR 正常工况数据模型**：

```python
class CSTRSimulationState(BaseModel):
    timestamp: float
    temperature: float      # 目标 180-200°C，高斯噪声 σ=2
    pressure: float         # 目标 12-15 atm，高斯噪声 σ=0.5
    concentration_A: float  # 目标 1.5-2.0 mol/L，高斯噪声 σ=0.1
    concentration_B: float  # 目标 1.0-1.5 mol/L，高斯噪声 σ=0.1
    flow_rate_in: float     # 目标 50 L/min，高斯噪声 σ=1
    coolant_flow: float     # 目标 100 L/min，高斯噪声 σ=2
    agitator_speed: float   # 目标 300 RPM，高斯噪声 σ=5
    reaction_rate: float    # 由 Arrhenius 方程计算
```

**各场景数据特征**：

| 阶段 | 文件 | tick 数 | 关键变化 | 预期引擎反应 |
|------|------|---------|----------|-------------|
| 启动 | 01_startup.json | 30 | temperature: 25→180°C (线性) | 约束从 not_applicable→passed |
| 稳态 | 02_steady_state.json | 60 | 全部参数在目标附近波动 | 全部 passed，yield_optimization 学习中 |
| 漂移 | 03_sensor_drift.json | 30 | temperature 传感器偏差 +0.5°C/tick | IdentityMonitor → uncertain |
| 飙升 | 04_temperature_spike.json | 20 | coolant_flow 降至 10，temperature 升至 260°C | thermal_runaway_warning → uncertain→failed |
| 紧急 | 05_emergency.json | 10 | temperature 突破 280°C | safety_critical → fallback triggered |
| 恢复 | 06_recovery.json | 30 | fallback 后逐渐恢复到安全状态 | fallback 完成，Bridge 生成恢复行动空间 |

### 2.3 演示脚本流程

```python
# demo_runner.py 简化流程
async def run_demo(api_base_url: str):
    # Phase 0: 准备
    client = APIClient(api_base_url, admin_key)
    await client.upload_domain_pack("configs/examples/cstr-standard.yaml")
    twin = await client.create_twin("CSTR-Demo-001", domain_pack="cstr.standard")

    # Phase 1-6: 按场景推送数据
    scenarios = ["01_startup", "02_steady_state", "03_sensor_drift",
                 "04_temperature_spike", "05_emergency", "06_recovery"]

    for scenario_name in scenarios:
        data = load_scenario(scenario_name)
        for tick in data.ticks:
            result = await client.update_state(twin.id, tick.values)
            print(f"[{scenario_name}] {tick.timestamp:.1f}s → {result.safety_status}")
            await asyncio.sleep(tick.interval)

    # Phase 7: 输出总结
    summary = await client.get_twin_summary(twin.id)
    audit_log = await client.export_audit(twin.id)
    print_summary(summary, audit_log)
```

### 2.4 验收点

| 编号 | 类别 | 验收项 | 通过标准 |
|------|------|--------|----------|
| DEMO-01 | 功能 | 演示脚本运行 | `python demo_runner.py --api http://localhost:8000` 全流程无报错 |
| DEMO-02 | 功能 | 六阶段走通 | 每个阶段输出正确的 safety_status 变化 |
| DEMO-03 | 功能 | 回落触发 | Phase 5 中 safety_critical 触发，回落 < 200ms |

---

## 3. 可视化面板设计

### 3.1 页面布局

```
┌──────────────────────────────────────────────────────────────────┐
│  Polymorphic-Twin Dashboard         CSTR-Demo-001    ● Active   │
├───────────────────────────────┬──────────────────────────────────┤
│                               │                                  │
│  状态变量时序图                │  约束状态面板                     │
│  ┌───────────────────────┐   │  ┌────────────────────────────┐  │
│  │  Temperature ──────── │   │  │ ● max_temperature   PASS   │  │
│  │  Pressure ────────── │   │  │ ● max_pressure      PASS   │  │
│  │  Concentration_A ─── │   │  │ ● min_coolant_flow  PASS   │  │
│  │  Concentration_B ─── │   │  │ ● mass_balance      PASS   │  │
│  │  ─────────────────── │   │  │ ◐ thermal_runaway   N/A    │  │
│  │   0s    30s   60s    │   │  │ ● reaction_eff.     PASS   │  │
│  └───────────────────────┘   │  │ ○ yield_optim.      LEARN  │  │
│                               │  │ ● agitator_integ.   PASS   │  │
│                               │  └────────────────────────────┘  │
├───────────────────────────────┼──────────────────────────────────┤
│                               │                                  │
│  行动空间                     │  审计日志                         │
│  ┌───────────────────────┐   │  ┌────────────────────────────┐  │
│  │ ✓ Immediate (1)       │   │  │ 10:01:30 state_updated     │  │
│  │   adjust_coolant      │   │  │ 10:01:30 constraint_eval   │  │
│  │ ◐ Conditional (1)     │   │  │ 10:01:31 identity_check    │  │
│  │   adjust_feed_rate    │   │  │ 10:01:32 action_generated  │  │
│  │ ✗ Forbidden (1)       │   │  │ 10:01:33 lab_explore_start │  │
│  │   emergency_override  │   │  │  ...                       │  │
│  │ ? Undetermined (0)    │   │  └────────────────────────────┘  │
│  └───────────────────────┘   │                                  │
├───────────────────────────────┴──────────────────────────────────┤
│  安全状态: ● NORMAL    身份状态: ● CONFIRMED    Uptime: 2m 30s  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 页面组件

#### 状态变量时序图

- 使用 Chart.js 折线图
- X 轴：时间（秒）
- Y 轴：各变量值（多 Y 轴，按单位分组）
- 约束边界用虚线标注（如 temperature 的 280°C 红线）
- 实时更新：通过 WebSocket 推送新数据点
- 回退查看：支持拖拽缩放查看历史

**验收**：图表实时更新，约束边界线可见，能看出温度接近/突破红线的过程。

#### 约束状态面板

- 每个约束一行，显示：名称、当前状态、关键性标签
- 状态用颜色标识：
  - ● passed = 绿色
  - ◐ uncertain = 黄色
  - ✗ failed = 红色（闪烁）
  - ○ not_applicable = 灰色
  - ◎ learnable = 蓝色
- safety_critical 约束加粗显示
- 状态变化时有过渡动画

**验收**：6 个阶段中约束状态变化与脚本输出一致。

#### 行动空间面板

- 四分类列表，每个行动显示：模板名、参数范围、风险等级
- Immediate 行动可点击查看详情
- Forbidden 行动显示 prohibition_reason
- 行动空间版本变化时标记"需刷新"

**验收**：Phase 5 触发回落后，行动空间自动更新。

#### 审计日志

- 实时追加的事件列表
- 每条记录：时间、事件类型、组件、摘要
- 可按类型筛选
- 最新事件自动滚动到底部

**验收**：演示结束时日志条目数与脚本操作数一致。

#### 底部状态栏

- 安全状态：NORMAL / WARNING / FALLBACK / RECOVERING
- 身份状态：CONFIRMED / UNCERTAIN / FORKED
- 运行时间
- 当前 DomainPack 版本

**验收**：Phase 3 漂移时身份状态变为 UNCERTAIN，Phase 5 紧急时安全状态变为 FALLBACK。

### 3.3 技术实现

```
demos/
└── chemical_process/
    └── dashboard/
        ├── index.html              # 单页应用
        ├── style.css               # 样式
        ├── app.js                  # 主逻辑
        ├── websocket.js            # WebSocket 客户端
        ├── charts.js               # Chart.js 配置
        └── components/
            ├── state-chart.js      # 状态变量图
            ├── constraint-panel.js # 约束状态面板
            ├── action-panel.js     # 行动空间面板
            └── audit-log.js        # 审计日志
```

**依赖**：
- Chart.js（CDN 引入）
- 无其他第三方依赖

**连接方式**：
- WebSocket `/api/v1/twins/{id}/ws` 接收实时事件
- REST API 查询历史数据（页面加载时）

**验收**：
- 打开 `index.html` 自动连接 API 服务
- 无需 npm/webpack 等构建工具
- 单个 HTML 文件可直接在浏览器打开

---

## 4. 演示剧本

### 4.1 演示流程脚本（面向演示者）

```
=== Polymorphic-Twin 演示 ===

[准备阶段]
  演示者: docker-compose up
  演示者: 打开浏览器 http://localhost:8000/dashboard
  演示者: python demo_runner.py

[第一幕：启动 — 感知闭环]
  "这是一个化工厂的连续搅拌釜反应器。我们用 Polymorphic-Twin
   来管理它的运行安全。现在反应器正在启动，温度从常温升至工作温度。"
  → 面板展示：温度曲线上升，约束状态逐个变为 passed

[第二幕：稳定运行 — 演化闭环]
  "反应器进入稳定工况。系统正在学习最优的操作参数组合，
   这就是 yield_optimization 约束——它是 learnable 类型的。"
  → 面板展示：yield_optimization 状态为 LEARN，所有约束 passed

[第三幕：传感器漂移 — 身份监控]
  "现在出现了一个问题：温度传感器开始漂移，读数逐渐偏离真实值。
   Polymorphic-Twin 的 IdentityMonitor 检测到了这个异常。"
  → 面板展示：身份状态变为 UNCERTAIN，面板高亮警告
  "注意：系统没有盲目信任传感器数据，而是标记身份不确定。"

[第四幕：温度飙升 — 探索+决策闭环]
  "冷却水系统出现故障，温度开始快速上升。
   Lab 引擎立即开始探索替代控制策略。"
  → 面板展示：温度曲线接近红线，Lab 探索启动
  "Core 对 Lab 的探索结果进行审判，Bridge 生成行动空间。"
  → 面板展示：行动空间更新，出现 conditional 和 forbidden 行动

[第五幕：紧急工况 — 安全回落]
  "温度突破 280°C 安全上限。系统自动触发安全回落——
   关闭进料、全开冷却水、打开排气阀。"
  → 面板展示：安全状态变为 FALLBACK，约束状态 max_temperature 变为 failed
  "注意：这个回落是自动的、不可中断的，反应时间 187ms。"

[第六幕：恢复 — 执行闭环]
  "反应器安全停机。系统生成恢复行动空间，
   操作员可以按照指引逐步恢复。"
  → 面板展示：安全状态变为 RECOVERING，行动空间显示恢复步骤

[总结]
  "这就是 Polymorphic-Twin 的核心价值：
   不是预测——而是审判。它不替你做决定，
   但它保证任何决定都在安全约束之内。"
```

### 4.2 演示要点清单

| 要点 | 对应闭环 | 面板上可见 |
|------|----------|-----------|
| 传感器数据自动转化为 TwinObject | 感知 | 状态变量图实时更新 |
| 约束验证四态判决 | 感知 | 约束面板状态变化 |
| Lab 隔离探索不直接影响生产 | 探索 | Lab 状态显示 running/completed |
| Core 审判 Lab 结果 | 决策 | 行动空间更新 |
| Bridge 结构化行动空间 | 决策 | 四分类行动列表 |
| safety_critical 不可中断回落 | 执行 | 安全状态 FALLBACK + 187ms |
| 身份连续性监控 | 感知 | 身份状态 UNCERTAIN |
| DomainPack 定义场景边界 | — | 约束来自 DomainPack，非硬编码 |

---

## 5. CSTR DomainPack 完整定义

本节提供 M11 演示用的完整 CSTR DomainPack，可直接用于 M9 Workbench 和 M10 API 服务。

### 5.1 DomainPack YAML

```yaml
domain_id: "cstr.standard"
domain_name: "CSTR连续搅拌釜反应器标准场景"
domain_version: "1.0.0"
description: "1000L CSTR放热反应器的约束治理标准配置，用于演示Polymorphic-Twin五闭环能力"
author: "Polymorphic-Twin Team"

# ── 继承策略 ──
inheritance_policy:
  can_relax_parent_absolute_constraints: false
  can_lower_parent_criticality: false
  conflict_resolution: "stricter_wins"

# ── 状态变量 ──
state_variables:
  - name: "temperature"
    unit: "°C"
    physical_range: [20, 350]
    observable: true
    controllable: true
    description: "反应器内部温度"

  - name: "pressure"
    unit: "atm"
    physical_range: [0.5, 50]
    observable: true
    controllable: true
    description: "反应器内部压力"

  - name: "concentration_A"
    unit: "mol/L"
    physical_range: [0, 5]
    observable: true
    controllable: false
    description: "反应物A浓度"

  - name: "concentration_B"
    unit: "mol/L"
    physical_range: [0, 5]
    observable: true
    controllable: false
    description: "产物B浓度"

  - name: "flow_rate_in"
    unit: "L/min"
    physical_range: [0, 100]
    observable: true
    controllable: true
    description: "进料流量"

  - name: "coolant_flow"
    unit: "L/min"
    physical_range: [0, 200]
    observable: true
    controllable: true
    description: "冷却水流量"

  - name: "agitator_speed"
    unit: "RPM"
    physical_range: [0, 500]
    observable: true
    controllable: true
    description: "搅拌速度"

  - name: "reaction_rate"
    unit: "mol/(L·min)"
    physical_range: [0, 10]
    observable: true
    controllable: false
    description: "当前反应速率（由Arrhenius方程计算）"

# ── 约束卡片 ──
constraints:
  - id: "max_temperature"
    description: "反应器温度不得超过280°C"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "temperature"
      operator: "<="
      threshold: 280.0
    domain_of_validity:
      match_mode: "all"
      conditions: []

  - id: "max_pressure"
    description: "反应器压力不得超过45atm"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "pressure"
      operator: "<="
      threshold: 45.0
    domain_of_validity:
      match_mode: "all"
      conditions: []

  - id: "min_coolant_flow"
    description: "温度超过150°C时冷却水流量不得低于20L/min"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "coolant_flow"
      operator: ">="
      threshold: 20.0
    domain_of_validity:
      match_mode: "all"
      conditions:
        - type: "state_range"
          variable: "temperature"
          min: 150.0
          inclusive: true

  - id: "thermal_runaway_warning"
    description: "温度超过200°C且持续上升时，温升速率不得超过5°C/min"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "rate_of_change"
      variable: "temperature"
      operator: "<="
      threshold: 5.0
      window_seconds: 60
    domain_of_validity:
      match_mode: "all"
      conditions:
        - type: "state_range"
          variable: "temperature"
          min: 200.0
          inclusive: true

  - id: "mass_balance"
    description: "物料守恒偏差不得超过0.5%"
    criticality: "identity_critical"
    rigidity: "absolute"
    certifier:
      type: "custom"
      expression: "abs(flow_rate_in * concentration_A - reaction_rate * volume - flow_out * concentration_B) / (flow_rate_in * concentration_A) <= 0.005"
    domain_of_validity:
      match_mode: "all"
      conditions: []

  - id: "reaction_efficiency"
    description: "反应转化率应大于70%"
    criticality: "operational"
    rigidity: "soft"
    penalty:
      type: "linear"
      expression: "0.7 - (concentration_B / (concentration_A + concentration_B))"
      per_unit_cost: 1.0
    certifier:
      type: "custom"
      expression: "concentration_B / (concentration_A + concentration_B) >= 0.7"
    domain_of_validity:
      match_mode: "all"
      conditions:
        - type: "state_range"
          variable: "temperature"
          min: 100.0

  - id: "yield_optimization"
    description: "寻找最优进料流量和冷却水流量组合以最大化收率"
    criticality: "operational"
    rigidity: "learnable"
    certifier:
      type: "learnable"
      target_metric: "concentration_B / (concentration_A + concentration_B)"
      optimization: "maximize"
    domain_of_validity:
      match_mode: "all"
      conditions:
        - type: "state_range"
          variable: "temperature"
          min: 150.0
          max: 250.0

  - id: "agitator_integrity"
    description: "搅拌速度不得超过450RPM以保护设备"
    criticality: "operational"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "agitator_speed"
      operator: "<="
      threshold: 450.0
    domain_of_validity:
      match_mode: "all"
      conditions: []

# ── 安全回落策略 ──
fallback_strategy:
  name: "emergency_shutdown"
  description: "紧急停机：关闭进料、全开冷却水、打开排气阀、停止搅拌"
  trigger: "any safety_critical constraint violation"
  steps:
    - action: "close_feed_valve"
      target_variable: "flow_rate_in"
      set_value: 0
      order: 1
    - action: "max_coolant"
      target_variable: "coolant_flow"
      set_value: 200
      order: 2
    - action: "open_vent"
      target_variable: "pressure"
      target_value: 1.0
      order: 3
    - action: "stop_agitator"
      target_variable: "agitator_speed"
      set_value: 0
      order: 4
  target_state:
    temperature: 50.0
    pressure: 1.0
    flow_rate_in: 0.0
    coolant_flow: 200.0
    agitator_speed: 0.0
  timeout_ms: 200

# ── 行动模板 ──
action_templates:
  - id: "adjust_coolant"
    name: "调整冷却水流量"
    type: "continuous"
    target_variable: "coolant_flow"
    parameter_range: [0, 200]
    required_role: "operator"
    prerequisites: []

  - id: "adjust_feed_rate"
    name: "调整进料流量"
    type: "continuous"
    target_variable: "flow_rate_in"
    parameter_range: [0, 100]
    required_role: "operator"
    prerequisites: []

  - id: "adjust_agitator"
    name: "调整搅拌速度"
    type: "continuous"
    target_variable: "agitator_speed"
    parameter_range: [0, 450]
    required_role: "operator"
    prerequisites: []

  - id: "emergency_shutdown"
    name: "紧急停机"
    type: "discrete"
    required_role: "system"
    auto_trigger: true
    trigger_condition: "any safety_critical violation"

  - id: "scheduled_maintenance"
    name: "计划维护"
    type: "discrete"
    required_role: "maintenance"
    prerequisites:
      - type: "state_range"
        variable: "temperature"
        max: 50.0
      - type: "state_range"
        variable: "pressure"
        max: 5.0

  - id: "exception_override"
    name: "例外请求"
    type: "discrete"
    required_role: "supervisor"
    parameters:
      - name: "justification"
        type: "string"
        required: true
    is_exception_request: true

# ── 人类角色 ──
human_roles:
  - id: "operator"
    name: "操作员"
    permissions: ["adjust_coolant", "adjust_feed_rate", "adjust_agitator"]

  - id: "supervisor"
    name: "主管"
    permissions: ["exception_override"]
    can_approve_exceptions: true

  - id: "domain_expert"
    name: "域专家"
    permissions: []
    can_modify_domain_pack: true

  - id: "maintenance"
    name: "维护工程师"
    permissions: ["scheduled_maintenance"]

  - id: "auditor"
    name: "审计员"
    permissions: []
    read_only: true
    can_export_audit: true

# ── 身份不变量 ──
identity_invariants:
  - name: "thermal_capacity"
    description: "反应器热容不变"
    expected: 4186.0
    tolerance: 0.05
    unit: "J/(kg·K)"

  - name: "reactor_volume"
    description: "反应器容积不变"
    expected: 1000.0
    tolerance: 0.01
    unit: "L"

# ── 域包元数据 ──
metadata:
  industry: "chemical"
  equipment_type: "CSTR"
  recommended_exploration_strategies:
    - "counterexample_finding"
    - "constraint_hypothesis"
  safety_standards_referenced:
    - "IEC 61511"
    - "ISO 45001"
```

---

## 6. 测试要求

### 6.1 演示脚本测试

| 测试场景 | 步骤 | 通过标准 |
|----------|------|----------|
| 全流程运行 | `python demo_runner.py` | 六阶段全部完成，无报错 |
| 断点续跑 | Phase 3 后中断，重新运行 Phase 4-6 | 不依赖前面阶段的状态 |
| API 服务不可用 | 不启动 API 服务运行脚本 | 友好错误提示，不崩溃 |
| 并行演示 | 同时运行 2 个 demo_runner（不同 TwinObject） | 各自独立，互不干扰 |

### 6.2 可视化面板测试

| 测试场景 | 步骤 | 通过标准 |
|----------|------|----------|
| 页面加载 | 打开 index.html | 所有面板渲染，无 JS 错误 |
| 实时更新 | 运行 demo_runner，观察面板 | 状态图、约束面板、行动空间实时更新 |
| WebSocket 断连 | 断开网络后恢复 | 自动重连，不丢失中间状态 |
| 约束变色 | Phase 5 触发 failed | 对应约束行变红闪烁 |
| 回落指示 | Phase 5 安全回落 | 底部状态栏显示 FALLBACK |

### 6.3 端到端演示测试

| 测试场景 | 步骤 | 通过标准 |
|----------|------|----------|
| 一键演示 | `docker-compose up` + `python demo_runner.py` + 打开浏览器 | 从零到完整演示，不超过 5 分钟 |
| 五闭环验证 | 检查每个闭环在演示中是否可见 | 5 个闭环全部有对应面板展示 |
| 审计完整性 | 演示结束后导出审计日志 | 日志条目数 ≥ 操作数 × 2（每操作至少 2 条审计） |

### 6.4 验收点

| 编号 | 类别 | 验收项 | 通过标准 |
|------|------|--------|----------|
| M11-V01 | 功能 | Docker 一键启动 | `docker-compose up` 后 30s 内健康检查通过 |
| M11-V02 | 功能 | 演示脚本运行 | 6 阶段全流程 ≤ 3 分钟 |
| M11-V03 | 功能 | 可视化面板 | 浏览器打开即展示，实时更新 |
| M11-V04 | 功能 | 安全回落演示 | Phase 5 触发回落，面板可见 |
| M11-F01 | 检查点 | 五闭环可见 | 每个闭环在面板上有对应展示区域 |
| M11-F02 | 检查点 | 审计完整 | 每次操作都有审计记录 |
| M11-F03 | 检查点 | DomainPack 驱动 | 演示中约束全部来自 DomainPack，无硬编码 |
| M11-T01 | 测试 | 演示脚本测试 | 4 个场景通过 |
| M11-T02 | 测试 | 面板测试 | 5 个场景通过 |
| M11-T03 | 测试 | 端到端测试 | 3 个场景通过 |
| M11-T04 | 测试 | CSTR DomainPack | 通过 `ptw workbench validate` 全部校验 |

---

## 7. 文件结构

```
demos/
└── chemical_process/
    ├── README.md                  # 演示操作说明
    ├── demo_runner.py             # 演示主脚本
    ├── data_generator.py          # 模拟数据生成器
    ├── scenarios/
    │   ├── 01_startup.json
    │   ├── 02_steady_state.json
    │   ├── 03_sensor_drift.json
    │   ├── 04_temperature_spike.json
    │   ├── 05_emergency.json
    │   └── 06_recovery.json
    ├── dashboard/
    │   ├── index.html
    │   ├── style.css
    │   ├── app.js
    │   ├── websocket.js
    │   ├── charts.js
    │   └── components/
    │       ├── state-chart.js
    │       ├── constraint-panel.js
    │       ├── action-panel.js
    │       └── audit-log.js
    └── tests/
        ├── test_demo_runner.py
        ├── test_data_generator.py
        ├── test_dashboard.py
        └── test_e2e.py

configs/
└── examples/
    └── cstr-standard.yaml         # CSTR DomainPack（完整版）
```

---

## 8. 审核记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-05-07 | 初始版本：演示脚本、可视化面板、CSTR DomainPack 完整定义 |
| v1.1.0 | 2026-05-08 | Jelly 集成：CSTR DomainPack 可从 Jelly 加载（`twin.get_domain_pack`）、演示数据可从 Jelly 获取（`twin.query_operational_history`）、dashboard 新增知识查询面板 |
