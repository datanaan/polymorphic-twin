# DomainPack 格式规范

> **版本**: 1.0.0
> **状态**: 🟡 规划中
> **创建日期**: 2026-05-06
> **对应理论文档**: `04-场景配置与DomainPack.md`, `docs/struc/DomainPack v0.3.md`
> **对应组件**: DomainPack Manager v0.3

---

## 变更历史

| 日期 | 版本 | 变更类型 | 变更内容 | 作者 |
|------|------|----------|----------|------|
| 2026-05-06 | 1.0.0 | 初始 | 文档创建 | - |
| 2026-05-08 | 1.1.0 | 修订 | DomainPack 加载新增双源策略（本地 YAML + Jelly MCP），详见 `2026-05-08-jelly-mcp-client-integration.md §5` | - |

---

## 1. 格式概览

### 1.1 DomainPack 定义

DomainPack 是一个轻量级配置单元，使用 YAML 或 JSON 格式定义特定场景下的 TwinObject 实例化参数。

**文件命名规范**:
- YAML: `{domain_name}-{version}.yaml`
- JSON: `{domain_name}-{version}.json`
- 示例: `robotic-arm-control-1.0.0.yaml`

### 1.2 文件位置

```
domain-packs/
├── official/              # 官方认证的 DomainPack
│   ├── robotic-arm/
│   │   ├── v1.0.0.yaml
│   │   └── v1.1.0.yaml
│   └── code-review/
│       └── v1.0.0.yaml
├── community/             # 社区贡献的 DomainPack
│   └── custom-scenario/
│       └── v0.5.0.yaml
└── templates/             # DomainPack 模板
    └── base-template.yaml
```

---

## 2. 完整格式定义

### 2.1 根结构

```yaml
# ==================== 标识部分 ====================
domain_id: string           # 唯一标识符，格式: {category}.{name}
domain_name: string         # 人类可读名称
domain_version: string      # semver 格式: "1.0.0"
parent_domain_id?: string   # 父 DomainPack ID（可选）

# ==================== 继承策略 ====================
inheritance_policy:
  can_relax_parent_absolute_constraints: boolean    # 默认: false
  can_lower_parent_criticality: boolean              # 默认: false
  conflict_resolution: "stricter_wins" | "require_manual_review"
  parent_update_action: "require_recertification" | "auto_upgrade" | "manual_review"
  parent_retirement_action_by_reason:
    safety_issue: "immediate_degrade_and_require_recertification"
    superseded: "mark_requires_upgrade_with_deadline"
    obsolete: "warn_and_prohibit_new_instantiation"
    administrative: "human_review_required"

# ==================== 刚性-关键性兼容规则 ====================
rigidity_criticality_compatibility:
  safety_critical: "must_be_absolute"
  identity_critical: "absolute_or_strictly_audited"
  operational: "absolute_or_soft_or_learnable"
  informational: "soft_or_learnable"

# ==================== 状态语义实例化 ====================
state_semantics_template:
  ontology_reference: string                    # 外部知识库中的本体 ID
  variables:
    - name: string                              # 变量名
      physical_meaning: string                  # 物理含义
      unit: string                              # 单位
      range_min: number                         # 最小值
      range_max: number                         # 最大值
      observability: "observable" | "partially_observable" | "unobservable"
      controllability: "controllable" | "partially_controllable" | "uncontrollable"
      measurement_source?: string               # 测量源引用
      required: boolean                         # 是否必需

# ==================== 约束卡片集合 ====================
constraint_cards:
  knowledge_base_reference: string              # 外部知识库中的约束模板 ID

  absolute:                                    # 刚性约束
    - constraint_id: string
      domain_override?: object                  # 域覆盖配置
      tolerance_override?: object               # 容差覆盖
      certifier_config?: object                 # 认证器配置
      scenario_criticality: "safety_critical" | "identity_critical" | "operational" | "informational"

  soft:                                        # 软约束
    - constraint_id: string
      weight: number                            # 权重 [0, 1]
      domain_override?: object
      scenario_criticality: "operational" | "informational"

  learnable:                                    # 可学习约束
    - constraint_id: string
      initial_value_source: string
      learning_rate_limit: number
      scenario_criticality: "identity_critical" | "operational" | "informational"
      # 若为 identity_critical，必须经过 strictly_audited 审查

# ==================== 安全回落策略 ====================
safe_fallback:
  policy_id: string
  template_reference: string                    # 引用的回落模板

  domain_of_validity:
    - condition: string                         # 适用条件
      parameter_values: object

  verified_initial_set: array                   # 验证过的初始状态集
  invariant_safe_set: array                     # 不变安全集
  robustness_margin: number                     # 鲁棒性裕度 [0, 1]

  target_state:
    state_description: string
    state_parameters: object

  trajectory_constraints:
    max_rate: object                            # 最大变化率
    forbidden_zones: array                      # 禁止区域

  max_duration: string                          # ISO 8601 持续时间: "PT1H"

  unavailable_action: "human_takeover" | "safe_shutdown" | "freeze"
  post_fallback_action: "hold" | "handoff" | "shutdown"

  verification_record:
    verified_in_simulation: boolean
    verified_scenarios: array
    verified_initial_set_reference: string      # v0.3 新增
    verified_domain_reference: string           # v0.3 新增
    verification_method: string                 # v0.3 新增
    verification_result_summary: string         # v0.3 新增
    last_verification_date: string              # RFC 3339

# ==================== 行动空间模板 ====================
action_templates:
  knowledge_base_reference: string

  immediate_action_types:                       # 可立即执行
    - action_type_id: string
      description_template: string
      applicable_when: array                    # 适用条件
      monitoring_requirements: array            # 监控要求
      fallback_if_fails: string                 # 失败时的回落

  conditional_action_types:                     # 有条件执行
    - action_type_id: string
      description_template: string
      typical_prerequisites: array              # 典型前提条件
      risk_profile: object                      # 风险画像

  forbidden_action_types:                       # 禁止执行
    - action_type_id: string
      description_template: string
      typical_prohibition_reasons: array

# ==================== 人类角色定义 ====================
human_roles:
  - role_id: string
    role_name: string
    authorized_action_types: array              # 授权的行动类型
    exception_request_authority:
      can_request_review: boolean
      can_request_recertification: boolean
      can_request_constraint_revision: boolean
      can_initiate_human_takeover: boolean
      can_initiate_safe_shutdown: boolean
    approval_required_for: array                # 需要审批的行动

# ==================== 验证集引用 ====================
validation_sets:
  public_eval_set_reference: string             # 公开评估集引用
  audit_benchmark_reference?: string            # 审计基准集引用（Lab 不可见）
  production_acceptance_reference?: string     # 生产验收集引用（Lab 不可见）

# ==================== 元信息 ====================
created_at: string                             # RFC 3339
last_modified_at: string                       # RFC 3339
certified_by: string                           # 认证机构/人员
certification_date: string                     # RFC 3339
applicability_scope: string                    # 适用范围描述

# ==================== 扩展字段 ====================
extensions?: object                             # 扩展字段（供未来使用）
```

---

## 3. 完整示例

### 3.1 机器人控制场景 DomainPack

```yaml
# ============================================================
# DomainPack: 四足机器人行走控制
# 版本: 1.0.0
# 认证状态: 已认证
# ============================================================

domain_id: robotics.quadruped_locomotion
domain_name: "四足机器人行走控制"
domain_version: "1.0.0"

# 继承策略
inheritance_policy:
  can_relax_parent_absolute_constraints: false
  can_lower_parent_criticality: false
  conflict_resolution: "stricter_wins"
  parent_update_action: "require_recertification"
  parent_retirement_action_by_reason:
    safety_issue: "immediate_degrade_and_require_recertification"
    superseded: "mark_requires_upgrade_with_deadline"
    obsolete: "warn_and_prohibit_new_instantiation"
    administrative: "human_review_required"

# 刚性-关键性兼容规则
rigidity_criticality_compatibility:
  safety_critical: "must_be_absolute"
  identity_critical: "absolute_or_strictly_audited"
  operational: "absolute_or_soft_or_learnable"
  informational: "soft_or_learnable"

# 状态语义
state_semantics_template:
  ontology_reference: "kb.ontologies.robotics.v1#locomotion"

  variables:
    - name: "joint_positions"
      physical_meaning: "关节角度位置"
      unit: "rad"
      range_min: -3.14159
      range_max: 3.14159
      observability: "observable"
      controllability: "controllable"
      measurement_source: "encoder_feedback"
      required: true

    - name: "joint_velocities"
      physical_meaning: "关节角速度"
      unit: "rad/s"
      range_min: -10.0
      range_max: 10.0
      observability: "observable"
      controllability: "controllable"
      measurement_source: "encoder_feedback"
      required: true

    - name: "contact_forces"
      physical_meaning: "足端接触力"
      unit: "N"
      range_min: 0
      range_max: 500
      observability: "partially_observable"
      controllability: "uncontrollable"
      measurement_source: "force_sensor"
      required: true

    - name: "base_orientation"
      physical_meaning: "机身姿态角"
      unit: "rad"
      range_min: -1.57
      range_max: 1.57
      observability: "observable"
      controllability: "partially_controllable"
      measurement_source: "imu"
      required: true

    - name: "base_linear_velocity"
      physical_meaning: "机身线速度"
      unit: "m/s"
      range_min: -2.0
      range_max: 2.0
      observability: "observable"
      controllability: "controllable"
      measurement_source: "odometry"
      required: true

# 约束卡片
constraint_cards:
  knowledge_base_reference: "kb.constraints.robotics.v1"

  absolute:
    - constraint_id: "force_non_negative"
      scenario_criticality: "safety_critical"
      domain_override:
        min_force: 0
        max_force: 500
      certifier_config:
        tolerance: 0.1
        sample_rate: "100Hz"

    - constraint_id: "torque_limits"
      scenario_criticality: "safety_critical"
      domain_override:
        max_torque_per_joint: 20  # Nm
      certifier_config:
        monitoring_interval: "10ms"
        violation_threshold: 1.0

    - constraint_id: "joint_limits"
      scenario_criticality: "safety_critical"
      domain_override:
        soft_limit_factor: 0.9
      certifier_config:
        preemptive_check: true

    - constraint_id: "energy_conservation"
      scenario_criticality: "operational"
      domain_override:
        max_power: 1000  # W

  soft:
    - constraint_id: "smooth_motion"
      weight: 0.8
      scenario_criticality: "operational"
      domain_override:
        max_jerk: 10  # rad/s^3

    - constraint_id: "stability_margin"
      weight: 0.9
      scenario_criticality: "operational"
      domain_override:
        min_margin: 0.1  # m

    - constraint_id: "energy_efficiency"
      weight: 0.6
      scenario_criticality: "informational"
      domain_override:
        target_efficiency: 0.7

  learnable:
    - constraint_id: "terrain_adaptability"
      initial_value_source: "kb.models.terrain_v1#default"
      learning_rate_limit: 0.01
      scenario_criticality: "operational"

    - constraint_id: "gait_optimization"
      initial_value_source: "kb.models.gait_v1#trot"
      learning_rate_limit: 0.05
      scenario_criticality: "informational"

# 安全回落策略
safe_fallback:
  policy_id: "robotics.locomotion.safe_stop"
  template_reference: "templates.robotics.v1#safe_shutdown"

  domain_of_validity:
    - condition: "normal_operation"
      parameter_values:
        terrain_type: ["flat", "slight_incline"]
        max_slope: 15  # degrees

  verified_initial_set:
    - state:
        joint_positions: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        base_orientation: [0, 0, 0]
        base_linear_velocity: [0, 0, 0]
      timestamp: "2026-05-01T00:00:00Z"

  invariant_safe_set:
    - description: "所有关节在软限位内"
      condition: "all(|joint_positions| < soft_limit)"
    - description: "机身无危险倾斜"
      condition: "max(|base_orientation|) < 0.5 rad"

  robustness_margin: 0.2

  target_state:
    state_description: "安全停止姿态"
    state_parameters:
      joint_positions: "zero_pose"
      base_orientation: "level"
      all_velocities: "zero"

  trajectory_constraints:
    max_rate:
      joint_position_rate: 2.0  # rad/s
      orientation_rate: 1.0     # rad/s
    forbidden_zones:
      - description: "机身倾倒区域"
        condition: "abs(pitch) > 1.0 or abs(roll) > 1.0"

  max_duration: "PT5S"  # 最多5秒完成回落

  unavailable_action: "safe_shutdown"
  post_fallback_action: "hold"

  verification_record:
    verified_in_simulation: true
    verified_scenarios:
      - "normal_flat_terrain"
      - "incline_10_degrees"
      - "sudden_obstacle"
    verified_initial_set_reference: "sim.quadruped.v1#verified_initial_states"
    verified_domain_reference: "sim.quadruped.v1#domain_validity_v1.0"
    verification_method: "Monte Carlo Simulation (N=10000)"
    verification_result_summary: "1000/1000 runs successful, mean_stop_time=2.3s, max_stop_time=4.8s"
    last_verification_date: "2026-05-01T10:00:00Z"

# 行动模板
action_templates:
  knowledge_base_reference: "kb.actions.robotics.v1"

  immediate_action_types:
    - action_type_id: "joint_position_control"
      description_template: "控制关节位置到目标角度"
      applicable_when:
        - "all_joints_within_limits"
        - "no_emergency_active"
      monitoring_requirements:
        - "joint_position_feedback"
        - "torque_monitoring"
      fallback_if_fails: "safe_shutdown"

    - action_type_id: "velocity_command"
      description_template: "发送速度指令"
      applicable_when:
        - "base_stable"
        - "feet_in_contact"
      monitoring_requirements:
        - "velocity_feedback"
        - "slip_detection"
      fallback_if_fails: "stop_velocity_command"

    - action_type_id: "emergency_stop"
      description_template: "紧急停止所有运动"
      applicable_when:
        - "always"
      monitoring_requirements: []
      fallback_if_fails: "safe_shutdown"

  conditional_action_types:
    - action_type_id: "gait_transition"
      description_template: "切换步态"
      typical_prerequisites:
        - "velocity_stable"
        - "terrain_detected"
      risk_profile:
        risk_level: "medium"
        potential_failures: ["stumble", "instability"]

    - action_type_id: "terrain_adaptation"
      description_template: "适应地形变化"
      typical_prerequisites:
        - "terrain_change_detected"
        - "stable_contact"
      risk_profile:
        risk_level: "low"
        potential_failures: ["delayed_adaptation"]

  forbidden_action_types:
    - action_type_id: "beyond_joint_limits"
      description_template: "超出关节物理限位的控制"
      typical_prohibition_reasons:
        - "mechanical_damage_risk"
        - "safety_violation"

    - action_type_id: "unsupported_manipulation"
      description_template: "未验证的操纵动作"
      typical_prohibition_reasons:
        - "safety_unknown"
        - "not_certified"

# 人类角色
human_roles:
  - role_id: "robot_operator"
    role_name: "机器人操作员"
    authorized_action_types:
      - "joint_position_control"
      - "velocity_command"
      - "gait_transition"
    exception_request_authority:
      can_request_review: true
      can_request_recertification: false
      can_request_constraint_revision: false
      can_initiate_human_takeover: true
      can_initiate_safe_shutdown: true
    approval_required_for:
      - "terrain_adaptation"
      - "gait_transition"

  - role_id: "safety_officer"
    role_name: "安全官"
    authorized_action_types:
      - "emergency_stop"
      - "safe_shutdown"
    exception_request_authority:
      can_request_review: true
      can_request_recertification: true
      can_request_constraint_revision: true
      can_initiate_human_takeover: true
      can_initiate_safe_shutdown: true
    approval_required_for: []

  - role_id: "system_admin"
    role_name: "系统管理员"
    authorized_action_types:
      - "system_reconfiguration"
      - "constraint_override"  # 仅在紧急情况
    exception_request_authority:
      can_request_review: true
      can_request_recertification: true
      can_request_constraint_revision: true
      can_initiate_human_takeover: true
      can_initiate_safe_shutdown: true
    approval_required_for: []

# 验证集引用
validation_sets:
  public_eval_set_reference: "eval.robotics.quadruped.v1#public_set_v1.0"
  audit_benchmark_reference: "eval.robotics.quadruped.v1#hidden_benchmark_v1.0"
  production_acceptance_reference: "eval.robotics.quadruped.v1#prod_acceptance_v1.0"

# 元信息
created_at: "2026-05-01T00:00:00Z"
last_modified_at: "2026-05-06T12:00:00Z"
certified_by: "robotics.safety.certification@company.com"
certification_date: "2026-05-05T10:00:00Z"
applicability_scope: "四足机器人在平坦或轻微倾斜地形上的行走控制"

# 扩展字段
extensions:
  simulator_compatibility:
    - "mujoco"
    - "isaac_gym"
  hardware_requirements:
    min_joint_torque: 20  # Nm
    sensor_requirements:
      - "6-axis IMU"
      - "joint encoders"
      - "foot force sensors"
  performance_benchmarks:
    max_velocity: 1.5  # m/s
    max_incline: 15  # degrees
    energy_consumption: 500  # W average
```

---

## 4. 格式验证

### 4.1 必需字段

| 字段路径 | 类型 | 是否必需 | 默认值 |
|---------|------|---------|--------|
| `domain_id` | string | ✅ | - |
| `domain_name` | string | ✅ | - |
| `domain_version` | string (semver) | ✅ | - |
| `inheritance_policy` | object | ✅ | - |
| `rigidity_criticality_compatibility` | object | ✅ | - |
| `state_semantics_template` | object | ✅ | - |
| `constraint_cards` | object | ✅ | - |
| `safe_fallback` | object | ✅ | - |
| `action_templates` | object | ✅ | - |
| `human_roles` | array | ✅ | - |
| `validation_sets` | object | ✅ | - |
| `created_at` | string (RFC 3339) | ✅ | - |
| `certified_by` | string | ✅ | - |
| `certification_date` | string (RFC 3339) | ✅ | - |

### 4.2 刚性-关键性兼容验证

**规则**: `scenario_criticality: safety_critical` 的约束，其 `rigidity` 必须为 `absolute`

**验证逻辑**:
```yaml
validation_rules:
  - rule: "safety_critical_must_be_absolute"
    check: |
      for each constraint in constraint_cards.absolute + constraint_cards.soft + constraint_cards.learnable:
        if constraint.scenario_criticality == "safety_critical":
          assert constraint.rigid == "absolute"
```

**错误示例**:
```yaml
# ❌ 错误：safety_critical 约束不能是 soft
soft:
  - constraint_id: "force_non_negative"
    scenario_criticality: "safety_critical"  # 违反规则
    weight: 1.0
```

### 4.3 继承验证

| 规则 | 描述 |
|------|------|
| `parent_exists` | 父 DomainPack 必须存在 |
| `version_compatible` | 子包版本号必须 ≥ 父包 |
| `stricter_only` | 子包只能收紧，不能放宽父包约束 |
| `fallback_strict` | 子包的回落策略必须 ≥ 父包 |

---

## 5. 视图机制

### 5.1 视图定义

| 视图 | 使用者 | 可见内容 | 隐藏内容 |
|------|--------|----------|----------|
| `CoreFullView` | Core | 全部字段 | - |
| `BridgeActionView` | Bridge | 标识、状态语义、约束摘要、安全回落（不含验证细节）、行动模板、人类角色 | 约束 certifier 完整逻辑、验证集隐藏引用、内部审计字段、父包退役原因详情 |
| `LabExplorationView` | Lab | 标识、状态语义、约束摘要（不含 certifier 和隐藏阈值）、刚性-关键性兼容规则摘要、公开评估集引用 | 约束 certifier 完整逻辑、audit_benchmark_reference、production_acceptance_reference、安全回落策略、人类角色、父包继承链 |
| `AuditView` | 审计系统 | 全部字段 + 完整变更历史 | - |

### 5.2 视图转换示例

**原始 DomainPack**:
```yaml
validation_sets:
  public_eval_set_reference: "eval.robotics.v1#public"
  audit_benchmark_reference: "eval.robotics.v1#hidden"    # Lab 不可见
  production_acceptance_reference: "eval.robotics.v1#prod"  # Lab 不可见
```

**LabExplorationView (Lab 可见)**:
```yaml
validation_sets:
  public_eval_set_reference: "eval.robotics.v1#public"
  # audit_benchmark_reference 被移除
  # production_acceptance_reference 被移除
```

---

## 6. 生命周期状态

### 6.1 状态机

```
         ┌──────────────┐
         │    draft     │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  certified   │◄────────┐
         └──────┬───────┘         │
                │                 │
                ▼                 │
         ┌──────────────┐         │
    ┌───►│  production  │         │
    │    └──────┬───────┘         │
    │           │                 │
    │           ▼                 │
    │    ┌──────────────┐         │
    │    │  deprecated  │         │
    │    └──────┬───────┘         │
    │           │                 │
    │           ▼                 │
    │    ┌──────────────┐         │
    └────┤   retired    │─────────┘
         └──────────────┘
```

### 6.2 状态转换规则

| 转换 | 触发条件 | 要求 |
|------|----------|------|
| `draft → certified` | 约束审查通过、安全回落验证通过、人类角色权限审查通过 | 签名确认 |
| `certified → production` | 生产环境验证通过 | 运营批准 |
| `production → deprecated` | 存在更好替代版本 | 人工标记 |
| `任意状态 → retired` | 明确退役请求 | 声明退役原因 |

### 6.3 修改规则

| 状态 | 修改限制 |
|------|----------|
| `draft` | 可自由修改 |
| `certified` | 小修改可重新认证，大修改需升版本 |
| `production` | 必须重新认证 |
| `deprecated` | 仅元信息可修改 |
| `retired` | 不可修改 |

**特殊规则**:
- `safety_critical` 约束的 `rigidity` 不得从 `absolute` 修改为其他值
- 涉及 `safe_fallback` 策略的修改必须重新验证回落

---

## 7. 错误码

| 错误码 | 含义 | 严重级别 |
|-------|------|----------|
| `DP001` | DomainPack ID 格式无效 | ERROR |
| `DP002` | 版本号不符合 semver | ERROR |
| `DP003` | 父 DomainPack 不存在 | ERROR |
| `DP004` | safety_critical 约束非 absolute | CRITICAL |
| `DP005` | 继承策略冲突 | ERROR |
| `DP006` | 状态变量定义不完整 | WARNING |
| `DP007` | 安全回落策略缺失关键信息 | CRITICAL |
| `DP008` | 行动模板引用不存在 | ERROR |
| `DP009` | 验证集引用不存在 | WARNING |
| `DP010` | 人类角色权限冲突 | ERROR |

---

## 8. 工具支持

### 8.1 验证工具

```bash
# 验证 DomainPack 格式
polymorphic-twin domain-pack validate <file.yaml>

# 检查刚性-关键性兼容性
polymorphic-twin domain-pack check-rigidity <file.yaml>

# 生成视图
polymorphic-twin domain-pack generate-view <file.yaml> --view LabExplorationView

# 转换格式
polymorphic-twin domain-pack convert <file.yaml> --format json
```

### 8.2 Schema 文件

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://schema.polymorphic-twin.io/domainpack/v1.0.0.json",
  "title": "DomainPack",
  "type": "object",
  "required": [
    "domain_id",
    "domain_name",
    "domain_version",
    "inheritance_policy",
    "constraint_cards",
    "safe_fallback",
    "action_templates",
    "human_roles",
    "validation_sets",
    "created_at",
    "certified_by",
    "certification_date"
  ],
  "properties": {
    "domain_id": {
      "type": "string",
      "pattern": "^[a-z]+\\.[a-z_]+$"
    },
    "domain_version": {
      "type": "string",
      "pattern": "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$"
    },
    ...
  }
}
```

---

## 9. 待定事项

| ID | 事项 | 优先级 |
|----|------|--------|
| D001 | DomainPack 之间依赖关系的版本兼容矩阵 | P1 |
| D002 | 大规模 DomainPack 的性能优化 | P2 |
| D003 | DomainPack 的国际化支持 | P2 |
| D004 | 可视化 DomainPack 编辑器 | P3 |

---

## 10. 参考文献

- 理论文档: `docs/framework/04-场景配置与DomainPack.md`
- DomainPack v0.3: `docs/struc/DomainPack v0.3.md`

---

**文档维护者**: [待定]
**审核人**: [待定]
**最后审核日期**: [待定]
