# M2: Core 约束治理引擎最小子集

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Core 的完整约束治理能力：四态约束验证（含 domain_of_validity 求值）、HardGate 六项检验、安全回落执行器、检疫隔离区、证据准入、IdentityMonitor、预筛函数库导出。M2 完成后，决策闭环的 Core 侧全通。

**Architecture:** Core 分为三层：runtime 层（engine + hardgate + identity_monitor，Lab 不可见）、certification 层（隐藏验证集，runtime 和 Lab 都不可见）、入口层（quarantine，Lab 提交唯一入口）。预筛函数库从 Core 导出，Lab 可在沙箱内调用但不作为权威结论。

**Tech Stack:** Python 3.11+, Pydantic v2, asyncio

**Spec reference:** §3.2 Core, §3.3 IdentityMonitor, §3.4 Lab 约束感知（预筛函数库）

**Depends on:** M1 (TwinObject 完整数据模型 + 视图投影)

**Quality gate (M2-C1 ~ C5):**
- C1: 约束验证正确性 — 已知应通过/失败的输入，逐一验证
- C2: safety_critical 优先中断 — 同时违反 safety + operational 时，验证在 safety 处终止
- C3: 安全回落仿真验证（M5 时做端到端，M2 先做逻辑验证）
- C4: 证据准入 item 级独立性 — 混合批次中有效/无效独立判决
- C5: 反馈脱敏 — Lab 无法区分"因隐藏集被拒"和"因公开集不足被拒"

---

## File Structure

```
src/polytwin/core/
├── __init__.py
├── types.py               # Task 1: Core-specific types
├── rules/
│   ├── __init__.py
│   ├── evaluator.py       # Task 2: 四态判决 + domain_of_validity
│   ├── combinator.py      # Task 3: AND/OR/weighted/priority
│   └── registry.py        # Task 4: 内置验证函数
├── engine.py              # Task 5: ConstraintEngine 主循环
├── hardgate.py            # Task 6: HardGate 六项检验
├── fallback.py            # Task 7: SafetyFallback
├── quarantine.py          # Task 8: SubmissionQuarantine
├── evidence.py            # Task 9: EvidenceAdmission
├── identity_monitor.py    # Task 10: IdentityMonitor
├── certification.py       # Task 11: ModelCertification
├── prescreen.py           # Task 12: PrescreenLibrary
└── audit.py               # Task 13: AuditLogWriter
tests/unit/
├── test_core_types.py
├── test_evaluator.py
├── test_combinator.py
├── test_registry.py
├── test_engine.py
├── test_hardgate.py
├── test_fallback.py
├── test_quarantine.py
├── test_evidence.py
├── test_identity_monitor.py
├── test_certification.py
├── test_prescreen.py
└── test_audit.py
```

---

## Task 1: Core 类型定义

**Files:** Create `src/polytwin/core/types.py`, Test `tests/unit/test_core_types.py`

**类型列表：**

| 类型 | 用途 | 关键字段 |
|------|------|----------|
| `ConstraintStatus` | 四态判决 | passed/uncertain/failed/not_applicable（已在 tom/types.py，此处 re-export） |
| `SingleConstraintResult` | 单约束求值结果 | constraint_id, status, actual_values, threshold, rigidity, criticality |
| `ValidationResult` | 综合验证结果 | passed, individual_results, combination_logic, requires_human_review |
| `HardGateCheckResult` | 单项检验结果 | check_name, passed, details |
| `HardGateResult` | HardGate 综合结果 | granted_links, degraded_links, denied_links |
| `CertificationResult` | 模型认证结果 | granted, score, certificate, gaps |
| `QuarantineResult` | 检疫结果 | rejected, reason, detail |
| `EvidenceAdmissionResult` | 证据准入结果 | item_id, admitted, reason |
| `IdentityCheckResult` | 身份检查结果 | identity_status, drift_values, timestamp |
| `DriftSample` | 漂移采样点 | invariant_name, drift, timestamp |
| `FallbackResult` | 安全回落结果 | strategy_used, object_id, violated_constraint |
| `LabSubmission` | Lab 提交包（从 M3 导入） | submission_id, items: list[CandidateModelPackage], strategy_manifest, is_prescreen: bool=True |
| `PrescreenResult` | 预筛结果 | status, is_authoritative=False（永远） |

- [ ] **Step 1-5: TDD — 定义所有 Core 类型**

---

## Task 2: 约束求值器 — 四态判决 + domain_of_validity

**Files:** `src/polytwin/core/rules/evaluator.py`, Test `tests/unit/test_evaluator.py`

**这是 M2 的核心 — 约束治理的地基。**

**domain_of_validity 求值逻辑（5 种条件类型）：**

```python
def evaluate_domain_of_validity(
    conditions: list[dict],
    match_mode: str,
    state_values: dict[str, float],
    identity_confidence: float,
    sensor_status: dict[str, str],
) -> bool:
    """
    返回 True = 约束适用, False = not_applicable
    安全默认值：未定义 domain_of_validity → 始终适用（宽松）
    状态变量缺失 → 视为适用（保守：宁可多检查）
    """
    if not conditions:
        return True  # 宽松默认

    results = []
    for cond in conditions:
        ctype = cond["type"]
        if ctype == "state_range":
            val = state_values.get(cond["variable"])
            if val is None:
                results.append(True)  # 保守：变量缺失视为适用
                continue
            in_range = cond.get("min", float("-inf")) <= val <= cond.get("max", float("inf"))
            if not cond.get("inclusive", True):
                in_range = cond.get("min", float("-inf")) < val < cond.get("max", float("inf"))
            results.append(in_range)

        elif ctype == "state_enum":
            # state_enum 用于字符串枚举变量，此处简化处理
            results.append(True)

        elif ctype == "sensor_status":
            status = sensor_status.get(cond.get("sensor_id", ""), "unknown")
            if status == "unknown":
                results.append(True)  # 保守：未知视为适用
                continue
            results.append(status == cond.get("required_status", "active"))

        elif ctype == "composite":
            sub_results = evaluate_domain_of_validity(
                cond.get("sub_conditions", []),
                cond.get("operator", "and"),
                state_values, identity_confidence, sensor_status,
            )
            # 递归调用需要返回 bool，此处简化
            results.append(sub_results if isinstance(sub_results, bool) else all(sub_results))

        elif ctype == "identity_confidence":
            results.append(identity_confidence >= cond.get("min_confidence", 0.0))

    if match_mode == "any":
        return any(results)
    return all(results)  # default "all"
```

**求值器完整逻辑：**

```
输入: TwinObject (通过 CoreRuntimeView), ConstraintCard
  1. 提取 state_values from view.state_semantics.current_values
  2. 提取 identity_confidence from view.identity_invariants.overall_confidence
  3. 调用 evaluate_domain_of_validity(card.domain_of_validity, ...)
     → False: 返回 SingleConstraintResult(status=NOT_APPLICABLE)
  4. 调用 validator(state_values, card.validation.config)
     → 返回验证结果
  5. 返回 SingleConstraintResult(status=验证结果, ...)
```

**测试用例（每条必须有）：**

| 测试名 | 条件 | 预期 status |
|--------|------|-------------|
| `temp_in_range_passes` | temp=150, 上限=180 | PASSED |
| `temp_exceeds_fails` | temp=190, 上限=180 | FAILED |
| `outside_domain_not_applicable` | temp=250, domain=[0,200] | NOT_APPLICABLE |
| `missing_variable_still_applicable` | 变量缺失 | 仍适用（保守） |
| `sensor_offline_still_applicable` | 传感器 offline | 仍适用（保守） |
| `sensor_active_passes` | 传感器 active | 正常求值 |
| `identity_low_not_applicable` | confidence=0.5, min=0.8 | NOT_APPLICABLE |
| `composite_and_all_match` | 两个子条件都满足 | 适用 |
| `composite_and_one_miss` | 一个子条件不满足 | NOT_APPLICABLE |
| `empty_domain_always_applicable` | 无 domain_of_validity | 适用 |

- [ ] **Step 1-5: TDD**

---

## Task 3: 约束组合逻辑

**Files:** `src/polytwin/core/rules/combinator.py`, Test `tests/unit/test_combinator.py`

**四种组合方式 + identity_critical 触发人工审核标记：**

| 组合 | 逻辑 | 测试用例 |
|------|------|----------|
| AND | 全通过才通过 | 3 pass → pass; 2 pass 1 fail → fail |
| OR | 任一通过即通过 | 1 pass 2 fail → pass |
| weighted | 加权分 ≥ threshold | weight 0.5 pass + 0.5 fail = 0.5, threshold 0.6 → fail |
| priority | 按 criticality 排序，第一个 fail 即停 | safety fail → 整体 fail |
| human_review | identity_critical fail → requires_human_review=True | identity fail → 标记 |

- [ ] **Step 1-5: TDD**

---

## Task 4: 内置验证函数注册表

**Files:** `src/polytwin/core/rules/registry.py`, Test `tests/unit/test_registry.py`

**内置函数：**

| 函数 | 输入 | 逻辑 |
|------|------|------|
| `range_check` | variable, min/max, inclusive | current_value 在范围内 → PASSED |
| `threshold_exceeded` | variable, threshold | value > threshold → FAILED |
| `enum_membership` | variable, allowed_values | value in values → PASSED |
| `statistical_test` | variables, test_type, params | 简化版：均值/方差检查 |

- [ ] **Step 1-5: TDD**

---

## Task 5: ConstraintEngine 主循环

**Files:** `src/polytwin/core/engine.py`, Test `tests/unit/test_engine.py`

**M2-C2 验收关键测试：safety_critical 优先中断**

```python
# tests/unit/test_engine.py 关键测试
class TestSafetyCriticalInterrupt:
    def test_safety_violation_stops_further_evaluation(self):
        """M2-C2: 同时违反 safety_critical 和 operational 时，验证在 safety_critical 处终止。"""
        engine = ConstraintEngine(...)
        cards = [
            make_card("safety_temp", criticality="safety_critical", will_fail=True),
            make_card("oper_press", criticality="operational", will_fail=True),
            make_card("oper_quality", criticality="operational", will_pass=True),
        ]
        result = await engine.validate(obj, cards)
        # safety 违规 → 立即中断，只评估了 1 个约束
        assert len(result.evaluated_constraints) == 1
        assert result.safety_fallback_triggered is True
        # operational 约束没有被评估
```

**主循环伪代码：**

```
for card in constraint_cards:
    result = evaluator.evaluate(obj, card)
    if result.status == NOT_APPLICABLE:
        suspend(card) → 记录到 suspended_constraints
        continue
    if result.status == FAILED and card.criticality == SAFETY_CRITICAL:
        trigger_safety_fallback(obj, card) → 中断
        break
    results.append(result)
combined = combinator.combine(results)
audit.write(...)
return combined
```

- [ ] **Step 1-5: TDD**

---

## Task 6: HardGate 六项检验

**Files:** `src/polytwin/core/hardgate.py`, Test `tests/unit/test_hardgate.py`

**六项检验及测试用例：**

| 检验项 | 测试用例 |
|--------|----------|
| 1. 状态语义兼容 | 变量缺失 → denied |
| 2. 约束适用域匹配 | 当前模式不在适用域 → degraded |
| 3. 所需观测齐备 | 传感器 offline → denied |
| 4. 任务类型允许 | autonomous_control 无安全证书 → denied |
| 5. 安全边界前置 | 不确定性传播后越界 → degraded |
| 6. 干预有效性 | production_control 链路 → 检查干预路径 |

**⚠️ 隔离规则：** `hardgate.py` 不得 import `certification.py`。CI 扫描强制执行。

- [ ] **Step 1-5: TDD**

---

## Task 7: SafetyFallback 安全回落

**Files:** `src/polytwin/core/fallback.py`, Test `tests/unit/test_fallback.py`

**四种策略：**

| 策略 | 测试 |
|------|------|
| safe_state | 执行 → TwinObject.state 更新为 target_state |
| shutdown | 执行 → lifecycle = "archived" |
| degraded_mode | 执行 → health = "degraded" |
| human_takeover | 执行 → 写入审计事件通知人类 |

**回落不可中断测试：** fallback 一旦触发，不能被取消。

- [ ] **Step 1-5: TDD**

---

## Task 8: SubmissionQuarantine 检疫隔离区

**Files:** `src/polytwin/core/quarantine.py`, Test `tests/unit/test_quarantine.py`

**检疫三步检查：**

| 检查 | 测试 |
|------|------|
| 格式完整性 | 缺失 lineage → rejected("format_integrity") |
| 资源异常 | 载荷 > 10MB → rejected("payload_too_large") |
| 敏感信息扫描 | 包含 "hidden_challenge_set" 字符串 → rejected("sensitive_info_detected") |

**通过后转交 certification。**

- [ ] **Step 1-5: TDD**

---

## Task 9: EvidenceAdmission 证据准入

**Files:** `src/polytwin/core/evidence.py`, Test `tests/unit/test_evidence.py`

**M2-C4 验收关键：item 级独立性**

```python
class TestItemLevelIndependence:
    def test_valid_and_invalid_items_independently_judged(self):
        """M2-C4: 混合批次中有效 item 被准入，无效 item 被拒绝，互不影响。"""
        admission = EvidenceAdmission(...)
        batch = [
            make_submission("valid-model", type="model", quality=0.95),
            make_submission("bad-hypothesis", type="constraint_hypothesis", invalid=True),
        ]
        results = await admission.admit_batch(batch)
        assert results[0].admitted is True
        assert results[1].admitted is False
```

**M2-C5 验收关键：反馈脱敏**

```python
class TestFeedbackDesensitization:
    def test_lab_cannot_distinguish_rejection_reason(self):
        """M2-C5: 两种拒绝原因返回相同格式的脱敏反馈。"""
        # 模型因隐藏集被拒
        hidden_reject = await admission.admit(model_fails_hidden_set)
        # 模型因公开集性能不足被拒
        public_reject = await admission.admit(model_fails_public_set)
        # Lab 收到的反馈格式相同，无法区分
        assert hidden_reject.feedback_format == public_reject.feedback_format
        assert "hidden" not in hidden_reject.feedback_to_lab
```

- [ ] **Step 1-5: TDD**

---

## Task 10: IdentityMonitor 身份连续性监控

**Files:** `src/polytwin/core/identity_monitor.py`, Test `tests/unit/test_identity_monitor.py`

**关键参数（来自 DomainPack 的 identity_monitor_config）：**

```python
@dataclass
class IdentityMonitorConfig:
    check_interval: float = 1.0
    drift_tolerance: float = 0.05
    drift_trend_window: int = 100
    drift_trend_threshold: float = 0.02
    uncertain_timeout: float = 30.0
```

**漂移计算：**

```
drift = |actual - expected| / |expected|   (expected ≠ 0)
```

**判定逻辑：**

| 条件 | identity_status |
|------|-----------------|
| 所有 drift < tolerance | confirmed |
| 任一 drift ≥ tolerance 但 < 2*tolerance | uncertain |
| 任一 drift ≥ 2*tolerance 或趋势持续上升超 trend_threshold | forked |

**测试用例：**

| 测试 | 输入 | 预期 |
|------|------|------|
| all_within_tolerance | 所有 drift=0.03, tolerance=0.05 | confirmed |
| one_exceeds_tolerance | 一个 drift=0.06, tolerance=0.05 | uncertain |
| double_exceeds | 一个 drift=0.12, tolerance=0.05 | forked |
| trend_rising | 100 样本持续上升, trend_threshold=0.02 | forked |
| uncertain_timeout | uncertain 持续 30s | 触发安全回落 |

- [ ] **Step 1-5: TDD**

---

## Task 11: ModelCertification 模型资格认证

**Files:** `src/polytwin/core/certification.py`, Test `tests/unit/test_certification.py`

**⚠️ 隔离规则：**
- `runtime.py` 和 `hardgate.py` 不得 import 此模块
- `lab/` 代码不得 import 此模块
- CI 扫描强制执行

**MVP 阶段：** hidden_challenge_set 为空，certify 基于公开评估集做简单评分。但接口已预留。

- [ ] **Step 1-5: TDD**

---

## Task 12: PrescreenLibrary 预筛函数库

**Files:** `src/polytwin/core/prescreen.py`, Test `tests/unit/test_prescreen.py`

**Spec §3.4: Core 导出无状态约束预筛函数集。**

```python
class PrescreenLibrary:
    """导出给 Lab 的无状态约束验证函数集。
    每个函数：(state_values, constraint_config) → PrescreenResult
    PrescreenResult.is_authoritative 永远为 False。
    """
    @staticmethod
    def prescreen_range_check(state_values: dict, config: dict) -> PrescreenResult:
        ...

    @staticmethod
    def prescreen_threshold(state_values: dict, config: dict) -> PrescreenResult:
        ...

    @staticmethod
    def get_available_functions() -> list[str]:
        """返回可用预筛函数名列表。"""
        return ["range_check", "threshold_exceeded", "enum_membership"]
```

**关键测试：**

| 测试 | 验证 |
|------|------|
| result.is_authoritative == False | 预筛结果永远不权威 |
| 逻辑与 Core evaluator 一致 | 同样的输入，同样的 passed/failed 判断 |
| 不含隐藏验证集逻辑 | 预筛函数不知道隐藏集的存在 |

- [ ] **Step 1-5: TDD**

---

## Task 13: AuditLogWriter

**Files:** `src/polytwin/core/audit.py`, Test `tests/unit/test_audit.py`

```python
class AuditLogWriter(Protocol):
    async def write(self, record: AuditRecord) -> None: ...

class PostgresAuditWriter:
    """写入 PostgreSQL 审计表。"""
    async def write(self, record: AuditRecord) -> None: ...

class InMemoryAuditWriter:
    """测试用。"""
    def __init__(self):
        self.records: list[AuditRecord] = []

    async def write(self, record: AuditRecord) -> None:
        self.records.append(record)
```

- [ ] **Step 1-5: TDD**

---

## M2 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M2-C1: 约束验证正确性** | `pytest tests/unit/test_evaluator.py tests/unit/test_registry.py -v` | 全部 PASSED |
| **M2-C2: safety_critical 优先中断** | `pytest tests/unit/test_engine.py::TestSafetyCriticalInterrupt -v` | 只评估 1 个约束即中断 |
| **M2-C3: 安全回落逻辑** | `pytest tests/unit/test_fallback.py -v` | 4 种策略正确执行 |
| **M2-C4: item 级独立性** | `pytest tests/unit/test_evidence.py::TestItemLevelIndependence -v` | 混合批次独立判决 |
| **M2-C5: 反馈脱敏** | `pytest tests/unit/test_evidence.py::TestFeedbackDesensitization -v` | 无法区分拒绝原因 |
| **模块隔离** | `python scripts/check_import_isolation.py` | 0 个违规 import |

---

## Jelly 集成任务 (Spec v2.1.0 §3.7)

> **详细设计**: `2026-05-08-jelly-mcp-client-integration.md §6.1`
> **Jelly Phase 依赖**: Phase 1 (Group 2: twin.get_validation_set, twin.query_validation_data)

### Jelly Task: Core 验证集从 Jelly 加载

**Files:**
- Modify: `src/polytwin/core/evidence.py` — 新增 Jelly 验证集获取路径
- Modify: `src/polytwin/core/certification.py` — HardGate 使用 Jelly production_acceptance_set
- Test: `tests/unit/test_jelly_validation.py`

**目的:** Core 的证据准入和模型认证可从 Jelly 获取验证数据集。

**集成方式:**

```python
class CoreEngine:
    def __init__(self, registry, jelly: JellyClient | None): ...

    def load_validation_sets(self, domain_id: str) -> None:
        """从 Jelly 加载验证数据集。
        Core 全权 caller → 可获取所有 set_type。
        - production_acceptance_set → HardGate 隐藏验证集
        - audit_benchmark → 审计对比
        - public_eval → Lab 可见的公开集
        """
        if self.jelly and self.jelly.health_check():
            pa = self.jelly.get_validation_set(domain_id, "production_acceptance", caller="core")
            ab = self.jelly.get_validation_set(domain_id, "audit_benchmark", caller="core")
```

**降级:** Jelly 不可用时使用 DomainPack 内嵌的 validation_sets 引用（本地数据）。

**二次视图过滤:** Core 使用 Jelly 数据前，view_filter.py 执行兜底过滤，确保不应有的字段被移除。
