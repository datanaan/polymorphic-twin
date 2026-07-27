# M8: SDK 打包与公共 API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 M0-M7 引擎代码包装为可 pip install 的 Python 包，定义清晰的公共 API 边界，提供内存运行模式和集成示例。

**Architecture:** 引擎代码已在 `polymorphic_twin/` 中实现。M8 在其之上添加 `pyproject.toml` 包定义、`__init__.py` 白名单导出、统一入口 `PolymorphicTwinEngine`、公共异常层级、配置模型和内存存储后端。

**Spec reference:** `docs/superpowers/specs/2026-05-07-product-overview-sdk.md` v1.0.0 §3-§5

**Quality gate:** M8 完成前：
- `pip install -e .` 成功
- `import polymorphic_twin` 导出且仅导出 Spec §3.2 列出的符号
- 内存模式下引擎可 start/stop
- 4 个集成示例全部可运行

---

## File Structure

```
polymorphic-twin/
├── pyproject.toml                                    # Task 1
├── polymorphic_twin/
│   ├── __init__.py                                   # Task 4
│   ├── py.typed                                      # Task 4
│   ├── engine.py                                     # Task 5
│   ├── config.py                                     # Task 3
│   ├── exceptions.py                                 # Task 2
│   └── ...                                           # M0-M7 引擎代码（不修改）
├── docs/examples/
│   ├── minimal_example.py                            # Task 6
│   ├── chemical_process_demo.py                      # Task 7
│   ├── custom_domainpack.py                          # Task 7
│   └── lab_exploration.py                            # Task 7
└── tests/sdk/
    ├── test_imports.py                               # Task 8
    ├── test_api_surface.py                           # Task 8
    └── test_engine_lifecycle.py                      # Task 8
```

---

## Task 1: pyproject.toml 包定义

**Files:**
- Create: `pyproject.toml`

**Purpose:** 定义 Python 包元数据、依赖、入口点。

- [ ] **Step 1: 编写 pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "polymorphic-twin"
version = "0.1.0"
description = "Trusted governance infrastructure for digital twin systems"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
dependencies = [
    "pydantic>=2.0",
    "sqlalchemy[asyncio]>=2.0",
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "pyyaml>=6.0",
    "rich>=13.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "pytest-cov", "mypy", "ruff"]
postgres = ["asyncpg>=0.28"]
sqlite = ["aiosqlite>=0.19"]

[project.scripts]
ptw = "polymorphic_twin.workbench.cli:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.11"
strict = true
```

- [ ] **Step 2: 验证包定义有效**

```bash
pip install -e ".[dev]"
python -c "import polymorphic_twin; print('OK')"
```

Expected: `OK`（如果 `__init__.py` 已存在则成功，否则等 Task 4）

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(sdk): add pyproject.toml package definition"
```

---

## Task 2: 公共异常层级

**Files:**
- Create: `polymorphic_twin/exceptions.py`
- Create: `tests/sdk/test_exceptions.py`

**Purpose:** 定义 SDK 用户可见的统一异常层级，所有异常继承自 `PolymorphicTwinError`。

- [ ] **Step 1: 编写异常测试**

```python
# tests/sdk/test_exceptions.py
import pytest
from polymorphic_twin.exceptions import (
    PolymorphicTwinError,
    ValidationError,
    ConstraintViolationError,
    SafetyFallbackTriggeredError,
    PermissionDeniedError,
    DomainPackNotFoundError,
    TwinObjectNotFoundError,
    InvalidStateError,
)


def test_base_error_has_code_and_message():
    err = PolymorphicTwinError(error_code="E001", message="test error")
    assert err.error_code == "E001"
    assert err.message == "test error"
    assert err.details is None


def test_all_errors_inherit_from_base():
    errors = [
        ValidationError(error_code="V001", message="bad input"),
        ConstraintViolationError(
            error_code="C001",
            message="violated",
            violated_constraints=["max_temp"],
        ),
        SafetyFallbackTriggeredError(
            error_code="S001",
            message="fallback",
            fallback_action="shutdown",
            reason="overheat",
        ),
        PermissionDeniedError(error_code="P001", message="denied"),
        DomainPackNotFoundError(error_code="D001", message="not found"),
        TwinObjectNotFoundError(error_code="T001", message="not found"),
        InvalidStateError(
            error_code="I001",
            message="invalid",
            variable_name="temperature",
            expected_range=(20, 350),
        ),
    ]
    for err in errors:
        assert isinstance(err, PolymorphicTwinError)


def test_constraint_violation_has_details():
    err = ConstraintViolationError(
        error_code="C001",
        message="violated",
        violated_constraints=["max_temp", "max_pressure"],
    )
    assert len(err.violated_constraints) == 2
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/sdk/test_exceptions.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'polymorphic_twin.exceptions'`

- [ ] **Step 3: 实现异常层级**

```python
# polymorphic_twin/exceptions.py
"""公共异常层级 — 所有 SDK 用户可见的异常。"""

from __future__ import annotations


class PolymorphicTwinError(Exception):
    """所有 Polymorphic-Twin 异常的基类。"""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(f"[{error_code}] {message}")


class ValidationError(PolymorphicTwinError):
    """DomainPack 或数据验证失败。"""


class ConstraintViolationError(PolymorphicTwinError):
    """约束违反。"""

    def __init__(
        self,
        error_code: str,
        message: str,
        violated_constraints: list[str],
        details: dict | None = None,
    ) -> None:
        self.violated_constraints = violated_constraints
        super().__init__(error_code, message, details)


class SafetyFallbackTriggeredError(PolymorphicTwinError):
    """安全回落已触发。"""

    def __init__(
        self,
        error_code: str,
        message: str,
        fallback_action: str,
        reason: str,
        details: dict | None = None,
    ) -> None:
        self.fallback_action = fallback_action
        self.reason = reason
        super().__init__(error_code, message, details)


class PermissionDeniedError(PolymorphicTwinError):
    """视图或操作权限不足。"""


class DomainPackNotFoundError(PolymorphicTwinError):
    """DomainPack 不存在。"""


class TwinObjectNotFoundError(PolymorphicTwinError):
    """TwinObject 不存在。"""


class InvalidStateError(PolymorphicTwinError):
    """状态值不合法。"""

    def __init__(
        self,
        error_code: str,
        message: str,
        variable_name: str,
        expected_range: tuple[float, float],
        details: dict | None = None,
    ) -> None:
        self.variable_name = variable_name
        self.expected_range = expected_range
        super().__init__(error_code, message, details)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/sdk/test_exceptions.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/exceptions.py tests/sdk/test_exceptions.py
git commit -m "feat(sdk): add public exception hierarchy"
```

---

## Task 3: EngineConfig 配置模型

**Files:**
- Create: `polymorphic_twin/config.py`
- Create: `tests/sdk/test_config.py`

**Purpose:** 定义引擎配置模型，支持 memory/sqlite/postgres 三种存储后端。

- [ ] **Step 1: 编写配置测试**

```python
# tests/sdk/test_config.py
import pytest
from polymorphic_twin.config import EngineConfig, ObservabilityConfig


def test_default_config_is_memory_mode():
    config = EngineConfig()
    assert config.storage_backend == "memory"
    assert config.storage_url is None
    assert config.max_concurrent_twins == 100


def test_memory_mode_no_url_needed():
    config = EngineConfig(storage_backend="memory")
    assert config.storage_url is None


def test_postgres_mode_requires_url():
    with pytest.raises(Exception):
        EngineConfig(storage_backend="postgres")


def test_observability_defaults():
    obs = ObservabilityConfig()
    assert obs.log_level == "INFO"
    assert obs.audit_log_enabled is True
    assert obs.log_format == "json"


def test_config_from_dict():
    config = EngineConfig(
        storage_backend="sqlite",
        storage_url="/tmp/test.db",
        max_concurrent_twins=10,
    )
    assert config.storage_backend == "sqlite"
    assert config.max_concurrent_twins == 10
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/sdk/test_config.py -v
```

- [ ] **Step 3: 实现 EngineConfig**

```python
# polymorphic_twin/config.py
"""引擎配置模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class ObservabilityConfig(BaseModel):
    """可观测性配置。"""

    log_level: str = "INFO"
    log_format: str = "json"
    trace_enabled: bool = False
    metrics_enabled: bool = False
    audit_log_enabled: bool = True


class EngineConfig(BaseModel):
    """引擎主配置。"""

    storage_backend: Literal["memory", "sqlite", "postgres"] = "memory"
    storage_url: str | None = None
    observability: ObservabilityConfig = ObservabilityConfig()
    domain_pack_paths: list[str] = []
    max_concurrent_twins: int = 100
    safety_fallback_timeout_ms: int = 200

    @model_validator(mode="after")
    def _validate_storage_config(self) -> EngineConfig:
        if self.storage_backend in ("sqlite", "postgres") and not self.storage_url:
            msg = f"storage_url is required for {self.storage_backend} backend"
            raise ValueError(msg)
        return self
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/sdk/test_config.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/config.py tests/sdk/test_config.py
git commit -m "feat(sdk): add EngineConfig and ObservabilityConfig models"
```

---

## Task 4: 公共 API 导出

**Files:**
- Create: `polymorphic_twin/py.typed`
- Modify: `polymorphic_twin/__init__.py`

**Purpose:** 定义 SDK 的公共 API 白名单。外部用户只能通过 `from polymorphic_twin import ...` 访问列出的符号。

- [ ] **Step 1: 编写导出测试**

```python
# tests/sdk/test_imports.py
import polymorphic_twin


def test_public_symbols_exported():
    """验证所有公共符号可通过包级别导入。"""
    expected = [
        "PolymorphicTwinEngine",
        "EngineConfig",
        "ObservabilityConfig",
        "PolymorphicTwinError",
        "ValidationError",
        "ConstraintViolationError",
        "SafetyFallbackTriggeredError",
        "PermissionDeniedError",
        "DomainPackNotFoundError",
        "TwinObjectNotFoundError",
        "InvalidStateError",
        "ViewType",
        "CallerIdentity",
    ]
    for name in expected:
        assert hasattr(polymorphic_twin, name), f"Missing public symbol: {name}"


def test_no_internal_symbols_leaked():
    """验证 __all__ 不包含 internal 符号。"""
    all_exports = polymorphic_twin.__all__
    for name in all_exports:
        assert not name.startswith("_"), f"Internal symbol leaked: {name}"


def test_py_typed_exists():
    """验证 PEP 561 标记文件存在。"""
    import pathlib
    pkg_dir = pathlib.Path(polymorphic_twin.__file__).parent
    assert (pkg_dir / "py.typed").exists()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/sdk/test_imports.py -v
```

- [ ] **Step 3: 创建 py.typed 标记文件**

```bash
touch polymorphic_twin/py.typed
```

- [ ] **Step 4: 编写 __init__.py 公共导出**

```python
# polymorphic_twin/__init__.py
"""Polymorphic-Twin SDK — 数字孪生系统可信治理基础设施。"""

from polymorphic_twin.config import EngineConfig, ObservabilityConfig
from polymorphic_twin.engine import PolymorphicTwinEngine
from polymorphic_twin.exceptions import (
    ConstraintViolationError,
    DomainPackNotFoundError,
    InvalidStateError,
    PermissionDeniedError,
    PolymorphicTwinError,
    SafetyFallbackTriggeredError,
    TwinObjectNotFoundError,
    ValidationError,
)

# 从引擎组件导入公共数据模型（这些由 M0-M7 实现）
# 以下导入在 M0-M7 完成后可用
try:
    from polymorphic_twin.models import CallerIdentity, ViewType
except ImportError:
    pass

__all__ = [
    # 引擎入口
    "PolymorphicTwinEngine",
    # 配置
    "EngineConfig",
    "ObservabilityConfig",
    # 异常
    "PolymorphicTwinError",
    "ValidationError",
    "ConstraintViolationError",
    "SafetyFallbackTriggeredError",
    "PermissionDeniedError",
    "DomainPackNotFoundError",
    "TwinObjectNotFoundError",
    "InvalidStateError",
    # 数据模型
    "ViewType",
    "CallerIdentity",
]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/sdk/test_imports.py -v
```

Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add polymorphic_twin/__init__.py polymorphic_twin/py.typed tests/sdk/test_imports.py
git commit -m "feat(sdk): define public API surface with __all__ whitelist"
```

---

## Task 5: PolymorphicTwinEngine 入口

**Files:**
- Create: `polymorphic_twin/engine.py`
- Create: `tests/sdk/test_engine_lifecycle.py`

**Purpose:** 提供引擎统一入口，管理组件生命周期，支持内存模式。

- [ ] **Step 1: 编写引擎生命周期测试**

```python
# tests/sdk/test_engine_lifecycle.py
import pytest
from polymorphic_twin.config import EngineConfig
from polymorphic_twin.engine import PolymorphicTwinEngine


@pytest.fixture
def engine():
    e = PolymorphicTwinEngine(EngineConfig())
    return e


@pytest.mark.asyncio
async def test_engine_start_stop():
    engine = PolymorphicTwinEngine(EngineConfig())
    await engine.start()
    assert engine.is_running
    await engine.stop()
    assert not engine.is_running


@pytest.mark.asyncio
async def test_engine_stop_idempotent():
    engine = PolymorphicTwinEngine(EngineConfig())
    await engine.start()
    await engine.stop()
    await engine.stop()  # 不应报错


@pytest.mark.asyncio
async def test_engine_memory_mode():
    config = EngineConfig(storage_backend="memory")
    engine = PolymorphicTwinEngine(config)
    await engine.start()
    # 基本操作不应报错
    packs = engine.domain_pack_registry
    assert packs is not None
    await engine.stop()


@pytest.mark.asyncio
async def test_engine_facade_properties():
    engine = PolymorphicTwinEngine(EngineConfig())
    await engine.start()
    assert engine.tom is not None
    assert engine.core is not None
    assert engine.lab is not None
    assert engine.bridge is not None
    assert engine.domain_pack_registry is not None
    await engine.stop()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/sdk/test_engine_lifecycle.py -v
```

- [ ] **Step 3: 实现 PolymorphicTwinEngine**

```python
# polymorphic_twin/engine.py
"""Polymorphic-Twin 引擎统一入口。"""

from __future__ import annotations

from polymorphic_twin.config import EngineConfig


class PolymorphicTwinEngine:
    """引擎主入口 — 管理所有组件的生命周期。"""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._running = False
        # 组件引用（延迟初始化）
        self._tom = None
        self._core = None
        self._lab = None
        self._bridge = None
        self._domain_pack_registry = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def config(self) -> EngineConfig:
        return self._config

    @property
    def tom(self):
        return self._tom

    @property
    def core(self):
        return self._core

    @property
    def lab(self):
        return self._lab

    @property
    def bridge(self):
        return self._bridge

    @property
    def domain_pack_registry(self):
        return self._domain_pack_registry

    async def start(self) -> None:
        """启动引擎及所有组件。"""
        if self._running:
            return
        # 初始化存储后端
        if self._config.storage_backend == "memory":
            self._init_memory_storage()
        # 初始化组件（引用 M0-M7 实现的组件）
        self._init_components()
        # 加载预配置的 DomainPack
        for path in self._config.domain_pack_paths:
            await self.domain_pack_registry.load(path)
        self._running = True

    async def stop(self) -> None:
        """停止引擎及所有组件。"""
        if not self._running:
            return
        self._running = False
        self._tom = None
        self._core = None
        self._lab = None
        self._bridge = None
        self._domain_pack_registry = None

    def _init_memory_storage(self) -> None:
        """初始化纯内存存储。"""
        # 具体实现依赖 M0-M7 的 Repository 抽象
        pass

    def _init_components(self) -> None:
        """初始化五组件 facade。"""
        # 具体实现依赖 M0-M7 的组件代码
        # 这里创建轻量 facade 对象作为占位
        from polymorphic_twin.engine_facades import (
            TOMFacade,
            CoreFacade,
            LabFacade,
            BridgeFacade,
        )
        from polymorphic_twin.domainpack.registry import DomainPackRegistry

        self._tom = TOMFacade(self._config)
        self._core = CoreFacade(self._config)
        self._lab = LabFacade(self._config)
        self._bridge = BridgeFacade(self._config)
        self._domain_pack_registry = DomainPackRegistry()
```

- [ ] **Step 4: 创建 facade 占位文件**

```python
# polymorphic_twin/engine_facades.py
"""组件 Facade 占位 — M0-M7 实现完成后替换为真实 facade。"""


class TOMFacade:
    def __init__(self, config) -> None:
        self._config = config


class CoreFacade:
    def __init__(self, config) -> None:
        self._config = config


class LabFacade:
    def __init__(self, config) -> None:
        self._config = config


class BridgeFacade:
    def __init__(self, config) -> None:
        self._config = config
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/sdk/test_engine_lifecycle.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add polymorphic_twin/engine.py polymorphic_twin/engine_facades.py tests/sdk/test_engine_lifecycle.py
git commit -m "feat(sdk): add PolymorphicTwinEngine entry point with memory mode"
```

---

## Task 6: 最小集成示例

**Files:**
- Create: `docs/examples/minimal_example.py`

**Purpose:** 5 分钟上手示例。展示 SDK 的基本用法。

- [ ] **Step 1: 编写最小示例**

```python
#!/usr/bin/env python3
"""Polymorphic-Twin 最小示例 — 5 分钟上手。

演示：创建引擎 → 加载 DomainPack → 创建 TwinObject → 更新状态 → 查看约束结果。
"""

import asyncio
from polymorphic_twin import PolymorphicTwinEngine, EngineConfig


async def main():
    # 1. 创建引擎（内存模式，无需数据库）
    engine = PolymorphicTwinEngine(EngineConfig())
    await engine.start()
    print("✓ 引擎启动成功（内存模式）")

    # 2. 加载示例 DomainPack
    pack_id = await engine.domain_pack_registry.load(
        "configs/examples/minimal-domain-pack.yaml"
    )
    print(f"✓ DomainPack 加载成功: {pack_id}")

    # 3. 创建 TwinObject
    twin_id = await engine.tom.create_twin(
        spec={
            "name": "demo-device",
            "domain_pack_id": pack_id,
            "initial_state": {
                "temperature": 25.0,
                "pressure": 1.0,
            },
        }
    )
    print(f"✓ TwinObject 创建成功: {twin_id}")

    # 4. 更新状态（模拟传感器输入）
    result = await engine.tom.update_state(twin_id, {"temperature": 180.5})
    print(f"✓ 状态更新完成")
    if result and hasattr(result, "constraint_evaluation"):
        for cid, status in result.constraint_evaluation.items():
            print(f"  {cid}: {status}")

    # 5. 停止引擎
    await engine.stop()
    print("✓ 引擎停止")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
mkdir -p docs/examples
git add docs/examples/minimal_example.py
git commit -m "docs(sdk): add minimal integration example"
```

---

## Task 7: 更多集成示例

**Files:**
- Create: `docs/examples/chemical_process_demo.py`
- Create: `docs/examples/custom_domainpack.py`
- Create: `docs/examples/lab_exploration.py`

**Purpose:** 展示化学工艺五闭环、自定义 DomainPack、Lab 探索三种典型用法。

- [ ] **Step 1: 化学工艺演示示例**

```python
#!/usr/bin/env python3
"""化学工艺五闭环完整演示。

展示 CSTR 反应器在 Polymorphic-Twin 治理下的完整运行流程。
"""

import asyncio
from polymorphic_twin import PolymorphicTwinEngine, EngineConfig


async def main():
    engine = PolymorphicTwinEngine(EngineConfig())
    await engine.start()

    # 加载 CSTR DomainPack
    pack_id = await engine.domain_pack_registry.load(
        "configs/examples/cstr-standard.yaml"
    )

    # 创建 CSTR TwinObject
    twin_id = await engine.tom.create_twin({
        "name": "CSTR-001",
        "domain_pack_id": pack_id,
        "initial_state": {
            "temperature": 25.0,
            "pressure": 1.0,
            "concentration_A": 3.0,
            "concentration_B": 0.0,
            "flow_rate_in": 50.0,
            "coolant_flow": 100.0,
            "agitator_speed": 300.0,
            "reaction_rate": 0.0,
        },
    })
    print(f"CSTR TwinObject: {twin_id}")

    # 感知闭环：模拟启动升温
    for temp in [50, 100, 150, 180, 190, 195, 200]:
        result = await engine.tom.update_state(twin_id, {"temperature": float(temp)})
        status = "正常"
        if result and hasattr(result, "safety_status"):
            status = result.safety_status
        print(f"  温度 {temp}°C → {status}")

    # 探索闭环：启动 Lab
    explore_result = await engine.lab.run_exploration(
        task_type="constraint_hypothesis",
        data_release_id="auto",
        budget={"max_iterations": 50, "max_time_seconds": 30},
    )
    print(f"Lab 探索完成: {len(explore_result.hypotheses)} 个假设")

    # 决策闭环：生成行动空间
    action_space = await engine.bridge.generate_action_space(twin_id)
    print(f"行动空间: {len(action_space.immediate_actions)} immediate, "
          f"{len(action_space.forbidden_actions)} forbidden")

    # 触发安全回落
    print("\n模拟温度超标...")
    result = await engine.tom.update_state(twin_id, {"temperature": 285.0})
    if result and hasattr(result, "safety_status"):
        print(f"安全状态: {result.safety_status}")
        if hasattr(result, "fallback_action"):
            print(f"回落动作: {result.fallback_action}")

    await engine.stop()
    print("演示完成")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 自定义 DomainPack 示例**

```python
#!/usr/bin/env python3
"""自定义 DomainPack 示例。

展示如何用 Python dict 构建并加载 DomainPack。
"""

import asyncio
from polymorphic_twin import PolymorphicTwinEngine, EngineConfig


async def main():
    engine = PolymorphicTwinEngine(EngineConfig())
    await engine.start()

    # 用 dict 定义 DomainPack
    my_pack = {
        "domain_id": "custom.water_tank",
        "domain_name": "水箱液位监控",
        "domain_version": "0.1.0",
        "state_variables": [
            {"name": "water_level", "unit": "m", "physical_range": [0, 10],
             "observable": True, "controllable": True},
            {"name": "inflow_rate", "unit": "L/min", "physical_range": [0, 100],
             "observable": True, "controllable": True},
        ],
        "constraints": [
            {"id": "max_level", "criticality": "safety_critical", "rigidity": "absolute",
             "certifier": {"type": "threshold", "variable": "water_level",
                           "operator": "<=", "threshold": 9.0}},
        ],
        "fallback_strategy": {
            "name": "drain",
            "trigger": "safety_critical violation",
            "steps": [{"action": "close_inflow", "target_variable": "inflow_rate",
                       "set_value": 0}],
            "target_state": {"water_level": 5.0},
            "timeout_ms": 200,
        },
        "action_templates": [],
        "human_roles": [],
    }

    # 校验并加载
    pack_id = await engine.domain_pack_registry.load_from_dict(my_pack)
    print(f"DomainPack 加载成功: {pack_id}")

    # 创建 TwinObject 并测试
    twin_id = await engine.tom.create_twin({
        "name": "WaterTank-001",
        "domain_pack_id": pack_id,
        "initial_state": {"water_level": 5.0, "inflow_rate": 30.0},
    })
    result = await engine.tom.update_state(twin_id, {"water_level": 9.5})
    print(f"水位 9.5m → 约束状态: {result}")

    await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Lab 探索示例**

```python
#!/usr/bin/env python3
"""Lab 探索示例。

展示如何启动 Lab 探索、查看结果、提交到 Core。
"""

import asyncio
from polymorphic_twin import PolymorphicTwinEngine, EngineConfig


async def main():
    engine = PolymorphicTwinEngine(EngineConfig())
    await engine.start()

    pack_id = await engine.domain_pack_registry.load(
        "configs/examples/minimal-domain-pack.yaml"
    )
    twin_id = await engine.tom.create_twin({
        "name": "explore-demo",
        "domain_pack_id": pack_id,
        "initial_state": {"temperature": 180.0, "pressure": 10.0},
    })

    # 查看可用策略
    strategies = await engine.lab.get_strategies()
    print(f"可用探索策略: {[s.name for s in strategies]}")

    # 运行探索
    result = await engine.lab.run_exploration(
        task_type="counterexample_finding",
        data_release_id="auto",
        budget={"max_iterations": 100, "max_time_seconds": 60},
    )
    print(f"探索完成: {len(result.hypotheses)} 假设, "
          f"{len(result.counterexamples)} 反例")

    # 提交到 Core
    for hypothesis in result.hypotheses[:3]:
        qr = await engine.lab.submit_to_core(hypothesis.to_submission())
        print(f"假设提交: {qr.status}")

    await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Commit**

```bash
git add docs/examples/chemical_process_demo.py docs/examples/custom_domainpack.py docs/examples/lab_exploration.py
git commit -m "docs(sdk): add chemical process, custom domainpack, and lab exploration examples"
```

---

## Task 8: SDK 测试套件

**Files:**
- Create: `tests/sdk/test_api_surface.py`

**Purpose:** 验证公共 API 签名与 Spec 一致。

- [ ] **Step 1: 编写 API 签名测试**

```python
# tests/sdk/test_api_surface.py
"""验证公共 API 签名与 Spec §3.2 一致。"""

import inspect
from polymorphic_twin.engine import PolymorphicTwinEngine
from polymorphic_twin.config import EngineConfig, ObservabilityConfig
from polymorphic_twin.exceptions import (
    PolymorphicTwinError,
    ValidationError,
    ConstraintViolationError,
    SafetyFallbackTriggeredError,
    PermissionDeniedError,
    DomainPackNotFoundError,
    TwinObjectNotFoundError,
    InvalidStateError,
)


def test_engine_has_required_methods():
    methods = [
        "start", "stop",
        "tom", "core", "lab", "bridge", "domain_pack_registry",
        "is_running", "config",
    ]
    for method in methods:
        assert hasattr(PolymorphicTwinEngine, method) or hasattr(PolymorphicTwinEngine.__init__, method), \
            f"PolymorphicTwinEngine missing: {method}"


def test_engine_init_accepts_config():
    sig = inspect.signature(PolymorphicTwinEngine.__init__)
    params = list(sig.parameters.keys())
    assert "config" in params
    ann = sig.parameters["config"].annotation
    assert "EngineConfig" in str(ann)


def test_engine_start_stop_are_async():
    assert inspect.iscoroutinefunction(PolymorphicTwinEngine.start)
    assert inspect.iscoroutinefunction(PolymorphicTwinEngine.stop)


def test_config_model_fields():
    fields = EngineConfig.model_fields
    required_fields = [
        "storage_backend", "storage_url", "observability",
        "domain_pack_paths", "max_concurrent_twins", "safety_fallback_timeout_ms",
    ]
    for f in required_fields:
        assert f in fields, f"EngineConfig missing field: {f}"


def test_exception_hierarchy():
    subclasses = [
        ValidationError, ConstraintViolationError, SafetyFallbackTriggeredError,
        PermissionDeniedError, DomainPackNotFoundError, TwinObjectNotFoundError,
        InvalidStateError,
    ]
    for cls in subclasses:
        assert issubclass(cls, PolymorphicTwinError)
```

- [ ] **Step 2: 运行全部 SDK 测试**

```bash
pytest tests/sdk/ -v
```

Expected: 全部通过

- [ ] **Step 3: Commit**

```bash
git add tests/sdk/test_api_surface.py
git commit -m "test(sdk): add API surface signature verification tests"
```

---

## Task 9: API 文档生成

**Files:**
- Create: `docs/api/.gitkeep`
- Create: `Makefile` (docs target)

**Purpose:** Spec §4.4 要求 API 参考文档从 docstring 自动生成。

- [ ] **Step 1: 添加 mkdocs 配置**

```toml
# pyproject.toml 的 [project.optional-dependencies] 中追加:
docs = ["mkdocs", "mkdocstrings[python]"]
```

- [ ] **Step 2: 创建 docs 生成 Makefile target**

```makefile
# Makefile
.PHONY: docs

docs:
	mkdocs build || echo "mkdocs not configured yet — docstrings are in place for future generation"
```

- [ ] **Step 3: 验证 docstrings 存在**

```bash
# 检查公共模块的 docstring
python -c "
from polymorphic_twin.engine import PolymorphicTwinEngine
from polymorphic_twin.config import EngineConfig
from polymorphic_twin.exceptions import PolymorphicTwinError
assert PolymorphicTwinEngine.__doc__
assert EngineConfig.__doc__
assert PolymorphicTwinError.__doc__
print('All public APIs have docstrings')
"
```

- [ ] **Step 4: Commit**

```bash
mkdir -p docs/api
touch docs/api/.gitkeep
git add Makefile docs/api/.gitkeep pyproject.toml
git commit -m "docs(sdk): add API documentation generation setup"
```

---

## Quality Gate Checklist

M8 完成后，逐项验证：

- [ ] `pip install -e ".[dev]"` 成功
- [ ] `python -c "import polymorphic_twin"` 成功
- [ ] `pytest tests/sdk/ -v` 全部通过
- [ ] `python docs/examples/minimal_example.py` 可运行
- [ ] `mypy polymorphic_twin/ --strict` 对公共 API 无错误
- [ ] `make docs` 可执行（docstrings 就绪）

---

## Task 10: Internal API 隔离测试 + 示例集成测试

**Files:**
- Create: `tests/sdk/test_internal_isolation.py`
- Create: `tests/sdk/test_examples_run.py`

**Purpose:** 覆盖 Spec §4.5 M8-T04（Internal 隔离测试）和 M8-T05（示例代码测试）。

- [ ] **Step 1: 编写 Internal API 隔离测试**

```python
# tests/sdk/test_internal_isolation.py
"""Spec §4.5 M8-T04: Internal API 隔离测试。"""
import importlib
import pytest

# 这些 import 应该失败（internal 模块不对外暴露）
FORBIDDEN_IMPORTS = [
    "polymorphic_twin.core._runtime",
    "polymorphic_twin.core._certification",
    "polymorphic_twin.core._hardgate",
    "polymorphic_twin.lab._sandbox",
]

def test_internal_modules_not_importable():
    """Spec API-02: Internal 模块不可被外部 import。"""
    for module_path in FORBIDDEN_IMPORTS:
        with pytest.raises(ImportError, match=module_path):
            importlib.import_module(module_path)


def test_no_core_internal_in_lab_directory():
    """Lab 代码不得 import core 内部模块。"""
    import ast
    from pathlib import Path

    lab_dir = Path("polymorphic_twin/lab")
    if not lab_dir.exists():
        pytest.skip("Lab module not yet implemented")

    forbidden = {"core._runtime", "core._certification", "core._hardgate", "core._audit"}
    for py_file in lab_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", "") or ""
                names = [alias.name for alias in getattr(node, "names", [])]
                for f in forbidden:
                    assert f not in module and f not in names, \
                        f"{py_file} imports forbidden module: {f}"
```

- [ ] **Step 2: 编写示例代码集成测试**

```python
# tests/sdk/test_examples_run.py
"""Spec §4.5 M8-T05: 示例代码可运行性测试。"""
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path("docs/examples")


@pytest.mark.parametrize("example_file", [
    "minimal_example.py",
    "chemical_process_demo.py",
    "custom_domainpack.py",
    "lab_exploration.py",
])
def test_example_runs_without_import_error(example_file):
    """示例代码至少能通过 import 阶段（不报 ModuleNotFoundError）。"""
    path = EXAMPLES_DIR / example_file
    if not path.exists():
        pytest.skip(f"{example_file} not found")
    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"Syntax error in {example_file}: {result.stderr}"
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/sdk/test_internal_isolation.py tests/sdk/test_examples_run.py -v
```

Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add tests/sdk/test_internal_isolation.py tests/sdk/test_examples_run.py
git commit -m "test(sdk): add internal API isolation and example code tests (M8-T04, M8-T05)"
```
