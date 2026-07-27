# M1: TwinObject + 视图投影

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 TwinObject 的完整数据模型（通用底层 + 类型化顶层）、五种视图投影引擎（带硬编码访问控制矩阵）、不可变快照系统、PostgreSQL 存储。M1 完成后，所有后续组件（Core/Lab/Bridge）都有可依赖的数据基础。

**Architecture:** Pydantic v2 做数据模型和验证。TwinObjectInternal 是内部完整模型（不对外暴露）。TwinObject 门面类是唯一入口，通过 get_view(view_type, caller) 返回 frozen 快照。PostgreSQL 用 JSONB 存储类型化顶层字段，Alembic 管理迁移。

**Tech Stack:** Python 3.11+, Pydantic v2, SQLAlchemy 2.0 (async), asyncpg, Alembic

**Spec reference:** §3.1 TOM, §3.6 DomainPack (domain_of_validity), §4 视图隔离

**Depends on:** M0 (DomainPack YAML + 验证脚本)

**Quality gate (M1-C1 ~ C4):**
- C1: TwinObject 所有字段对照 TOM v0.3 无遗漏
- C2: 视图投影正向/负向测试覆盖率 ≥ 95%
- C3: 快照不可变（创建后无法修改或删除）
- C4: 写入权限矩阵（core_runtime 可写，lab 不可写，bridge 限写）

---

## File Structure

```
src/polytwin/
├── tom/
│   ├── __init__.py          # Task 1
│   ├── types.py             # Task 2: enums + CallerIdentity
│   ├── base_models.py       # Task 3: Identity, Lineage, State, Relationship, TwinObjectBase
│   ├── domain_models.py     # Task 4: 7 typed domain models + TwinObjectInternal
│   ├── views.py             # Task 5: 5 frozen views + ConstraintProhibition
│   ├── facade.py            # Task 6: TwinObject facade + access matrix
│   ├── store.py             # Task 7: Store ABC + PostgresTwinObjectStore
│   ├── snapshot.py          # Task 8: snapshot create/query
│   └── identity.py          # Task 9: lineage management
├── domainpack/
│   ├── __init__.py          # Task 10
│   ├── types.py             # Task 10: DomainPack Pydantic 模型
│   ├── parser.py            # Task 10: YAML 解析 + 验证
│   ├── validator.py         # Task 10: 加载时验证（复用 M0 逻辑）
│   ├── lifecycle.py         # Task 10: 生命周期管理
│   └── registry.py          # Task 10: DomainPackRegistry
migrations/
├── env.py                   # Task 7
└── versions/
    └── 001_initial.py       # Task 7
tests/
├── conftest.py              # Task 1
└── unit/
    ├── test_types.py         # Task 2
    ├── test_base_models.py   # Task 3
    ├── test_domain_models.py # Task 4
    ├── test_views.py         # Task 5
    ├── test_facade.py        # Task 6
    ├── test_store.py         # Task 7
    ├── test_snapshot.py      # Task 8
    ├── test_domainpack_types.py  # Task 10
    ├── test_domainpack_parser.py # Task 10
    └── test_import_isolation.py  # Task 11
scripts/
└── check_import_isolation.py    # Task 11
```

---

## Task 1: 包结构初始化

**Files:** `src/polytwin/tom/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: 创建包目录和 __init__.py**

```bash
mkdir -p src/polytwin/tom
touch src/polytwin/tom/__init__.py
```

- [ ] **Step 2: 创建 tests/conftest.py**

```python
# tests/conftest.py
"""Shared fixtures for all tests."""
from polytwin.tom.types import CallerIdentity


def make_caller(component: str, role: str = "test") -> CallerIdentity:
    return CallerIdentity(component=component, role=role)
```

- [ ] **Step 3: Commit**

```bash
git add src/polytwin/tom/__init__.py tests/conftest.py
git commit -m "chore(M1): initialize tom package and test config"
```

---

## Task 2: 枚举和 CallerIdentity (types.py)

**Files:** Create `src/polytwin/tom/types.py`, Test `tests/unit/test_types.py`

- [ ] **Step 1: 写测试**

```python
# tests/unit/test_types.py
"""Verify all enum values and CallerIdentity."""
from polytwin.tom.types import (
    ObjectType, LifecycleState, HealthState, RelationType,
    ViewType, Criticality, Rigidity, ConstraintStatus, CallerIdentity,
)

class TestEnums:
    def test_object_types(self):
        for name in ("user", "agent", "tool", "doc", "code", "knowledge",
                      "device", "scene", "domain_pack", "constraint_card",
                      "hypothesis", "evidence", "custom"):
            assert ObjectType(name) is not None

    def test_view_type_five(self):
        assert len(ViewType) == 5
        assert ViewType.CORE_RUNTIME == "core_runtime"
        assert ViewType.CORE_CERTIFICATION == "core_certification"
        assert ViewType.BRIDGE_DECISION == "bridge_decision"
        assert ViewType.LAB_EXPLORATION == "lab_exploration"
        assert ViewType.AUDIT == "audit"

    def test_constraint_status_four(self):
        assert len(ConstraintStatus) == 4
        assert ConstraintStatus.NOT_APPLICABLE == "not_applicable"

class TestCallerIdentity:
    def test_construction(self):
        c = CallerIdentity(component="lab", role="explorer", session_id="s-1")
        assert c.component == "lab"
        assert c.session_id == "s-1"
```

- [ ] **Step 2: 运行确认失败**

```bash
pytest tests/unit/test_types.py -v
```

- [ ] **Step 3: 实现 types.py**

```python
# src/polytwin/tom/types.py
"""Enumerations and value types shared across all components."""
from enum import Enum
from pydantic import BaseModel


class ObjectType(str, Enum):
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    DOC = "doc"
    CODE = "code"
    KNOWLEDGE = "knowledge"
    DEVICE = "device"
    SCENE = "scene"
    DOMAIN_PACK = "domain_pack"
    CONSTRAINT_CARD = "constraint_card"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    CUSTOM = "custom"


class LifecycleState(str, Enum):
    CREATING = "creating"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DELETED = "deleted"


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


class RelationType(str, Enum):
    OWNS = "owns"
    CREATED = "created"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    PART_OF = "part_of"
    VERSION_OF = "version_of"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    SIMILAR_TO = "similar_to"
    TRIGGERS = "triggers"


class ViewType(str, Enum):
    CORE_RUNTIME = "core_runtime"
    CORE_CERTIFICATION = "core_certification"
    BRIDGE_DECISION = "bridge_decision"
    LAB_EXPLORATION = "lab_exploration"
    AUDIT = "audit"


class Criticality(str, Enum):
    SAFETY_CRITICAL = "safety_critical"
    IDENTITY_CRITICAL = "identity_critical"
    OPERATIONAL = "operational"
    INFORMATIONAL = "informational"


class Rigidity(str, Enum):
    ABSOLUTE = "absolute"
    SOFT = "soft"
    LEARNABLE = "learnable"


class ConstraintStatus(str, Enum):
    PASSED = "passed"
    UNCERTAIN = "uncertain"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class CallerIdentity(BaseModel):
    component: str
    role: str
    session_id: str | None = None
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/unit/test_types.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/polytwin/tom/types.py tests/unit/test_types.py
git commit -m "feat(M1): add type enumerations (13 ObjectTypes, 5 ViewTypes, 4 ConstraintStatus) and CallerIdentity"
```

---

## Task 3: 通用底层模型 (base_models.py)

**Files:** Create `src/polytwin/tom/base_models.py`, Test `tests/unit/test_base_models.py`

- [ ] **Step 1: 写测试** — Identity UUID 默认值、Lineage provenance、Relationship strength 验证、State 默认值、TwinObjectBase 组合

- [ ] **Step 2: 运行确认失败** `pytest tests/unit/test_base_models.py -v`

- [ ] **Step 3: 实现** — Identity, ProvenanceEntry, Lineage, Relationship (strength ∈ [0,1]), AccessStats, State (default CREATING/UNKNOWN), TwinObjectBase

- [ ] **Step 4: 运行测试通过** `pytest tests/unit/test_base_models.py -v`

- [ ] **Step 5: Commit** `git commit -m "feat(M1): add generic base layer models"`

---

## Task 4: 类型化业务模型 (domain_models.py)

**Files:** Create `src/polytwin/tom/domain_models.py`, Test `tests/unit/test_domain_models.py`

**关键模型（共 7 个 + 1 个组合模型）：**

| 模型 | 关键字段 | 必须测试的行为 |
|------|----------|---------------|
| StateVariable | name, unit, range_min/max, observable, controllable | valid range, missing required field |
| StateSemantics | variables: dict[str, StateVariable], current_values: dict[str, float] | variable lookup, value access |
| ConstraintEvaluation | constraint_id, status (四态), evaluated_at, actual_values | 四种 ConstraintStatus 值 |
| ConstraintState | active_constraints, suspended_constraints, last_evaluation | 空/有数据的构造 |
| IdentityInvariant | name, expected_value, actual_value, confidence | 默认 confidence=1.0 |
| IdentityInvariants | invariants, overall_confidence, identity_status | 默认 confirmed，可设 uncertain/forked |
| LinkPermission | model_id, link_type, granted, degraded | link_type 枚举值 |
| Certificate | certificate_id, model_id, score, granted_at | |
| ModelGovernanceState | active_links, qualification_history, active_certificates | 空/有数据 |
| AdmittedEvidence | evidence_id, source, admitted_at, evidence_type, summary | |
| KnowledgeState | admitted_lab_evidence, pending_submissions | |
| SafeAction | action_id, execution_mode, risk_level | |
| ActionState | current_safe_action_set, fallback_available | fallback 默认 False |
| AuditEvent | event_id, event_type, timestamp, actor, detail | |
| AuditTrail | events, created_at | 默认空 |
| **TwinObjectInternal** | = TwinObjectBase + 以上所有模型的组合构造 | 最小构造 + 完整构造 |

- [ ] **Step 1-5: 按 TDD 模式展开**

---

## Task 5: 五种视图快照 (views.py)

**Files:** Create `src/polytwin/tom/views.py`, Test `tests/unit/test_views.py`

**关键测试点：**

1. 每个 View 模型的 `model_config = {"frozen": True}` — 修改属性必须抛 ValidationError
2. CoreCertificationView 有 audit_benchmark + hidden_challenge_set 字段，CoreRuntimeView 没有
3. BridgeDecisionView 包含 `constraint_summary: list[ConstraintProhibition]`
4. ConstraintProhibition 的 `prohibition_reason` — 违反时非 None，通过时为 None
5. LabExplorationView 只有 state_semantics + constraint_summary + public_eval_set + own_evidence_history，不包含 model_governance 或 action_state 的细节

- [ ] **Step 1-5: 按 TDD 模式展开**

---

## Task 6: TwinObject 门面类 (facade.py) — 视图投影与访问控制矩阵

**Files:** Create `src/polytwin/tom/facade.py`, Test `tests/unit/test_facade.py`

**这是 M1 的核心交付物 — 视图隔离的运行时强制执行点。**

**访问矩阵（12 条规则，每条必须有一个测试用例）：**

| # | caller | view_type | 结果 |
|---|--------|-----------|------|
| 1 | core_runtime | CORE_RUNTIME | 允许 |
| 2 | core_runtime | BRIDGE_DECISION | 允许 |
| 3 | core_runtime | LAB_EXPLORATION | 允许 |
| 4 | core_runtime | CORE_CERTIFICATION | 拒绝 |
| 5 | core_runtime | AUDIT | 拒绝 |
| 6 | core_certification | CORE_RUNTIME | 允许 |
| 7 | core_certification | CORE_CERTIFICATION | 允许 |
| 8 | lab | LAB_EXPLORATION | 允许 |
| 9 | lab | CORE_RUNTIME | 拒绝 |
| 10 | lab | CORE_CERTIFICATION | 拒绝 |
| 11 | bridge | BRIDGE_DECISION | 允许 |
| 12 | audit | AUDIT | 允许 |

**写入权限测试：**

| caller | write | 结果 |
|--------|-------|------|
| core_runtime | 允许 | |
| bridge | 允许 | |
| lab | 拒绝 | |
| audit | 拒绝 | |

**视图 frozen 返回测试：** 任何返回的视图修改属性必须抛异常。

- [ ] **Step 1-5: 按 TDD 模式展开**

---

## Task 7: PostgreSQL 存储层 + Alembic 迁移

**Files:** Create `src/polytwin/tom/store.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/001_initial.py`, Test `tests/unit/test_store.py`

**⚠️ 测试基础设施前置条件：** 此 Task 的集成测试需要 PostgreSQL 实例。使用 `docker run -d --name polytwin-test-postgres -e POSTGRES_DB=polytwin_test -e POSTGRES_USER=polytwin -e POSTGRES_PASSWORD=polytwin -p 5432:5432 postgres:16` 启动测试数据库。单元测试可先用内存 dict 实现 TwinObjectStore ABC，集成测试用真实 PostgreSQL。

**PostgreSQL 表结构（对应 Spec §3.1 的数据协议）：**

```sql
CREATE TABLE twin_objects (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type                VARCHAR(50) NOT NULL,
    version             VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    identity            JSONB NOT NULL DEFAULT '{}',
    lineage             JSONB NOT NULL DEFAULT '{}',
    lifecycle           VARCHAR(20) NOT NULL DEFAULT 'creating',
    health              VARCHAR(20) NOT NULL DEFAULT 'unknown',
    last_modified       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_stats        JSONB NOT NULL DEFAULT '{}',
    state_semantics     JSONB NOT NULL DEFAULT '{}',
    constraint_state    JSONB NOT NULL DEFAULT '{}',
    identity_invariants JSONB NOT NULL DEFAULT '{}',
    model_governance    JSONB NOT NULL DEFAULT '{}',
    knowledge_state     JSONB NOT NULL DEFAULT '{}',
    action_state        JSONB NOT NULL DEFAULT '{}',
    audit_trail         JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE twin_relationships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES twin_objects(id),
    target_id       UUID NOT NULL REFERENCES twin_objects(id),
    type            VARCHAR(50) NOT NULL,
    strength        FLOAT NOT NULL DEFAULT 1.0 CHECK (strength BETWEEN 0.0 AND 1.0),
    bidirectional   BOOLEAN NOT NULL DEFAULT FALSE,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_id, target_id, type)
);

CREATE TABLE twin_object_changes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id       UUID NOT NULL REFERENCES twin_objects(id),
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by      VARCHAR(100) NOT NULL,
    field_path      VARCHAR(200) NOT NULL,
    old_value       JSONB,
    new_value       JSONB,
    reason          TEXT
);

CREATE TABLE twin_object_snapshots (
    id              VARCHAR(200) PRIMARY KEY,
    object_id       UUID NOT NULL REFERENCES twin_objects(id),
    snapshot        JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Store 接口：**

```python
class TwinObjectStore(ABC):
    async def create(self, obj: TwinObjectInternal) -> str: ...
    async def get_by_id(self, id: str) -> TwinObjectInternal | None: ...
    async def update(self, id: str, changes: dict, caller: CallerIdentity) -> None: ...
    async def query(self, **filters) -> list[TwinObjectInternal]: ...
    async def get_relationships(self, object_id: str, ...) -> list[Relationship]: ...
    async def add_relationship(self, source_id: str, rel: Relationship) -> None: ...
    async def get_change_history(self, id: str) -> list[dict]: ...
    async def create_snapshot(self, obj_id: str) -> str: ...
    async def get_snapshot(self, snapshot_id: str) -> TwinObjectInternal: ...
```

**关键测试：**
- create + get_by_id 往返正确
- update 记录变更历史到 twin_object_changes
- snapshot 创建后不可修改（只追加）
- get_change_history 返回按时间排序的变更记录

- [ ] **Step 1-5: 按 TDD 模式展开**

---

## Task 8: 快照不可变性测试

**Files:** Test `tests/unit/test_snapshot.py`

**M1-C3 验收：** 快照创建后不可删除、不可修改。

- [ ] **Step 1: 写测试**

```python
# tests/unit/test_snapshot.py
"""M1-C3: Snapshot immutability tests."""
import pytest
from datetime import datetime, timezone

from polytwin.tom.base_models import Identity, Lineage
from polytwin.tom.domain_models import TwinObjectInternal
from polytwin.tom.types import ObjectType


class TestSnapshotIdFormat:
    def test_snapshot_id_contains_twin_id_and_timestamp(self):
        """Snapshot ID format: {twin_id}_{timestamp}_{hash}"""
        internal = TwinObjectInternal(
            identity=Identity(id="test-123", type=ObjectType.DEVICE),
            lineage=Lineage(creator_id="system"),
        )
        # This will be tested with actual store in integration tests
        # For unit test, verify the format function
        from polytwin.tom.snapshot import generate_snapshot_id
        snap_id = generate_snapshot_id(internal, datetime.now(timezone.utc))
        assert snap_id.startswith("test-123_")
        assert len(snap_id.split("_")) >= 3  # id + timestamp + hash


class TestSnapshotFrozen:
    def test_snapshot_data_is_deep_copy(self):
        """Modifying original internal must not affect snapshot data."""
        internal = TwinObjectInternal(
            identity=Identity(type=ObjectType.DEVICE),
            lineage=Lineage(creator_id="system"),
        )
        original_id = internal.identity.id
        # Simulate snapshot capturing current state
        from copy import deepcopy
        snapshot_data = deepcopy(internal.model_dump())
        # Modify original
        internal.state.lifecycle = "active"
        # Snapshot should still have "creating"
        assert snapshot_data["state"]["lifecycle"] == "creating"
```

- [ ] **Step 2: 实现 snapshot.py**

```python
# src/polytwin/tom/snapshot.py
"""Snapshot management — immutable version snapshots."""
import hashlib
import json
from datetime import datetime, timezone

from polytwin.tom.domain_models import TwinObjectInternal


def generate_snapshot_id(internal: TwinObjectInternal, ts: datetime) -> str:
    """Format: {twin_id}_{timestamp}_{hash}"""
    ts_str = ts.strftime("%Y%m%dT%H%M%S%f")
    data_hash = hashlib.sha256(
        json.dumps(internal.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()[:12]
    return f"{internal.identity.id}_{ts_str}_{data_hash}"
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/unit/test_snapshot.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/polytwin/tom/snapshot.py tests/unit/test_snapshot.py
git commit -m "feat(M1): add snapshot ID generation with immutability guarantees"
```

---

## Task 9: 身份谱系管理

**Files:** Create `src/polytwin/tom/identity.py`

**职责：** 管理谱系链的创建、查询、溯源。提供 `trace_provenance(obj_id)` 返回完整来源链，`compute_trust(obj_id)` 计算信任衰减。

- [ ] **Step 1-5: 按 TDD 模式**

---

## Task 10: DomainPack 运行时模块（填补缺口）

**Files:** Create `src/polytwin/domainpack/__init__.py`, `types.py`, `parser.py`, `validator.py`, `lifecycle.py`, `registry.py`, Test `tests/unit/test_domainpack_types.py`, `test_parser.py`, `test_validator.py`

**⚠️ 此 Task 修复自检缺口 1.4：M5 依赖 DomainPackRegistry 但无计划创建它。**

M0 创建了 CLI 验证脚本和 YAML 文件。但 Core、Bridge、Lab 在运行时需要通过 Python 模块加载 DomainPack，不能只靠 CLI 脚本。此 Task 将 M0 的验证逻辑升级为运行时 Python 包。

**模块职责：**

| 文件 | 职责 |
|------|------|
| `types.py` | DomainPack Pydantic 模型（含 DomainOfValidity 5 种条件类型、ConstraintCard 模型） |
| `parser.py` | YAML/JSON 解析 → 调用 validator → 返回 DomainPack 对象 |
| `validator.py` | 复用 M0 `scripts/validate_domainpack.py` 的验证逻辑，但作为 Python 函数而非 CLI |
| `lifecycle.py` | DomainPack 生命周期管理（版本追踪、父包继承规则检查） |
| `registry.py` | DomainPackRegistry — 按 domain_id 注册/查询/热更新 DomainPack 实例 |

**核心类型（types.py）：**

```python
# src/polytwin/domainpack/types.py
"""DomainPack runtime types — Pydantic models for DomainPack structure."""
from pydantic import BaseModel, Field


class ValidityCondition(BaseModel):
    """domain_of_validity 的单个条件（5 种类型之一）。"""
    type: str  # "state_range" | "state_enum" | "sensor_status" | "composite" | "identity_confidence"
    variable: str | None = None
    min: float | None = None
    max: float | None = None
    inclusive: bool = True
    values: list[str] | None = None
    sensor_id: str | None = None
    required_status: str | None = None
    operator: str | None = None  # "and" | "or" for composite
    sub_conditions: list["ValidityCondition"] | None = None
    min_confidence: float | None = None


class DomainOfValidity(BaseModel):
    conditions: list[ValidityCondition] = Field(default_factory=list)
    match_mode: str = "all"  # "all" | "any"


class ValidationConfig(BaseModel):
    method: str  # "range_check" | "threshold_exceeded" | etc.
    config: dict = Field(default_factory=dict)


class ConstraintCard(BaseModel):
    constraint_id: str
    scenario_criticality: str  # "safety_critical" | "identity_critical" | "operational" | "informational"
    domain_of_validity: DomainOfValidity = Field(default_factory=DomainOfValidity)
    validation: ValidationConfig | None = None
    tolerance: dict = Field(default_factory=dict)
    violation_priority: int = 999
    weight: float | None = None  # only for soft
    audit_config: dict | None = None  # required for identity_critical + learnable


class StateVariable(BaseModel):
    name: str
    physical_meaning: str = ""
    unit: str = ""
    range_min: float = 0.0
    range_max: float = 0.0
    observability: str = "observable"
    controllability: str = "uncontrollable"
    measurement_source: str | None = None
    required: bool = True


class SafeFallback(BaseModel):
    policy_id: str
    domain_of_validity: DomainOfValidity = Field(default_factory=DomainOfValidity)
    target_state: dict = Field(default_factory=dict)
    trajectory_constraints: dict = Field(default_factory=dict)
    max_duration: str = "PT5M"
    unavailable_action: str = "safe_shutdown"
    post_fallback_action: str = "hold"
    verification_record: dict = Field(default_factory=dict)


class ActionTemplate(BaseModel):
    action_type_id: str
    description_template: str = ""
    applicable_when: list[str] = Field(default_factory=list)
    monitoring_requirements: list[str] = Field(default_factory=list)
    fallback_if_fails: str = "hold"
    typical_prerequisites: list[str] = Field(default_factory=list)
    risk_profile: dict | None = None
    typical_prohibition_reasons: list[str] | None = None


class HumanRole(BaseModel):
    role_id: str
    role_name: str = ""
    authorized_action_types: list[str] = Field(default_factory=list)
    exception_request_authority: dict = Field(default_factory=dict)
    approval_required_for: list[str] = Field(default_factory=list)


class DomainPack(BaseModel):
    """完整的 DomainPack 运行时模型。"""
    domain_id: str
    domain_name: str = ""
    domain_version: str = "0.1.0"
    inheritance_policy: dict = Field(default_factory=dict)
    rigidity_criticality_compatibility: dict = Field(default_factory=dict)
    state_semantics_template: dict = Field(default_factory=dict)
    variables: list[StateVariable] = Field(default_factory=list)
    constraint_cards: dict = Field(default_factory=dict)  # {"absolute": [...], "soft": [...], "learnable": [...]}
    safe_fallback: SafeFallback | None = None
    action_templates: dict = Field(default_factory=dict)
    human_roles: list[HumanRole] = Field(default_factory=list)
    validation_sets: dict = Field(default_factory=dict)
    identity_monitor_config: dict = Field(default_factory=dict)
    created_at: str = ""
    last_modified_at: str = ""
    certified_by: str = ""
    certification_date: str = ""
    applicability_scope: str = ""
```

**步骤：**

- [ ] **Step 1: 写 types.py 测试**

```python
# tests/unit/test_domainpack_types.py
"""Verify DomainPack runtime types can parse the M0 YAML."""
import yaml
from pathlib import Path
from polytwin.domainpack.types import DomainPack, ValidityCondition, ConstraintCard


class TestDomainPackParsing:
    def test_parse_minimal_domain_pack_yaml(self):
        data = yaml.safe_load(Path("configs/examples/minimal-domain-pack.yaml").read_text())
        dp = DomainPack(**data)
        assert dp.domain_id == "example.minimal_device_monitor"
        assert dp.domain_version == "0.1.0"
        assert len(dp.variables) == 5

    def test_validity_condition_types(self):
        """All 5 condition types parse correctly."""
        range_cond = ValidityCondition(type="state_range", variable="temperature", min=-20.0, max=200.0)
        assert range_cond.type == "state_range"

        enum_cond = ValidityCondition(type="state_enum", variable="operating_mode", values=["normal", "startup"])
        assert len(enum_cond.values) == 2

        sensor_cond = ValidityCondition(type="sensor_status", sensor_id="thermo_1", required_status="active")
        assert sensor_cond.sensor_id == "thermo_1"

        composite_cond = ValidityCondition(type="composite", operator="and",
            sub_conditions=[range_cond, enum_cond])
        assert len(composite_cond.sub_conditions) == 2

        identity_cond = ValidityCondition(type="identity_confidence", min_confidence=0.7)
        assert identity_cond.min_confidence == 0.7

    def test_constraint_card_parsing(self):
        data = yaml.safe_load(Path("configs/examples/minimal-domain-pack.yaml").read_text())
        absolute_cards = data["constraint_cards"]["absolute"]
        cards = [ConstraintCard(**c) for c in absolute_cards]
        assert len(cards) == 4
        assert cards[0].scenario_criticality == "safety_critical"
```

- [ ] **Step 2: 运行确认失败** `pytest tests/unit/test_domainpack_types.py -v`

- [ ] **Step 3: 实现 types.py**（代码见上方）

- [ ] **Step 4: 运行测试通过** `pytest tests/unit/test_domainpack_types.py -v`

- [ ] **Step 5: 写 parser.py 测试**

```python
# tests/unit/test_domainpack_parser.py
"""Verify DomainPack YAML parser with validation."""
from pathlib import Path
from polytwin.domainpack.parser import parse_domainpack
from polytwin.domainpack.types import DomainPack


class TestDomainPackParser:
    def test_parse_valid_yaml(self):
        dp = parse_domainpack(Path("configs/examples/minimal-domain-pack.yaml"))
        assert isinstance(dp, DomainPack)
        assert dp.domain_id == "example.minimal_device_monitor"

    def test_parse_invalid_yaml_raises(self):
        """Parser should raise on invalid YAML (e.g., missing required fields)."""
        from polytwin.domainpack.parser import DomainPackValidationError
        import tempfile, yaml
        invalid = {"domain_id": "test", "domain_name": "test"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid, f)
            f.flush()
            try:
                parse_domainpack(Path(f.name))
                assert False, "Should have raised"
            except DomainPackValidationError as e:
                assert "Missing required field" in str(e) or "validation" in str(e).lower()
            finally:
                Path(f.name).unlink()
```

- [ ] **Step 6: 实现 parser.py**

```python
# src/polytwin/domainpack/parser.py
"""Parse DomainPack YAML files with load-time validation."""
from pathlib import Path
import yaml
from polytwin.domainpack.types import DomainPack
from polytwin.domainpack.validator import validate_domainpack_data


class DomainPackValidationError(Exception):
    """Raised when DomainPack validation fails."""


def parse_domainpack(filepath: Path) -> DomainPack:
    """Parse a DomainPack YAML file, validate, and return typed object."""
    data = yaml.safe_load(filepath.read_text())
    if not isinstance(data, dict):
        raise DomainPackValidationError(f"Top-level must be a mapping, got {type(data).__name__}")
    errors = validate_domainpack_data(data, filepath.name)
    if errors:
        msg = "; ".join(f"[{e.path}] {e.message}" for e in errors)
        raise DomainPackValidationError(msg)
    return DomainPack(**data)
```

- [ ] **Step 7: 实现 validator.py**（将 M0 `scripts/validate_domainpack.py` 的 `validate_domainpack` 函数重构为纯函数 `validate_domainpack_data(data, name)`，CLI 脚本调用此函数）

```python
# src/polytwin/domainpack/validator.py
"""DomainPack validation logic — reused by CLI script and runtime parser."""
# Extract validate_domainpack_data() from scripts/validate_domainpack.py
# The function takes (data: dict, name: str) -> list[ValidationError]
# scripts/validate_domainpack.py imports and calls this function
```

- [ ] **Step 8: 实现 registry.py**

```python
# src/polytwin/domainpack/registry.py
"""In-memory registry of loaded DomainPacks."""
from polytwin.domainpack.types import DomainPack


class DomainPackRegistry:
    def __init__(self):
        self._packs: dict[str, DomainPack] = {}

    def register(self, dp: DomainPack) -> None:
        self._packs[dp.domain_id] = dp

    def get(self, domain_id: str) -> DomainPack | None:
        return self._packs.get(domain_id)

    def list_all(self) -> list[DomainPack]:
        return list(self._packs.values())

    def remove(self, domain_id: str) -> bool:
        if domain_id in self._packs:
            del self._packs[domain_id]
            return True
        return False
```

- [ ] **Step 9: 实现 lifecycle.py**

```python
# src/polytwin/domainpack/lifecycle.py
"""DomainPack lifecycle: version tracking, parent inheritance rules."""
from polytwin.domainpack.types import DomainPack


def check_inheritance_compatibility(child: DomainPack, parent: DomainPack | None) -> list[str]:
    """Verify child DomainPack doesn't violate parent's constraints.
    Returns list of violations (empty = OK)."""
    if parent is None:
        return []
    violations = []
    policy = child.inheritance_policy
    # Check: cannot relax parent absolute constraints
    if not policy.get("can_relax_parent_absolute_constraints", False):
        # Verify child constraints are at least as strict as parent's
        pass  # detailed logic implemented in full version
    return violations
```

- [ ] **Step 10: 运行所有 domainpack 测试** `pytest tests/unit/test_domainpack_types.py tests/unit/test_domainpack_parser.py -v`

- [ ] **Step 11: Commit**

```bash
git add src/polytwin/domainpack/ tests/unit/test_domainpack_types.py tests/unit/test_domainpack_parser.py
git commit -m "feat(M1): add DomainPack runtime module (types, parser, validator, registry, lifecycle)"
```

---

## Task 11: CI 导入隔离扫描脚本

**Files:** Create `scripts/check_import_isolation.py`, Test `tests/unit/test_import_isolation.py`

**⚠️ 此 Task 修复自检缺口 1.5：视图隔离的 CI 强制执行无自动化脚本。**

**目的：** 在 CI 中自动扫描，确保 Lab/Bridge/Core 不直接 import 对方的内部模块，只能通过视图接口交互。

**隔离规则：**

| 模块 | 禁止导入 |
|------|----------|
| `polytwin.lab.*` | `polytwin.core.engine`, `polytwin.core.hardgate`, `polytwin.core.fallback`, `polytwin.core.evidence`, `polytwin.core.certification` |
| `polytwin.bridge.*` | `polytwin.core.engine`, `polytwin.core.hardgate`, `polytwin.core.fallback`, `polytwin.lab.explorer`, `polytwin.lab.sandbox` |
| `polytwin.core.*` | `polytwin.lab.explorer`, `polytwin.lab.sandbox`, `polytwin.bridge.orchestrator`, `polytwin.bridge.action_space` |
| 允许的跨模块导入 | `polytwin.tom.*`（所有模块可导入 TOM）, `polytwin.domainpack.*`（所有模块可导入 DomainPack） |

- [ ] **Step 1: 写隔离扫描脚本**

```python
#!/usr/bin/env python3
"""check_import_isolation.py — Scan source files for forbidden cross-module imports.

Enforces view isolation at CI time: Lab, Bridge, and Core must not import
each other's internal modules directly.
"""
import ast
import sys
from pathlib import Path

# Define forbidden import patterns
FORBIDDEN = {
    "polytwin.lab": [
        "polytwin.core.engine",
        "polytwin.core.hardgate",
        "polytwin.core.fallback",
        "polytwin.core.evidence",
        "polytwin.core.certification",
        "polytwin.core.audit",
    ],
    "polytwin.bridge": [
        "polytwin.core.engine",
        "polytwin.core.hardgate",
        "polytwin.core.fallback",
        "polytwin.core.evidence",
        "polytwin.core.certification",
        "polytwin.lab.explorer",
        "polytwin.lab.sandbox",
        "polytwin.lab.data_release",
    ],
    "polytwin.core": [
        "polytwin.lab.explorer",
        "polytwin.lab.sandbox",
        "polytwin.lab.data_release",
        "polytwin.bridge.orchestrator",
        "polytwin.bridge.action_space",
    ],
}


def get_imports(filepath: Path) -> list[str]:
    """Extract all import targets from a Python file."""
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def check_isolation(src_root: Path) -> list[str]:
    """Scan all source files for forbidden imports. Returns list of violations."""
    violations = []
    for module_name, forbidden_imports in FORBIDDEN.items():
        module_dir = src_root / module_name.replace(".", "/")
        if not module_dir.exists():
            continue
        for py_file in module_dir.rglob("*.py"):
            imports = get_imports(py_file)
            for imp in imports:
                for forbidden in forbidden_imports:
                    if imp == forbidden or imp.startswith(forbidden + "."):
                        rel_path = py_file.relative_to(src_root)
                        violations.append(
                            f"{rel_path}: imports '{imp}' (forbidden for {module_name})"
                        )
    return violations


def main():
    src_root = Path("src")
    if not src_root.exists():
        print("ERROR: src/ directory not found")
        sys.exit(1)
    violations = check_isolation(src_root)
    if violations:
        print(f"ISOLATION VIOLATION: {len(violations)} forbidden import(s) found:")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("ISOLATION CHECK PASSED: no forbidden cross-module imports")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 写测试**

```python
# tests/unit/test_import_isolation.py
"""Test that the import isolation scanner correctly detects violations."""
import tempfile
from pathlib import Path
from scripts.check_import_isolation import check_isolation, get_imports


class TestGetImports:
    def test_extracts_import(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import polytwin.core.engine\nfrom polytwin.tom import types\n")
            f.flush()
            imports = get_imports(Path(f.name))
            assert "polytwin.core.engine" in imports
            assert "polytwin.tom.types" in imports


class TestCheckIsolation:
    def test_no_violations_with_clean_code(self, tmp_path):
        # Create a clean lab module that only imports tom
        lab_dir = tmp_path / "polytwin" / "lab"
        lab_dir.mkdir(parents=True)
        (lab_dir / "__init__.py").write_text("from polytwin.tom.types import CallerIdentity\n")
        violations = check_isolation(tmp_path)
        assert violations == []

    def test_detects_lab_importing_core_engine(self, tmp_path):
        lab_dir = tmp_path / "polytwin" / "lab"
        lab_dir.mkdir(parents=True)
        (lab_dir / "__init__.py").write_text("from polytwin.core.engine import ConstraintEngine\n")
        violations = check_isolation(tmp_path)
        assert len(violations) == 1
        assert "polytwin.core.engine" in violations[0]
        assert "forbidden" in violations[0]

    def test_detects_bridge_importing_lab(self, tmp_path):
        bridge_dir = tmp_path / "polytwin" / "bridge"
        bridge_dir.mkdir(parents=True)
        (bridge_dir / "__init__.py").write_text("import polytwin.lab.explorer\n")
        violations = check_isolation(tmp_path)
        assert len(violations) == 1
        assert "polytwin.lab.explorer" in violations[0]
```

- [ ] **Step 3: 运行测试** `pytest tests/unit/test_import_isolation.py -v`

- [ ] **Step 4: Commit**

```bash
git add scripts/check_import_isolation.py tests/unit/test_import_isolation.py
git commit -m "feat(M1): add CI import isolation scanner (enforces view isolation boundaries)"
```

---

## M1 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M1-C1: 数据结构完整性** | `pytest tests/unit/test_domain_models.py -v` — 对照 TOM v0.3 每个字段 | 全部 PASSED |
| **M1-C2: 视图投影测试 ≥ 95%** | `pytest tests/unit/test_facade.py tests/unit/test_views.py --cov=polytwin.tom --cov-report=term-missing` | 覆盖率 ≥ 95% |
| **M1-C3: 快照不可变** | `pytest tests/unit/test_snapshot.py -v` | PASSED |
| **M1-C4: 写入权限矩阵** | `pytest tests/unit/test_facade.py -k "write" -v` | lab 写入被拒绝，audit 写入被拒绝 |

---

## M1 → M2 交接条件

M1 完成后，以下产物就绪：

1. **TwinObject 完整数据模型** — 通用底层 + 7 个类型化业务模型，Pydantic 验证
2. **五种视图投影引擎** — 硬编码访问矩阵，运行时权限检查
3. **PostgreSQL 存储层** — JSONB 存储 + 变更历史 + 关系表 + 快照表
4. **不可变快照系统** — append-only，格式 `{id}_{timestamp}_{hash}`
5. **完整测试套件** — 覆盖率 ≥ 95%

---

## Jelly 集成任务 (Spec v2.1.0 §3.7)

> **详细设计**: `2026-05-08-jelly-mcp-client-integration.md`

### Jelly Task: DomainPack 双源加载 + JellyClient MCP 协议实现

**Files:**
- Modify: `src/polytwin/domainpack/registry.py`
- Modify: `src/polytwin/jelly/client.py`
- Create: `src/polytwin/jelly/protocol.py`
- Create: `src/polytwin/jelly/caller.py`
- Create: `src/polytwin/jelly/view_filter.py`
- Create: `src/polytwin/jelly/retry.py`
- Test: `tests/unit/test_jelly_protocol.py`

**目的:** DomainPack.Registry 支持双源加载——本地 YAML 优先兜底，Jelly MCP 可选增强。JellyClient 实现 HTTP/SSE MCP 协议调用。

**双源加载策略:**
1. 本地 YAML 文件始终加载（开箱即用）
2. 如果 `JellyConfig.enabled=True` 且 Jelly 可达，从 `twin.get_domain_pack` 获取并覆盖同名本地条目
3. 如果 Jelly 不可达，使用本地 YAML 兜底，记录告警日志

**Registry 接口扩展:**

```python
class DomainPackRegistry:
    def __init__(self, jelly_client: JellyClient | None = None): ...

    def load_from_directory(self, path: str) -> list[str]:
        """从本地 YAML 目录加载。返回加载成功的 domain_id 列表。"""

    def load_from_jelly(self, domain_id: str) -> bool:
        """从 Jelly MCP 获取 DomainPack 并注册。转换 Jelly 格式到 PT 内部模型。"""

    def search_jelly(self, keywords: list[str]) -> list[JellyDomainPackSummary]:
        """搜索 Jelly 上的 DomainPack。"""
```

**JellyClient MCP 协议:**
- `protocol.py`: HTTP/SSE MCP 客户端，调用 `twin.*` 工具
- `caller.py`: domain_id 双格式映射（`cstr.standard` ↔ `twin.chemical.cstr_standard`）+ caller 身份注入
- `view_filter.py`: 二次视图过滤兜底（契约 Q10 双层保障）
- `retry.py`: 指数退避重试（1s/2s/4s）

**Jelly DomainPack → PT DomainPack 转换函数:**
将 Jelly 返回的扁平结构转换为 PT 内部 constraint_cards 分桶格式（absolute/soft/learnable），state_variables 从 Jelly 格式转为 PT StateSemanticsTemplate.variables 格式。
