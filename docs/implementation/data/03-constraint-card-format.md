# 约束卡片格式规范

> **版本**: 1.0.0
> **状态**: 🟡 规划中
> **创建日期**: 2026-05-06
> **对应理论文档**: `02-核心原理与约束治理.md`
> **对应组件**: Core v1.3

---

## 变更历史

| 日期 | 版本 | 变更类型 | 变更内容 | 作者 |
|------|------|----------|----------|------|
| 2026-05-06 | 1.0.0 | 初始 | 文档创建 | - |
| 2026-05-08 | 1.1.0 | 修订 | 约束卡片 knowledge_base_reference 可指向 Jelly MCP 数据源 | - |

---

## 1. 格式概览

### 1.1 约束卡片定义

约束卡片是 Core 中约束的最小结构化单元，定义了约束的行为、验证逻辑和回落策略。

**文件命名规范**:
- YAML: `{category}-{constraint_id}-{version}.yaml`
- JSON: `{category}-{constraint_id}-{version}.json`
- 示例: `security-force_non_negative-1.0.0.yaml`

### 1.2 文件位置

```
constraint-cards/
├── official/              # 官方认证的约束卡片
│   ├── security/
│   │   ├── force_non_negative-1.0.0.yaml
│   │   └── torque_limits-1.0.0.yaml
│   ├── quality/
│   │   └── test_coverage-1.0.0.yaml
│   └── performance/
│       └── response_time-1.0.0.yaml
├── custom/                # 自定义约束卡片
│   └── business/
│       └── cost_limit-1.0.0.yaml
└── templates/             # 约束卡片模板
    ├── base_template.yaml
    └── numeric_constraint.yaml
```

---

## 2. 完整格式定义

### 2.1 根结构

```yaml
# ==================== 标识信息 ====================
constraint_id: string           # 唯一标识符
name: string                   # 人类可读名称
version: string                # semver 格式: "1.0.0"
category: string               # 分类: security | quality | performance | business | compliance | custom

# ==================== 约束等级 ====================
level: "hard" | "critical" | "soft" | "info"
rigidity: "absolute" | "soft" | "learnable"
scenario_criticality: "safety_critical" | "identity_critical" | "operational" | "informational"

# ==================== 适用范围 ====================
scope:
  object_types: array          # 适用的对象类型
  object_pattern?: string      # 对象 ID 匹配模式 (glob)
  conditions: array            # 适用条件

# ==================== 触发配置 ====================
trigger:
  type: "on_produce" | "on_transform" | "on_access" | "scheduled"
  target: string               # 触发目标 (对象属性或操作)
  timing?: object              # 定时触发配置

# ==================== 验证配置 ====================
validation:
  method: string               # 验证方法
  tool?: string                # 验证工具
  config: object               # 验证配置
  timeout: string              # 验证超时 (ISO 8601)

# ==================== 判定逻辑 ====================
decision:
  pass_conditions: array       # 通过条件
  fail_conditions: array       # 失败条件
  partial_conditions?: array   # 部分通过条件
  score_calculation: string    # 得分计算表达式

# ==================== 回落策略 ====================
fallback:
  strategy: "same_level_alternative" | "degraded_execution" | "human_intervention" | "reject" | "system_isolation"
  alternatives: array          # 替代方案
  required?: boolean           # 是否必须执行回落

# ==================== 元数据 ====================
metadata:
  description: string
  rationale: string            # 约束原因
  owner: string                # 负责人/团队
  created_at: string           # RFC 3339
  last_modified: string        # RFC 3339
  tags: array                  # 标签
  references: array            # 参考文档
```

---

## 3. 约束等级系统

### 3.1 等级定义

| 等级 | 名称 | 违反后果 | 适用场景 |
|------|------|----------|----------|
| `hard` | 刚性约束 | 系统拒绝执行 | 安全策略、法律合规 |
| `critical` | 关键约束 | 强制执行回落 | 性能阈值、资源上限 |
| `soft` | 建议约束 | 记录偏离，继续执行 | 风格偏好、最佳实践 |
| `info` | 参考约束 | 仅用于报告和优化 | 历史基准、统计参考 |

### 3.2 刚性定义

| 刚性 | 名称 | 可调整性 | 违反处理 |
|------|------|----------|----------|
| `absolute` | 绝对约束 | 不可调整 | 直接拒绝 |
| `soft` | 软约束 | 可加权重 | 计入总分 |
| `learnable` | 可学习约束 | 可从数据学习 | 动态调整 |

### 3.3 场景关键性

| 关键性 | 允许的刚性 | 说明 |
|--------|-----------|------|
| `safety_critical` | 仅 `absolute` | 安全关键，不可妥协 |
| `identity_critical` | `absolute` 或 `learnable` (需审计) | 身份关键，需严格审计 |
| `operational` | 任意刚性 | 运行层面，灵活处理 |
| `informational` | `soft` 或 `learnable` | 信息层面，记录即可 |

### 3.4 兼容性规则

```yaml
# rigid-criticality 兼容性矩阵
safety_critical:
  allowed_rigidity: ["absolute"]
  reason: "安全关键约束必须绝对，不可妥协"

identity_critical:
  allowed_rigidity: ["absolute", "learnable"]
  learnable_requirements:
    - "strictly_audited"
    - "manual_confirmation_required"
    - "change_log_mandatory"
  reason: "身份关键约束可以学习，但必须严格审计"

operational:
  allowed_rigidity: ["absolute", "soft", "learnable"]
  reason: "运行层面约束，可根据情况选择"

informational:
  allowed_rigidity: ["soft", "learnable"]
  reason: "信息层面约束，不进入硬门槛"
```

---

## 4. 验证方法库

### 4.1 通用验证方法

| 方法 | 描述 | 输入 | 输出 |
|------|------|------|------|
| `pattern_match` | 模式匹配 | 字符串/代码 | bool |
| `range_check` | 范围检查 | 数值 | bool |
| `enum_check` | 枚举检查 | 任意值 | bool |
| `reference_check` | 引用检查 | 对象引用 | bool |
| `schema_validation` | Schema 验证 | 结构化数据 | bool + 错误详情 |
| `custom_function` | 自定义函数 | 任意 | bool |

### 4.2 安全验证方法

| 方法 | 描述 | 工具示例 |
|------|------|----------|
| `static_analysis` | 静态代码分析 | bandit, semgrep, SonarQube |
| `dependency_scan` | 依赖扫描 | Snyk, Dependabot |
| `secret_detection` | 密钥检测 | gitleaks, truffleHog |
| `vulnerability_scan` | 漏洞扫描 | OWASP ZAP, Burp Suite |

### 4.3 质量验证方法

| 方法 | 描述 | 工具示例 |
|------|------|----------|
| `test_coverage` | 测试覆盖率 | pytest-cov, coverage.py |
| `lint_check` | 代码规范检查 | flake8, eslint, pylint |
| `complexity_analysis` | 复杂度分析 | radon, lizard |
| `duplicate_detection` | 重复代码检测 | jscpd, cpd |

### 4.4 性能验证方法

| 方法 | 描述 | 工具示例 |
|------|------|----------|
| `benchmark` | 性能基准测试 | pytest-benchmark, JMH |
| `profiling` | 性能分析 | cProfile, py-spy |
| `load_test` | 负载测试 | locust, k6 |
| `latency_check` | 延迟检查 | Apache Bench, wrk |

---

## 5. 完整示例

### 5.1 示例 1: 安全约束 - 力非负

```yaml
# ============================================================
# 约束卡片: 接触力非负
# 类别: 安全
# 等级: Hard
# 刚性: Absolute
# 场景关键性: Safety Critical
# ============================================================

constraint_id: "force_non_negative"
name: "接触力非负约束"
version: "1.0.0"
category: "security"

# 约束等级
level: "hard"
rigidity: "absolute"
scenario_criticality: "safety_critical"

# 适用范围
scope:
  object_types:
    - "device"
    - "sensor"
  object_pattern: "sensor-force-*"
  conditions:
    - field: "content.device.device_type"
      operator: "equals"
      value: "force_sensor"

# 触发配置
trigger:
  type: "on_produce"
  target: "content.device.state.contact_forces"

# 验证配置
validation:
  method: "range_check"
  config:
    field: "content.device.state.contact_forces"
    min: 0
    max: 500  # N
    check_all: true
  timeout: "PT1S"

# 判定逻辑
decision:
  pass_conditions:
    - "all(contact_forces >= 0)"
  fail_conditions:
    - "any(contact_forces < 0)"
  score_calculation: "all(contact_forces >= 0) ? 1.0 : 0.0"

# 回落策略
fallback:
  strategy: "reject"
  alternatives:
    - description: "拒绝并返回错误"
      action: "return_error"
      error_code: "VIOLATION_FORCE_NEGATIVE"
  required: true

# 元数据
metadata:
  description: "确保所有接触力传感器读数为非负值"
  rationale: "物理上接触力不可能为负，负值表示传感器故障或数据异常"
  owner: "robotics.safety@company.com"
  created_at: "2026-05-01T00:00:00Z"
  last_modified: "2026-05-01T00:00:00Z"
  tags:
    - "physics"
    - "safety"
    - "sensor_validation"
  references:
    - "ISO 13482:2014 - Safety requirements for personal care robots"
    - "Robotics Safety Guidelines v2.0"
```

### 5.2 示例 2: 性能约束 - 响应时间

```yaml
# ============================================================
# 约束卡片: API 响应时间
# 类别: 性能
# 等级: Critical
# 刚性: Soft
# 场景关键性: Operational
# ============================================================

constraint_id: "api_response_time"
name: "API 响应时间约束"
version: "1.2.0"
category: "performance"

# 约束等级
level: "critical"
rigidity: "soft"
scenario_criticality: "operational"

# 适用范围
scope:
  object_types:
    - "api_endpoint"
  object_pattern: "api-*"
  conditions:
    - field: "attributes.environment"
      operator: "in"
      value: ["production", "staging"]

# 触发配置
trigger:
  type: "on_produce"
  target: "content.response_time_ms"

# 验证配置
validation:
  method: "benchmark"
  config:
    field: "content.response_time_ms"
    thresholds:
      p50: 50
      p90: 100
      p99: 200
    unit: "ms"
  timeout: "PT5S"

# 判定逻辑
decision:
  pass_conditions:
    - "response_time_p99 <= 200"
  fail_conditions:
    - "response_time_p99 > 500"
  partial_conditions:
    - "response_time_p99 > 200 && response_time_p99 <= 500"
  score_calculation: |
    if (response_time_p99 <= 200) return 1.0;
    if (response_time_p99 <= 500) return 1.0 - (response_time_p99 - 200) / 300;
    return 0.0;

# 回落策略
fallback:
  strategy: "degraded_execution"
  alternatives:
    - description: "启用缓存"
      action: "enable_cache"
      config:
        ttl: "PT30S"
    - description: "降级为只读模式"
      action: "read_only_mode"
  required: false

# 元数据
metadata:
  description: "API 响应时间必须在 P99 < 200ms 范围内"
  rationale: "用户体验要求，超过 200ms 会影响系统可用性"
  owner: "platform.performance@company.com"
  created_at: "2026-04-15T00:00:00Z"
  last_modified: "2026-05-06T10:00:00Z"
  tags:
    - "slo"
    - "performance"
    - "api"
  references:
    - "SRE Book - Service Level Objectives"
    - "Internal Performance Standards v1.0"
```

### 5.3 示例 3: 质量约束 - 测试覆盖率

```yaml
# ============================================================
# 约束卡片: 代码测试覆盖率
# 类别: 质量
# 等级: Soft
# 刚性: Soft
# 场景关键性: Operational
# ============================================================

constraint_id: "test_coverage"
name: "代码测试覆盖率约束"
version: "1.0.0"
category: "quality"

# 约束等级
level: "soft"
rigidity: "soft"
scenario_criticality: "operational"

# 适用范围
scope:
  object_types:
    - "code"
  object_pattern: "code-*"
  conditions:
    - field: "attributes.module"
      operator: "not_in"
      value: ["test", "mock", "fixture"]

# 触发配置
trigger:
  type: "on_produce"
  target: "content.code.metrics.test_coverage"

# 验证配置
validation:
  method: "test_coverage"
  tool: "pytest-cov"
  config:
    min_coverage: 0.8
    exclude_paths:
      - "*/tests/*"
      - "*/migrations/*"
      - "*/__init__.py"
  timeout: "PT30S"

# 判定逻辑
decision:
  pass_conditions:
    - "test_coverage >= 0.9"
  fail_conditions:
    - "test_coverage < 0.7"
  partial_conditions:
    - "test_coverage >= 0.7 && test_coverage < 0.9"
  score_calculation: |
    if (test_coverage >= 0.9) return 1.0;
    if (test_coverage >= 0.7) return (test_coverage - 0.7) / 0.2;
    return 0.0;

# 回落策略
fallback:
  strategy: "human_intervention"
  alternatives:
    - description: "请求添加测试"
      action: "request_tests"
    - description: "标记为技术债务"
      action: "create_debt_ticket"
  required: false

# 元数据
metadata:
  description: "代码模块的测试覆盖率必须达到 80% 以上"
  rationale: "保证代码质量和可维护性"
  owner: "engineering.quality@company.com"
  created_at: "2026-03-01T00:00:00Z"
  last_modified: "2026-05-01T15:00:00Z"
  tags:
    - "testing"
    - "quality"
    - "coverage"
  references:
    - "Testing Best Practices v1.0"
    - "Code Quality Guidelines"
```

### 5.4 示例 4: 可学习约束 - 地形适应性

```yaml
# ============================================================
# 约束卡片: 地形适应性参数
# 类别: 运行
# 等级: Soft
# 刚性: Learnable
# 场景关键性: Operational
# ============================================================

constraint_id: "terrain_adaptability"
name: "地形适应性约束"
version: "1.0.0"
category: "operational"

# 约束等级
level: "soft"
rigidity: "learnable"
scenario_criticality: "operational"

# 适用范围
scope:
  object_types:
    - "agent"
  object_pattern: "agent-*"
  conditions:
    - field: "content.agent.capability_set"
      operator: "contains"
      value: "locomotion"

# 触发配置
trigger:
  type: "scheduled"
  target: "content.agent.model_config.parameters"
  timing:
    interval: "PT1H"  # 每小时学习一次
    initial_delay: "PT10M"

# 验证配置
validation:
  method: "custom_function"
  config:
    function: "evaluate_terrain_adaptation"
    parameters:
      - "terrain_type"
      - "success_rate"
      - "energy_efficiency"
  learning:
    enabled: true
    algorithm: "bayesian_optimization"
    learning_rate_limit: 0.01
    min_samples: 100
    safety_bounds:
      min_value: 0.1
      max_value: 0.9
  timeout: "PT10S"

# 判定逻辑
decision:
  pass_conditions:
    - "adaptation_score >= 0.7"
  fail_conditions:
    - "adaptation_score < 0.5"
  partial_conditions:
    - "adaptation_score >= 0.5 && adaptation_score < 0.7"
  score_calculation: |
    adaptation_score = 0.6 * success_rate + 0.4 * energy_efficiency
    return adaptation_score

# 回落策略
fallback:
  strategy: "same_level_alternative"
  alternatives:
    - description: "使用默认参数"
      action: "use_default_parameters"
      parameters:
        source: "kb.models.terrain_v1#default"
    - description: "请求人类干预"
      action: "human_intervention"
  required: false

# 元数据
metadata:
  description: "机器人的地形适应性参数可以从运行中学习优化"
  rationale: "不同地形需要不同的运动参数，学习可以提高适应性"
  owner: "robotics.research@company.com"
  created_at: "2026-05-01T00:00:00Z"
  last_modified: "2026-05-06T08:00:00Z"
  tags:
    - "machine_learning"
    - "adaptation"
    - "locomotion"
  references:
    - "Reinforcement Learning for Robotics"
    - "Terrain Adaptation Research Paper"
```

---

## 6. 约束组合

### 6.1 逻辑组合

```yaml
# AND 组合
composite_constraint:
  type: "and"
  constraints:
    - constraint_id: "force_non_negative"
    - constraint_id: "torque_limits"
    - constraint_id: "joint_limits"

# OR 组合
composite_constraint:
  type: "or"
  constraints:
    - constraint_id: "primary_path"
    - constraint_id: "fallback_path"

# NOT 组合
composite_constraint:
  type: "not"
  constraint:
    constraint_id: "dangerous_condition"

# 加权组合
composite_constraint:
  type: "weighted"
  constraints:
    - constraint_id: "safety_1"
      weight: 0.5
    - constraint_id: "safety_2"
      weight: 0.3
    - constraint_id: "safety_3"
      weight: 0.2
```

### 6.2 优先级组合

```yaml
# 按优先级评估，第一个满足的约束决定结果
priority_constraint:
  type: "priority"
  constraints:
    - constraint_id: "safety_critical_rule"
      priority: 1
    - constraint_id: "operational_rule"
      priority: 2
    - constraint_id: "best_practice"
      priority: 3
```

---

## 7. 格式验证

### 7.1 必需字段

| 字段路径 | 类型 | 是否必需 | 默认值 |
|---------|------|---------|--------|
| `constraint_id` | string | ✅ | - |
| `name` | string | ✅ | - |
| `version` | string (semver) | ✅ | - |
| `category` | string | ✅ | - |
| `level` | enum | ✅ | - |
| `rigidity` | enum | ✅ | - |
| `scenario_criticality` | enum | ✅ | - |
| `scope` | object | ✅ | - |
| `trigger` | object | ✅ | - |
| `validation` | object | ✅ | - |
| `decision` | object | ✅ | - |
| `fallback` | object | ✅ | - |
| `metadata` | object | ✅ | - |

### 7.2 刚性-关键性验证

**规则**: 验证 `rigidity` 和 `scenario_criticality` 的兼容性

```yaml
validation_rules:
  - rule: "rigidity_criticality_compatibility"
    check: |
      if (scenario_criticality == "safety_critical" && rigidity != "absolute"):
        error("safety_critical 约束必须是 absolute")

      if (scenario_criticality == "identity_critical" && rigidity == "soft"):
        error("identity_critical 约束不能是 soft")

      if (scenario_criticality == "informational" && rigidity == "absolute"):
        warning("informational 约束通常不建议使用 absolute")
```

---

## 8. 工具支持

### 8.1 命令行工具

```bash
# 验证约束卡片
polymorphic-twin constraint validate <file.yaml>

# 检查刚性-关键性兼容性
polymorphic-twin constraint check-compatibility <file.yaml>

# 测试约束
polymorphic-twin constraint test <file.yaml> --test-data <data.json>

# 生成测试用例
polymorphic-twin constraint generate-tests <file.yaml>

# 转换格式
polymorphic-twin constraint convert <file.yaml> --format json
```

### 8.2 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://schema.polymorphic-twin.io/constraint/v1.0.0.json",
  "title": "ConstraintCard",
  "type": "object",
  "required": [
    "constraint_id",
    "name",
    "version",
    "category",
    "level",
    "rigidity",
    "scenario_criticality",
    "scope",
    "trigger",
    "validation",
    "decision",
    "fallback",
    "metadata"
  ],
  "properties": {
    "constraint_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$"
    },
    "level": {
      "type": "string",
      "enum": ["hard", "critical", "soft", "info"]
    },
    "rigidity": {
      "type": "string",
      "enum": ["absolute", "soft", "learnable"]
    },
    "scenario_criticality": {
      "type": "string",
      "enum": ["safety_critical", "identity_critical", "operational", "informational"]
    },
    ...
  }
}
```

---

## 9. 错误码

| 错误码 | 含义 | 严重级别 |
|-------|------|----------|
| `CC001` | 约束 ID 格式无效 | ERROR |
| `CC002` | 版本号不符合 semver | ERROR |
| `CC003` | 刚性-关键性不兼容 | CRITICAL |
| `CC004` | 验证方法不存在 | ERROR |
| `CC005` | 回落策略无效 | ERROR |
| `CC006` | 判定逻辑语法错误 | ERROR |
| `CC007` | 范围配置无效 | WARNING |
| `CC008` | 工具配置无效 | WARNING |
| `CC009` | 学习参数超出安全范围 | ERROR |
| `CC010` | 超时配置不合理 | WARNING |

---

## 10. 待定事项

| ID | 事项 | 优先级 |
|----|------|--------|
| C001 | 约束依赖关系管理 | P1 |
| C002 | 约束版本迁移策略 | P1 |
| C003 | 约束性能基准测试 | P2 |
| C004 | 可视化约束编辑器 | P3 |

---

## 11. 参考文献

- 理论文档: `docs/framework/02-核心原理与约束治理.md`
- 系统架构: `docs/implementation/architecture/01-system-overview.md`
- Core API: `docs/implementation/interfaces/01-core-api.md`

---

**文档维护者**: [待定]
**审核人**: [待定]
**最后审核日期**: [待定]
