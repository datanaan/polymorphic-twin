# M4: Bridge 决策接口层

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Bridge 的完整决策接口能力：从 TwinObject 的 BridgeDecisionView 构建四分类行动空间（immediate/conditional/forbidden/undetermined）、有效期管理（版本不匹配立即失效）、人类行动响应验证、审计输出（不自己持久化）。M4 完成后，决策闭环（§2.3）的 Bridge 侧全通。

**Architecture:** Bridge 是无状态层。它从 TwinObject 的 BridgeDecisionView 读取数据，结合 DomainPack 的行动模板和角色定义，构建行动空间。审计输出通过 AuditLogWriter Protocol 接口完成，Bridge 不持数据库连接。Bridge 宪法：不得输出"建议"，每次生成行动空间必须写入审计事件，permanently_forbidden 的行动只能发起审查流程不能绕过约束。

**Tech Stack:** Python 3.11+, Pydantic v2

**Spec reference:** §3.5 Bridge

**Depends on:** M1 (TOM + 视图投影), M2 (Core 验证结果)

**Quality gate (M4-C1 ~ C4):**
- C1: 行动空间分类正确性 — 不同场景快照下分类符合预期
- C2: 有效期管理 — TwinObject 版本变化 → BridgeOutput 立即失效
- C3: exception_request ≠ override — permanently_forbidden 行动不能绕过约束
- C4: 审计记录不可修改 — 修改/删除被拒绝

---

## File Structure

```
src/polytwin/bridge/
├── __init__.py
├── types.py              # Task 1: Bridge types (ActionOption, ForbiddenAction, BridgeOutput, Validity, etc.)
├── orchestrator.py       # Task 2: BridgeOrchestrator 行动编排
├── action_space.py       # Task 3: ActionSpaceBuilder 四分类构建
├── decision.py           # Task 4: BridgeDecisionRecord 生成
├── validity.py           # Task 5: 有效期管理
├── human_response.py     # Task 6: 人类行动响应验证
├── roles.py              # Task 7: 角色权限检查
├── audit_writer.py       # Task 8: AuditLogWriter Protocol
└── constitution.py       # Task 9: Bridge 宪法检查（无"建议"词，每次生成写入审计）
tests/unit/
├── test_bridge_types.py
├── test_orchestrator.py
├── test_action_space.py
├── test_decision.py
├── test_validity.py
├── test_human_response.py
├── test_roles.py
├── test_audit_writer.py
└── test_constitution.py
```

---

## Task 1: Bridge 类型定义

**Files:** `src/polytwin/bridge/types.py`, `tests/unit/test_bridge_types.py`

**类型列表：**

| 类型 | 用途 | 关键字段 |
|------|------|----------|
| `ActionOption` | 行动选项 | action_id, execution_mode, risk_level, risk_basis, unmet_prerequisites, lawful_unlock_path |
| `ForbiddenAction` | 禁止行动 | action_id, prohibition_reasons: list[str], lawful_unlock_conditions: list[str], permanently_forbidden: bool |
| `BridgeOutput` | 行动空间输出 | immediate_actions, conditional_actions, forbidden_actions, undetermined_actions, validity |
| `Validity` | 有效期 | generated_from_snapshot_id, valid_until, invalidation_triggers, consistency_binding |
| `BridgeDecisionRecord` | 决策记录 | action_space_id, selected_action_id, decided_by, reasoning, timestamp, audit_anchor |
| `HumanActionResponse` | 人类响应 | action_id, status (accepted/rejected_due_to_expiry/rejected_due_to_unauthorized/forwarded_to_core/requires_fresh) |
| `ConsistencyBinding` | 版本绑定 | twin_object_version, domain_pack_version |

- [ ] **Step 1-5: TDD**

---

## Task 2: 行动编排器

**Files:** `src/polytwin/bridge/orchestrator.py`, `tests/unit/test_orchestrator.py`

```python
class BridgeOrchestrator:
    def __init__(self, audit_writer: AuditLogWriter, role_manager: RoleManager):
        self._audit = audit_writer
        self._roles = role_manager

    async def build_action_space(
        self, obj: TwinObject, dp: DomainPack, caller: CallerIdentity
    ) -> BridgeOutput:
        view = obj.get_view(ViewType.BRIDGE_DECISION, caller)
        builder = ActionSpaceBuilder(view, dp)
        output = builder.build()
        # 每次生成必须写入审计（Bridge 宪法）
        await self._audit.write(AuditRecord(action="action_space_generated", ...))
        return output

    async def record_decision(
        self, output: BridgeOutput, selected_action: str, caller: CallerIdentity, reasoning: str | None
    ) -> None:
        # 不自己写库，通过 audit_writer
        record = BridgeDecisionRecord(...)
        await self._audit.write(record)
```

- [ ] **Step 1-5: TDD**

---

## Task 3: 行动空间四分类构建

**Files:** `src/polytwin/bridge/action_space.py`, `tests/unit/test_action_space.py`

**M4-C1 验收：不同场景下分类正确**

```python
class ActionSpaceBuilder:
    def build(self) -> BridgeOutput:
        immediate = []    # 所有前置条件满足，无安全风险
        conditional = []  # 有未满足前置条件
        forbidden = []    # 违反 safety/identity 约束
        undetermined = [] # 信息不足

        for template in self._view.action_templates:
            action = self._classify(template)
            ...

    def _classify(self, template) -> str:
        # 检查约束：safety_critical 违反 → forbidden
        for cp in self._view.constraint_summary:
            if cp.is_violated and cp.criticality == Criticality.SAFETY_CRITICAL:
                if template.action_type_id in cp.affected_actions:
                    return "forbidden"
        # 检查前置条件
        if not self._prerequisites_met(template):
            return "conditional"
        # 默认
        return "immediate"
```

**测试用例：**

| 场景 | 预期 |
|------|------|
| 正常状态，无约束违反 | 全部 immediate |
| safety_critical 违反 | 相关行动 → forbidden，含 prohibition_reason |
| identity_uncertain | 不可逆操作 → forbidden |
| 缺少前置条件 | conditional，含 unmet_prerequisites + lawful_unlock_path |
| 数据不足 | undetermined |

- [ ] **Step 1-5: TDD**

---

## Task 4: 决策记录

**Files:** `src/polytwin/bridge/decision.py`, `tests/unit/test_decision.py`

**M4-C4 验收：审计记录不可修改**

BridgeDecisionRecord 是 `frozen=True` 的 Pydantic 模型。测试：创建后修改字段 → ValidationError。

- [ ] **Step 1-5: TDD**

---

## Task 5: 有效期管理

**Files:** `src/polytwin/bridge/validity.py`, `tests/unit/test_validity.py`

**M4-C2 验收：版本变化立即失效**

```python
class ValidityManager:
    def is_valid(self, output: BridgeOutput, current_obj: TwinObject, current_dp: DomainPack) -> bool:
        binding = output.validity.consistency_binding
        # 版本号不匹配 → 立即失效
        if binding.twin_object_version != current_obj.internal.identity.version:
            return False
        if binding.domain_pack_version != current_dp.domain_version:
            return False
        # 时间过期
        if datetime.now(timezone.utc) > output.validity.valid_until:
            return False
        return True
```

**测试用例：**

| 测试 | 预期 |
|------|------|
| 版本匹配 + 时间未过期 | valid |
| TwinObject 版本号变化 | invalid |
| DomainPack 版本号变化 | invalid |
| 时间过期 | invalid |

- [ ] **Step 1-5: TDD**

---

## Task 6: 人类行动响应

**Files:** `src/polytwin/bridge/human_response.py`, `tests/unit/test_human_response.py`

**M4-C3 验收：exception_request ≠ override**

```python
class HumanResponseHandler:
    async def handle(self, output: BridgeOutput, action_id: str, caller: CallerIdentity) -> HumanActionResponse:
        # 1. 验证有效期
        if not self._validity.is_valid(output, self._current_obj, self._current_dp):
            return HumanActionResponse(status="rejected_due_to_expiry")
        # 2. 验证角色权限
        action = self._find_action(output, action_id)
        if not self._roles.can_execute(caller.role, action):
            return HumanActionResponse(status="rejected_due_to_unauthorized")
        # 3. permanently_forbidden 检查
        if isinstance(action, ForbiddenAction) and action.permanently_forbidden:
            # exception_request 只能发起审查流程，不能绕过
            return HumanActionResponse(status="rejected_due_to_unauthorized")
        return HumanActionResponse(status="accepted")
```

- [ ] **Step 1-5: TDD**

---

## Task 7: 角色权限

**Files:** `src/polytwin/bridge/roles.py`, `tests/unit/test_roles.py`

从 DomainPack 的 human_roles 配置中加载角色权限。

- [ ] **Step 1-5: TDD**

---

## Task 8: AuditLogWriter

**Files:** `src/polytwin/bridge/audit_writer.py`, `tests/unit/test_audit_writer.py**

与 Core 的 AuditLogWriter 共享 Protocol 定义，Bridge 不知道自己用的是哪个实现。

- [ ] **Step 1-5: TDD**

---

## Task 9: Bridge 宪法检查

**Files:** `src/polytwin/bridge/constitution.py`, `tests/unit/test_constitution.py`

**Bridge 宪法四条规则，每条必须有测试：**

| 规则 | 测试 |
|------|------|
| 输出不含"建议"或同义词 | 构建输出 → 搜索"建议"、"recommend"等词 → 断言不存在 |
| 每次生成写入审计 | 调用 build_action_space → 验证 audit_writer.write 被调用 |
| 不向执行器直接发指令 | Bridge 模块不包含 send_to_actuator 类方法 |
| exception_request ≠ override | permanently_forbidden 行动的 exception 只能发起审查 |

- [ ] **Step 1-5: TDD**

---

## M4 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M4-C1: 分类正确性** | `pytest tests/unit/test_action_space.py -v` | 4 种场景分类正确 |
| **M4-C2: 有效期管理** | `pytest tests/unit/test_validity.py -v` | 版本变化 → 立即失效 |
| **M4-C3: exception ≠ override** | `pytest tests/unit/test_human_response.py::TestExceptionNotOverride -v` | permanently_forbidden 不可绕过 |
| **M4-C4: 审计不可修改** | `pytest tests/unit/test_decision.py -v` | frozen 模型修改被拒绝 |
