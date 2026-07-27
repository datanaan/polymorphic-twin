# M0: DomainPack 创建设计与知识库对接

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成首个 DomainPack 的完整 YAML 定义，建立加载时验证基础设施（刚性-关键性兼容检查脚本），确保后续所有组件开发都有真实的数据配置可依赖。

**Architecture:** M0 不写运行时代码。产出物是：(1) 一份完整的 DomainPack YAML 配置文件 (2) 一个独立的验证脚本，能检测刚性-关键性违规、引用完整性、必填字段缺失。

**Spec reference:** `docs/superpowers/specs/2026-05-06-python-monolith-design.md` v2.0.0 §3.6

**Milestone reference:** `docs/struc/Polymorphic-Twin 开发里程碑与关键检查点.md` §二、M0

**Quality gate:** M0 完成前，验证脚本必须能：
- 正确接受一份合规的 DomainPack
- 正确拒绝 safety_critical + soft 的刚性-关键性冲突
- 正确拒绝引用未定义状态变量的约束卡片
- 正确拒绝缺少安全回落策略的 DomainPack

---

## File Structure

```
polymorphic-twin/
├── configs/
│   └── examples/
│       └── minimal-domain-pack.yaml    # Task 1: 首个完整 DomainPack
├── scripts/
│   └── validate_domainpack.py          # Task 2: 验证脚本
└── tests/
    └── unit/
        └── test_domainpack_validation.py  # Task 3: 验证脚本的测试
```

---

## Task 1: 创建首个完整 DomainPack

**Files:**
- Create: `configs/examples/minimal-domain-pack.yaml`

**Purpose:** 提供一个涵盖所有 DomainPack 字段的最小但完整的配置，作为后续 M1-M7 所有组件的开发和测试数据基础。

**Milestone M0-D1 对应:** 配置完整性，每个字段有值或合理的空默认。

- [ ] **Step 1: 创建 configs/examples/ 目录**

```bash
mkdir -p configs/examples
```

- [ ] **Step 2: 编写 DomainPack YAML**

此 YAML 必须包含 Spec §3.6 定义的完整结构，包括 domain_of_validity 的五种条件类型。

```yaml
# configs/examples/minimal-domain-pack.yaml
# Polymorphic-Twin 首个示例 DomainPack
# 场景：简化的工业设备监控（演示用，非真实工业场景）

domain_id: "example.minimal_device_monitor"
domain_name: "最小设备监控场景"
domain_version: "0.1.0"

# ── 继承策略 ──
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

# ── 刚性-关键性兼容规则 ──
rigidity_criticality_compatibility:
  safety_critical: "must_be_absolute"
  identity_critical: "absolute_or_strictly_audited"
  operational: "absolute_or_soft_or_learnable"
  informational: "soft_or_learnable"

# ── 状态语义 ──
state_semantics_template:
  ontology_reference: "example:minimal_device"
  variables:
    - name: "temperature"
      physical_meaning: "设备核心温度"
      unit: "celsius"
      range_min: -20.0
      range_max: 200.0
      observability: "observable"
      controllability: "partially_controllable"
      measurement_source: "thermocouple_internal"
      required: true

    - name: "pressure"
      physical_meaning: "内部压力"
      unit: "bar"
      range_min: 0.0
      range_max: 50.0
      observability: "observable"
      controllability: "controllable"
      measurement_source: "pressure_gauge_1"
      required: true

    - name: "operating_mode"
      physical_meaning: "设备运行模式"
      unit: "enum"
      range_min: 0
      range_max: 0
      observability: "observable"
      controllability: "controllable"
      required: true

    - name: "vibration_freq"
      physical_meaning: "振动主频率"
      unit: "Hz"
      range_min: 0.0
      range_max: 5000.0
      observability: "observable"
      controllability: "uncontrollable"
      measurement_source: "accelerometer_1"
      required: false

    - name: "output_quality"
      physical_meaning: "产出质量指标"
      unit: "percentage"
      range_min: 0.0
      range_max: 100.0
      observability: "observable"
      controllability: "partially_controllable"
      required: true

# ── 约束卡片 ──
constraint_cards:
  knowledge_base_reference: "example:minimal_device:constraints"

  absolute:
    # 安全关键约束：温度上限
    - constraint_id: "temp_safety_limit"
      scenario_criticality: "safety_critical"
      domain_of_validity:
        conditions:
          - type: "state_range"
            variable: "temperature"
            min: -20.0
            max: 200.0
            inclusive: true
          - type: "sensor_status"
            sensor_id: "thermocouple_internal"
            required_status: "active"
        match_mode: "all"
      validation:
        method: "range_check"
        config:
          variable: "temperature"
          max: 180.0
          inclusive: true
      tolerance:
        absolute: 2.0
      violation_priority: 1

    # 安全关键约束：压力上限
    - constraint_id: "pressure_safety_limit"
      scenario_criticality: "safety_critical"
      domain_of_validity:
        conditions:
          - type: "state_range"
            variable: "pressure"
            min: 0.0
            max: 50.0
            inclusive: true
        match_mode: "all"
      validation:
        method: "range_check"
        config:
          variable: "pressure"
          max: 45.0
          inclusive: true
      tolerance:
        absolute: 1.0
      violation_priority: 1

    # 身份关键约束：振动频率应在物理合理范围
    - constraint_id: "vibration_physical_range"
      scenario_criticality: "identity_critical"
      domain_of_validity:
        conditions:
          - type: "state_enum"
            variable: "operating_mode"
            values: ["normal", "startup"]
          - type: "identity_confidence"
            min_confidence: 0.7
        match_mode: "all"
      validation:
        method: "range_check"
        config:
          variable: "vibration_freq"
          min: 10.0
          max: 3000.0
          inclusive: true
      tolerance:
        absolute: 50.0
      violation_priority: 2

    # 操作约束：温度-压力耦合范围
    - constraint_id: "temp_pressure_coupling"
      scenario_criticality: "operational"
      domain_of_validity:
        conditions:
          - type: "composite"
            operator: "and"
            sub_conditions:
              - type: "state_range"
                variable: "temperature"
                min: 50.0
                max: 180.0
                inclusive: true
              - type: "state_range"
                variable: "pressure"
                min: 5.0
                max: 45.0
                inclusive: true
        match_mode: "all"
      validation:
        method: "range_check"
        config:
          variable: "pressure"
          max: 40.0
          inclusive: true
      tolerance:
        percentage: 5.0
      violation_priority: 3

  soft:
    - constraint_id: "output_quality_target"
      weight: 0.8
      scenario_criticality: "operational"
      domain_of_validity:
        conditions:
          - type: "state_enum"
            variable: "operating_mode"
            values: ["normal"]
        match_mode: "all"
      validation:
        method: "threshold_exceeded"
        config:
          variable: "output_quality"
          min: 85.0

  learnable: []

# ── 安全回落策略 ──
safe_fallback:
  policy_id: "minimal_safe_shutdown"
  domain_of_validity:
    conditions: []
    match_mode: "all"
  verified_initial_set:
    - temperature: 25.0
      pressure: 1.0
      operating_mode: "shutdown"
  invariant_safe_set:
    - temperature: [0.0, 30.0]
      pressure: [0.0, 2.0]
  robustness_margin: 0.15
  target_state:
    state_description: "安全停机：温度降至 30°C 以下，压力降至 2 bar 以下"
    state_parameters:
      temperature: 25.0
      pressure: 1.0
      operating_mode: "shutdown"
  trajectory_constraints:
    max_rate:
      temperature: 10.0  # °C/s
      pressure: 5.0      # bar/s
    forbidden_zones:
      - temperature: [150, 200]
        pressure: [30, 50]
  max_duration: "PT5M"
  unavailable_action: "safe_shutdown"
  post_fallback_action: "hold"
  verification_record:
    verified_in_simulation: false
    verified_scenarios: []
    last_verification_date: "2026-01-01T00:00:00Z"

# ── 行动模板 ──
action_templates:
  knowledge_base_reference: "example:minimal_device:actions"

  immediate_action_types:
    - action_type_id: "observe_status"
      description_template: "观测当前设备状态"
      applicable_when: []
      monitoring_requirements:
        - "thermocouple_internal"
        - "pressure_gauge_1"
      fallback_if_fails: "hold"

    - action_type_id: "adjust_pressure"
      description_template: "微调内部压力（±2 bar 范围内）"
      applicable_when:
        - "operating_mode == 'normal'"
        - "fallback_available == true"
      monitoring_requirements:
        - "pressure_gauge_1"
      fallback_if_fails: "safe_shutdown"

  conditional_action_types:
    - action_type_id: "calibrate_sensors"
      description_template: "重新校准传感器"
      typical_prerequisites:
        - "operating_mode == 'shutdown'"
        - "all_sensors_active == true"
      risk_profile:
        risk_level: "low"
        reversible: true

  forbidden_action_types:
    - action_type_id: "override_safety_limits"
      description_template: "覆盖安全限制"
      typical_prohibition_reasons:
        - "safety_critical 约束不可覆盖"
    - action_type_id: "force_full_power"
      description_template: "强制满功率运行"
      typical_prohibition_reasons:
        - "需要 Core 资格验证"

# ── 人类角色 ──
human_roles:
  - role_id: "operator"
    role_name: "设备操作员"
    authorized_action_types: ["observe_status", "adjust_pressure"]
    exception_request_authority:
      can_request_review: true
      can_request_recertification: false
      can_request_constraint_revision: false
      can_initiate_human_takeover: true
      can_initiate_safe_shutdown: true
    approval_required_for: []

  - role_id: "supervisor"
    role_name: "值班主管"
    authorized_action_types: ["observe_status", "adjust_pressure", "calibrate_sensors"]
    exception_request_authority:
      can_request_review: true
      can_request_recertification: true
      can_request_constraint_revision: true
      can_initiate_human_takeover: true
      can_initiate_safe_shutdown: true
    approval_required_for: ["calibrate_sensors"]

# ── 验证集引用 ──
validation_sets:
  public_eval_set_reference: "example:minimal_device:public_eval"
  audit_benchmark_reference: "example:minimal_device:audit_benchmark"
  production_acceptance_reference: "example:minimal_device:production_acceptance"

# ── 身份监控配置 ──
identity_monitor_config:
  identity_check_interval: 1.0
  drift_tolerance: 0.05
  drift_trend_window: 100
  drift_trend_threshold: 0.02
  identity_uncertain_timeout: 30.0

# ── 元信息 ──
created_at: "2026-05-07T00:00:00Z"
last_modified_at: "2026-05-07T00:00:00Z"
certified_by: "initial_design"
certification_date: "2026-05-07T00:00:00Z"
applicability_scope: "演示用最小设备监控场景"
```

- [ ] **Step 3: 验证 YAML 语法正确**

```bash
python -c "import yaml; data = yaml.safe_load(open('configs/examples/minimal-domain-pack.yaml')); print('domain_id:', data['domain_id']); print('variables:', len(data['state_semantics_template']['variables'])); print('absolute constraints:', len(data['constraint_cards']['absolute'])); print('OK')"
```
Expected: `domain_id: example.minimal_device_monitor` / `variables: 5` / `absolute constraints: 4` / `OK`

- [ ] **Step 4: Commit**

```bash
git add configs/examples/minimal-domain-pack.yaml
git commit -m "feat(M0): add first complete DomainPack YAML with 5 state variables, 4 absolute constraints, 1 soft constraint, safety fallback, action templates, and human roles"
```

---

## Task 2: DomainPack 验证脚本

**Files:**
- Create: `scripts/validate_domainpack.py`

**Purpose:** 独立验证脚本，检查 DomainPack YAML 是否符合刚性-关键性兼容规则、引用完整性、必填字段。这是 M0-C2 检查点的自动化实现。

**Milestone M0-C2 对应:** 约束刚性-关键性兼容检查，零违规。

- [ ] **Step 1: 编写验证脚本**

```python
#!/usr/bin/env python3
"""validate_domainpack.py — DomainPack 加载时验证脚本.

Checks:
1. Rigidity-criticality compatibility (safety_critical must be absolute)
2. Reference integrity (constraint cards reference defined state variables)
3. Required fields (safe_fallback, human_roles, action_templates)
4. domain_of_validity references defined state variables

Usage:
    python scripts/validate_domainpack.py configs/examples/minimal-domain-pack.yaml
    python scripts/validate_domainpack.py configs/examples/*.yaml
"""
import sys
from pathlib import Path

import yaml


class ValidationError:
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"[{self.path}] {self.message}"


def validate_domainpack(filepath: Path) -> list[ValidationError]:
    """Validate a single DomainPack YAML file. Returns list of errors."""
    errors: list[ValidationError] = []

    try:
        data = yaml.safe_load(filepath.read_text())
    except yaml.YAMLError as e:
        return [ValidationError(str(filepath), f"YAML parse error: {e}")]

    if not isinstance(data, dict):
        return [ValidationError(str(filepath), "Top-level must be a mapping")]

    prefix = filepath.name

    # ── 1. Required top-level fields ──
    required_fields = [
        "domain_id", "domain_name", "domain_version",
        "state_semantics_template", "constraint_cards",
        "safe_fallback", "action_templates", "human_roles",
    ]
    for field in required_fields:
        if field not in data:
            errors.append(ValidationError(prefix, f"Missing required field: {field}"))

    if errors:
        return errors  # stop here if basic structure is broken

    # ── 2. Collect defined state variable names ──
    defined_vars = set()
    for var in data.get("state_semantics_template", {}).get("variables", []):
        if "name" in var:
            defined_vars.add(var["name"])

    # ── 3. Rigidity-criticality compatibility check ──
    constraint_cards = data.get("constraint_cards", {})

    # Check absolute constraints
    for i, card in enumerate(constraint_cards.get("absolute", [])):
        cid = card.get("constraint_id", f"absolute[{i}]")
        criticality = card.get("scenario_criticality", "")

        # safety_critical in absolute section is OK (absolute rigidity)
        # identity_critical in absolute section is OK
        # But verify it's not accidentally placed here with wrong criticality
        if criticality not in ("safety_critical", "identity_critical", "operational", "informational"):
            errors.append(ValidationError(
                f"{prefix}:constraint_cards.absolute.{cid}",
                f"Invalid scenario_criticality: {criticality}",
            ))

    # Check soft constraints — must NOT be safety_critical or identity_critical
    for i, card in enumerate(constraint_cards.get("soft", [])):
        cid = card.get("constraint_id", f"soft[{i}]")
        criticality = card.get("scenario_criticality", "")
        if criticality in ("safety_critical",):
            errors.append(ValidationError(
                f"{prefix}:constraint_cards.soft.{cid}",
                f"Rigidity-criticality violation: soft constraint has {criticality} criticality. "
                f"safety_critical constraints must be absolute.",
            ))

    # Check learnable constraints — must NOT be safety_critical without audit
    for i, card in enumerate(constraint_cards.get("learnable", [])):
        cid = card.get("constraint_id", f"learnable[{i}]")
        criticality = card.get("scenario_criticality", "")
        if criticality == "safety_critical":
            errors.append(ValidationError(
                f"{prefix}:constraint_cards.learnable.{cid}",
                f"Rigidity-criticality violation: learnable constraint has safety_critical criticality. "
                f"safety_critical constraints must be absolute.",
            ))
        if criticality == "identity_critical":
            if not card.get("audit_config"):
                errors.append(ValidationError(
                    f"{prefix}:constraint_cards.learnable.{cid}",
                    f"identity_critical + learnable requires audit_config",
                ))

    # ── 4. Reference integrity: domain_of_validity references defined variables ──
    all_cards = (
        constraint_cards.get("absolute", [])
        + constraint_cards.get("soft", [])
        + constraint_cards.get("learnable", [])
    )
    for card in all_cards:
        cid = card.get("constraint_id", "unknown")
        dov = card.get("domain_of_validity", {})
        for cond in dov.get("conditions", []):
            cond_type = cond.get("type", "")
            if cond_type in ("state_range", "state_enum"):
                var_name = cond.get("variable", "")
                if var_name and var_name not in defined_vars:
                    errors.append(ValidationError(
                        f"{prefix}:constraint_cards.{cid}.domain_of_validity",
                        f"References undefined state variable: {var_name}",
                    ))

        # Also check validation config references
        validation = card.get("validation", {})
        config = validation.get("config", {})
        var_name = config.get("variable", "")
        if var_name and var_name not in defined_vars:
            errors.append(ValidationError(
                f"{prefix}:constraint_cards.{cid}.validation",
                f"References undefined state variable: {var_name}",
            ))

    # ── 5. Safe fallback must exist and have target_state ──
    fallback = data.get("safe_fallback", {})
    if not fallback.get("target_state"):
        errors.append(ValidationError(
            f"{prefix}:safe_fallback",
            "Missing target_state in safe_fallback",
        ))

    # ── 6. Human roles must have role_id ──
    for i, role in enumerate(data.get("human_roles", [])):
        if not role.get("role_id"):
            errors.append(ValidationError(
                f"{prefix}:human_roles[{i}]",
                "Missing role_id",
            ))

    # ── 7. Action templates reference check ──
    for group in ("immediate_action_types", "conditional_action_types", "forbidden_action_types"):
        for i, action in enumerate(data.get("action_templates", {}).get(group, [])):
            if not action.get("action_type_id"):
                errors.append(ValidationError(
                    f"{prefix}:action_templates.{group}[{i}]",
                    "Missing action_type_id",
                ))

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_domainpack.py <file.yaml> [file2.yaml ...]")
        sys.exit(1)

    all_errors: list[ValidationError] = []
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"ERROR: {path_str} not found")
            sys.exit(1)
        errors = validate_domainpack(path)
        all_errors.extend(errors)

    if all_errors:
        print(f"VALIDATION FAILED: {len(all_errors)} error(s)")
        for err in all_errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print(f"VALIDATION PASSED: {len(sys.argv) - 1} file(s)")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 对合规 DomainPack 运行验证**

```bash
python scripts/validate_domainpack.py configs/examples/minimal-domain-pack.yaml
```
Expected: `VALIDATION PASSED: 1 file(s)`

- [ ] **Step 3: Commit**

```bash
git add scripts/validate_domainpack.py
git commit -m "feat(M0): add DomainPack validation script (rigidity-criticality, reference integrity, required fields)"
```

---

## Task 3: 验证脚本的测试 — 确保违规场景被正确检测

**Files:**
- Create: `tests/unit/test_domainpack_validation.py`
- Create: `configs/examples/invalid-soft-safety.yaml` (测试用违规配置)
- Create: `configs/examples/invalid-missing-fallback.yaml` (测试用违规配置)
- Create: `configs/examples/invalid-undefined-variable.yaml` (测试用违规配置)

**Purpose:** 确保验证脚本能正确拒绝各类违规 DomainPack。这是 M0-C2 检查点的质量保障。

- [ ] **Step 1: 创建测试用违规配置文件**

```yaml
# configs/examples/invalid-soft-safety.yaml
# 故意违反：safety_critical 约束放在 soft 段
domain_id: "test.invalid_soft_safety"
domain_name: "违规测试：soft+criticality"
domain_version: "0.0.1"

state_semantics_template:
  ontology_reference: "test"
  variables:
    - name: "temp"
      physical_meaning: "温度"
      unit: "C"
      range_min: 0
      range_max: 100
      observability: "observable"
      controllability: "controllable"
      required: true

constraint_cards:
  knowledge_base_reference: "test"
  absolute: []
  soft:
    - constraint_id: "bad_soft_safety"
      weight: 0.5
      scenario_criticality: "safety_critical"  # 违规！soft 不能是 safety_critical
      validation:
        method: "range_check"
        config:
          variable: "temp"
          max: 80
  learnable: []

safe_fallback:
  policy_id: "test"
  domain_of_validity: {conditions: [], match_mode: "all"}
  target_state: {state_description: "none", state_parameters: {}}
  trajectory_constraints: {max_rate: {}, forbidden_zones: []}
  max_duration: "PT0S"
  unavailable_action: "freeze"
  post_fallback_action: "hold"
  verification_record: {verified_in_simulation: false, verified_scenarios: [], last_verification_date: "2026-01-01T00:00:00Z"}

action_templates:
  knowledge_base_reference: "test"
  immediate_action_types: []
  conditional_action_types: []
  forbidden_action_types: []

human_roles: []
```

```yaml
# configs/examples/invalid-missing-fallback.yaml
# 故意违反：缺少 safe_fallback.target_state
domain_id: "test.invalid_missing_fallback"
domain_name: "违规测试：缺少回落目标"
domain_version: "0.0.1"

state_semantics_template:
  ontology_reference: "test"
  variables: []

constraint_cards:
  knowledge_base_reference: "test"
  absolute: []
  soft: []
  learnable: []

safe_fallback:
  policy_id: "test"
  domain_of_validity: {conditions: [], match_mode: "all"}
  # 故意缺少 target_state
  trajectory_constraints: {max_rate: {}, forbidden_zones: []}
  max_duration: "PT0S"
  unavailable_action: "freeze"
  post_fallback_action: "hold"
  verification_record: {verified_in_simulation: false, verified_scenarios: [], last_verification_date: "2026-01-01T00:00:00Z"}

action_templates:
  knowledge_base_reference: "test"
  immediate_action_types: []
  conditional_action_types: []
  forbidden_action_types: []

human_roles: []
```

```yaml
# configs/examples/invalid-undefined-variable.yaml
# 故意违反：约束引用了未定义的状态变量
domain_id: "test.invalid_undefined_var"
domain_name: "违规测试：引用未定义变量"
domain_version: "0.0.1"

state_semantics_template:
  ontology_reference: "test"
  variables:
    - name: "temp"
      physical_meaning: "温度"
      unit: "C"
      range_min: 0
      range_max: 100
      observability: "observable"
      controllability: "controllable"
      required: true

constraint_cards:
  knowledge_base_reference: "test"
  absolute:
    - constraint_id: "bad_ref"
      scenario_criticality: "operational"
      domain_of_validity:
        conditions:
          - type: "state_range"
            variable: "nonexistent_var"  # 违规！未定义
            min: 0
            max: 100
            inclusive: true
        match_mode: "all"
      validation:
        method: "range_check"
        config:
          variable: "also_nonexistent"  # 违规！未定义
          max: 50
  soft: []
  learnable: []

safe_fallback:
  policy_id: "test"
  domain_of_validity: {conditions: [], match_mode: "all"}
  target_state: {state_description: "none", state_parameters: {}}
  trajectory_constraints: {max_rate: {}, forbidden_zones: []}
  max_duration: "PT0S"
  unavailable_action: "freeze"
  post_fallback_action: "hold"
  verification_record: {verified_in_simulation: false, verified_scenarios: [], last_verification_date: "2026-01-01T00:00:00Z"}

action_templates:
  knowledge_base_reference: "test"
  immediate_action_types: []
  conditional_action_types: []
  forbidden_action_types: []

human_roles: []
```

- [ ] **Step 2: 编写验证测试**

```python
# tests/unit/test_domainpack_validation.py
"""Test that validate_domainpack.py correctly accepts valid configs
and rejects invalid ones for specific reasons."""
from pathlib import Path

import pytest

# Import the validation function directly
from scripts.validate_domainpack import validate_domainpack


CONFIGS = Path("configs/examples")


class TestValidDomainPack:
    def test_minimal_domain_pack_passes(self):
        errors = validate_domainpack(CONFIGS / "minimal-domain-pack.yaml")
        assert errors == [], f"Unexpected errors: {errors}"


class TestRigidityCriticalityViolation:
    def test_soft_with_safety_critical_rejected(self):
        errors = validate_domainpack(CONFIGS / "invalid-soft-safety.yaml")
        assert len(errors) > 0
        error_messages = [e.message for e in errors]
        assert any("safety_critical" in m and "soft" in m for m in error_messages), (
            f"Expected rigidity-criticality violation, got: {error_messages}"
        )


class TestMissingFallback:
    def test_missing_target_state_rejected(self):
        errors = validate_domainpack(CONFIGS / "invalid-missing-fallback.yaml")
        assert len(errors) > 0
        error_messages = [e.message for e in errors]
        assert any("target_state" in m for m in error_messages), (
            f"Expected missing target_state error, got: {error_messages}"
        )


class TestUndefinedVariableReference:
    def test_undefined_variable_in_domain_of_validity_rejected(self):
        errors = validate_domainpack(CONFIGS / "invalid-undefined-variable.yaml")
        assert len(errors) > 0
        error_messages = [e.message for e in errors]
        # Should catch both: domain_of_validity ref and validation config ref
        undefined_refs = [m for m in error_messages if "undefined state variable" in m]
        assert len(undefined_refs) >= 1, (
            f"Expected undefined variable references, got: {error_messages}"
        )
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/unit/test_domainpack_validation.py -v
```
Expected: 全部 PASSED

- [ ] **Step 4: 确认违规文件被正确拒绝**

```bash
python scripts/validate_domainpack.py configs/examples/invalid-soft-safety.yaml; echo "exit: $?"
python scripts/validate_domainpack.py configs/examples/invalid-missing-fallback.yaml; echo "exit: $?"
python scripts/validate_domainpack.py configs/examples/invalid-undefined-variable.yaml; echo "exit: $?"
```
Expected: 每个都输出 `VALIDATION FAILED` 且 exit code = 1

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_domainpack_validation.py configs/examples/invalid-*.yaml
git commit -m "test(M0): add validation tests for rigidity-criticality violations, missing fallback, and undefined variable references"
```

---

## M0 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M0-C1: 配置完整性** | `python scripts/validate_domainpack.py configs/examples/minimal-domain-pack.yaml` | `VALIDATION PASSED` |
| **M0-C2: 刚性-关键性兼容** | `pytest tests/unit/test_domainpack_validation.py::TestRigidityCriticalityViolation -v` | PASSED |
| **引用完整性** | `pytest tests/unit/test_domainpack_validation.py::TestUndefinedVariableReference -v` | PASSED |
| **必填字段检查** | `pytest tests/unit/test_domainpack_validation.py::TestMissingFallback -v` | PASSED |

---

## M0 额外交付物说明

里程碑 M0 定义了三个交付物 D1/D2/D3：
- **D1:** `configs/examples/minimal-domain-pack.yaml` — 已在 Task 1 完成
- **D2:** DomainPack 知识库映射文档 — 记录每个 `knowledge_base_reference` 对应的实际外部知识库位置和访问方式。由于示例 DomainPack 使用虚构引用（`example:minimal_device:*`），此文档在 M6 创建真实场景 DomainPack 时一并完成。
- **D3:** DomainPack 创建流程文档 — 记录领域专家创建新 DomainPack 的步骤指南。在 M7 Task 9（开发者文档）中作为"DomainPack 创建指南"一并完成。

M0-C3（安全回落模拟验证）的 `verified_in_simulation: false` 字段表示回落策略尚未通过仿真验证。M7 安全渗透测试阶段可补充此项验证。

---

## M0 → M1 交接条件

M0 完成后，以下产物就绪，可以开始 M1 开发：

1. **`configs/examples/minimal-domain-pack.yaml`** — 包含 5 个状态变量、4 个绝对约束（含 domain_of_validity 的 state_range/state_enum/sensor_status/composite/identity_confidence 五种条件）、1 个软约束、完整安全回落、行动模板、人类角色
2. **`scripts/validate_domainpack.py`** — 可独立运行的验证脚本
3. **测试套件** — 4 个正向/负向测试确保验证脚本可靠
4. **`src/polytwin/jelly/`** — Jelly MCP Client 骨架（mock 模式可用，详见下方 Jelly 集成任务）

---

## Jelly 集成任务 (Spec v2.1.0 §3.7)

> **依赖**: Jelly 契约 `2026-05-08-jelly-twin-provider-contract.md` (已生效)
> **详细设计**: `2026-05-08-jelly-mcp-client-integration.md`

### Task 4: JellyConfig + Client 骨架 + MockProvider

**Files:**
- Create: `src/polytwin/jelly/__init__.py`
- Create: `src/polytwin/jelly/config.py`
- Create: `src/polytwin/jelly/client.py`
- Create: `src/polytwin/jelly/mock.py`
- Create: `src/polytwin/jelly/exceptions.py`
- Create: `src/polytwin/jelly/types.py`
- Test: `tests/unit/test_jelly_client.py`

**Purpose:** 建立 Jelly MCP 集成层骨架。所有方法默认 mock 模式（从本地 YAML 读取），Jelly 不可用时 PT 仍可完整运行。

- [ ] **Step 1: 创建 jelly 模块目录**

```bash
mkdir -p src/polytwin/jelly tests/fixtures/jelly_mocks
```

- [ ] **Step 2: 实现 JellyConfig 数据模型**

```python
# src/polytwin/jelly/config.py
from pydantic import BaseModel

class JellyConfig(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:9091"
    timeout_seconds: float = 5.0
    auth_token: str | None = None
    max_retries: int = 3
    retry_backoff: list[float] = [1.0, 2.0, 4.0]
    mock_mode: bool = True
    mock_data_dir: str = "configs/examples"
    enable_secondary_filter: bool = True
```

- [ ] **Step 3: 实现 exceptions.py + types.py 骨架**

exceptions.py 定义 JellyError 层次（ConnectionError, DomainPackNotFoundError, PermissionDeniedError, DataAlignmentError, ServiceUnavailableError）。types.py 定义 Pydantic 返回类型（JellyDomainPack, JellyValidationSet 等），详见 `2026-05-08-jelly-mcp-client-integration.md §4.2`。

- [ ] **Step 4: 实现 MockProvider**

```python
# src/polytwin/jelly/mock.py
from pathlib import Path
import yaml

class MockProvider:
    """从本地 YAML 文件提供 mock 数据。Jelly 不可用时的回退方案。"""
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def get_domain_pack(self, domain_id: str) -> dict | None:
        for f in self.data_dir.glob("*.yaml"):
            data = yaml.safe_load(f.read_text())
            if data.get("domain_id") == domain_id:
                return data
        return None
```

- [ ] **Step 5: 实现 JellyClient 骨架**

```python
# src/polytwin/jelly/client.py
class JellyClient:
    def __init__(self, config: JellyConfig):
        self.config = config
        self._mock = MockProvider(config.mock_data_dir) if config.mock_mode else None

    def get_domain_pack(self, domain_id: str, caller: str = "core"):
        if self.config.mock_mode:
            return self._mock.get_domain_pack(domain_id)
        return None  # 真实 MCP 调用在 M1 实现

    def health_check(self) -> bool:
        return True if self.config.mock_mode else False

    def close(self) -> None: ...
```

- [ ] **Step 6: 编写 mock 模式测试并验证**

```bash
pytest tests/unit/test_jelly_client.py -v
```
Expected: 全部 PASSED（mock 返回本地 YAML 数据）

- [ ] **Step 7: Commit**

```bash
git add src/polytwin/jelly/ tests/unit/test_jelly_client.py
git commit -m "feat(M0): add Jelly MCP client skeleton with mock provider and config model"
```
