# M11a: 演示层 — CSTR DomainPack 与演示脚本

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建化学工艺 CSTR 演示场景的完整数据基础设施：完整 DomainPack YAML、模拟数据生成器、6 个预定义场景文件、演示运行脚本。

**Architecture:** 独立 Python 脚本通过 API 推送模拟数据驱动演示。数据生成器基于 DomainPack 约束边界生成工况数据。演示脚本调用 API 服务的 REST 端点。

**Spec reference:** `docs/superpowers/specs/2026-05-07-product-demo.md` v1.0.0 §2, §5

**Quality gate:**
- CSTR DomainPack 可被引擎加载
- 数据生成器可生成 4 种工况数据
- `python demo_runner.py` 六阶段全流程跑通

**Depends on:** plan-M10b-api-endpoints.md

---

## File Structure

```
demos/
└── chemical_process/
    ├── README.md
    ├── demo_runner.py              # Task 4
    ├── data_generator.py           # Task 2
    ├── api_client.py               # Task 3
    ├── scenarios/
    │   ├── 01_startup.json         # Task 3
    │   ├── 02_steady_state.json
    │   ├── 03_sensor_drift.json
    │   ├── 04_temperature_spike.json
    │   ├── 05_emergency.json
    │   └── 06_recovery.json
    └── tests/
        ├── test_data_generator.py  # Task 2
        └── test_demo_e2e.py        # Task 5
configs/examples/
    └── cstr-standard.yaml          # Task 1
```

---

## Task 1: CSTR DomainPack 完整 YAML

**Files:**
- Create: `configs/examples/cstr-standard.yaml`
- Create: `tests/demo/test_cstr_domainpack.py`

**Purpose:** 按照演示 Spec §5 定义的完整 CSTR DomainPack，可直接被引擎加载。

- [ ] **Step 1: 编写加载测试**

```python
# tests/demo/test_cstr_domainpack.py
import pytest
from pathlib import Path
import yaml


CSTR_PATH = Path("configs/examples/cstr-standard.yaml")


def test_cstr_file_exists():
    assert CSTR_PATH.exists()


def test_cstr_yaml_valid():
    with open(CSTR_PATH) as f:
        data = yaml.safe_load(f)
    assert data is not None


def test_cstr_has_all_state_variables():
    with open(CSTR_PATH) as f:
        data = yaml.safe_load(f)
    var_names = {v["name"] for v in data["state_variables"]}
    expected = {"temperature", "pressure", "concentration_A", "concentration_B",
                "flow_rate_in", "coolant_flow", "agitator_speed", "reaction_rate"}
    assert expected == var_names


def test_cstr_has_8_constraints():
    with open(CSTR_PATH) as f:
        data = yaml.safe_load(f)
    assert len(data["constraints"]) == 8


def test_cstr_safety_critical_are_absolute():
    with open(CSTR_PATH) as f:
        data = yaml.safe_load(f)
    for c in data["constraints"]:
        if c["criticality"] == "safety_critical":
            assert c["rigidity"] == "absolute", f"{c['id']} is safety_critical but not absolute"


def test_cstr_has_fallback_with_timeout():
    with open(CSTR_PATH) as f:
        data = yaml.safe_load(f)
    fb = data["fallback_strategy"]
    assert "timeout_ms" in fb
    assert fb["timeout_ms"] <= 200


def test_cstr_has_action_templates():
    with open(CSTR_PATH) as f:
        data = yaml.safe_load(f)
    assert len(data["action_templates"]) >= 5


def test_cstr_has_human_roles():
    with open(CSTR_PATH) as f:
        data = yaml.safe_load(f)
    role_ids = {r["id"] for r in data["human_roles"]}
    assert "operator" in role_ids
    assert "supervisor" in role_ids
```

- [ ] **Step 2: 编写 CSTR DomainPack YAML**

```yaml
# configs/examples/cstr-standard.yaml
# CSTR连续搅拌釜反应器标准场景
# 完整定义参照 docs/superpowers/specs/2026-05-07-product-demo.md §5

domain_id: "cstr.standard"
domain_name: "CSTR连续搅拌釜反应器标准场景"
domain_version: "1.0.0"
description: "1000L CSTR放热反应器约束治理标准配置"
author: "Polymorphic-Twin Team"

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
    description: "当前反应速率"

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
    description: "温度超过200°C且上升时温升速率不得超过5°C/min"
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
      expression: "abs(flow_rate_in * concentration_A - reaction_rate * 1000 - flow_rate_in * concentration_B) / max(flow_rate_in * concentration_A, 0.001) <= 0.005"
    domain_of_validity:
      match_mode: "all"
      conditions: []

  - id: "reaction_efficiency"
    description: "反应转化率应大于70%"
    criticality: "operational"
    rigidity: "soft"
    certifier:
      type: "custom"
      expression: "concentration_B / max(concentration_A + concentration_B, 0.001) >= 0.7"
    domain_of_validity:
      match_mode: "all"
      conditions:
        - type: "state_range"
          variable: "temperature"
          min: 100.0

  - id: "yield_optimization"
    description: "寻找最优进料和冷却水组合以最大化收率"
    criticality: "operational"
    rigidity: "learnable"
    certifier:
      type: "learnable"
      target_metric: "concentration_B / max(concentration_A + concentration_B, 0.001)"
      optimization: "maximize"
    domain_of_validity:
      match_mode: "all"
      conditions:
        - type: "state_range"
          variable: "temperature"
          min: 150.0
          max: 250.0

  - id: "agitator_integrity"
    description: "搅拌速度不得超过450RPM"
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
  description: "紧急停机"
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
```

- [ ] **Step 3: 运行测试确认通过**

```bash
pytest tests/demo/test_cstr_domainpack.py -v
```

Expected: 7 passed

- [ ] **Step 4: Commit**

```bash
mkdir -p configs/examples
git add configs/examples/cstr-standard.yaml tests/demo/test_cstr_domainpack.py
git commit -m "feat(demo): add complete CSTR DomainPack YAML"
```

---

## Task 2: 模拟数据生成器

**Files:**
- Create: `demos/chemical_process/data_generator.py`
- Create: `tests/demo/test_data_generator.py`

**Purpose:** 根据 CSTR DomainPack 的约束边界生成四种工况的模拟数据。

- [ ] **Step 1: 编写数据生成器测试**

```python
# tests/demo/test_data_generator.py
import pytest
from demos.chemical_process.data_generator import CSTRDataGenerator, CSTRState


@pytest.fixture
def gen():
    return CSTRDataGenerator()


def test_normal_tick_stays_in_range(gen):
    state = CSTRState(
        temperature=180.0, pressure=12.0, concentration_A=1.8,
        concentration_B=1.2, flow_rate_in=50.0, coolant_flow=100.0,
        agitator_speed=300.0, reaction_rate=2.0,
    )
    for _ in range(100):
        new_state = gen.normal_tick(state)
        assert 170 <= new_state.temperature <= 190
        assert 10 <= new_state.pressure <= 15
        state = new_state


def test_drift_tick_increases_target(gen):
    state = CSTRState(
        temperature=180.0, pressure=12.0, concentration_A=1.8,
        concentration_B=1.2, flow_rate_in=50.0, coolant_flow=100.0,
        agitator_speed=300.0, reaction_rate=2.0,
    )
    temps = []
    for _ in range(20):
        state = gen.drift_tick(state, drift_variable="temperature", drift_rate=2.0)
        temps.append(state.temperature)
    # 温度应该持续上升
    assert temps[-1] > temps[0]


def test_emergency_tick_pushes_to_violation(gen):
    state = CSTRState(
        temperature=250.0, pressure=12.0, concentration_A=1.8,
        concentration_B=1.2, flow_rate_in=50.0, coolant_flow=10.0,
        agitator_speed=300.0, reaction_rate=2.0,
    )
    for _ in range(20):
        state = gen.emergency_tick(state, target_temp=290.0)
    # 应该超过 280°C
    assert state.temperature >= 280.0


def test_recovery_tick_moves_toward_target(gen):
    state = CSTRState(
        temperature=280.0, pressure=20.0, concentration_A=1.8,
        concentration_B=1.2, flow_rate_in=0.0, coolant_flow=200.0,
        agitator_speed=0.0, reaction_rate=0.5,
    )
    target = {"temperature": 50.0}
    for _ in range(30):
        state = gen.recovery_tick(state, target)
    assert state.temperature < 200.0


def test_startup_tick_linear_ramp(gen):
    state = CSTRState(
        temperature=25.0, pressure=1.0, concentration_A=3.0,
        concentration_B=0.0, flow_rate_in=0.0, coolant_flow=0.0,
        agitator_speed=0.0, reaction_rate=0.0,
    )
    temps = []
    for i in range(30):
        progress = i / 29
        state = gen.startup_tick(state, target_temp=180.0, progress=progress)
        temps.append(state.temperature)
    assert temps[-1] >= 175.0  # 接近目标
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/demo/test_data_generator.py -v
```

- [ ] **Step 3: 实现数据生成器**

```python
# demos/chemical_process/data_generator.py
from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np


@dataclass
class CSTRState:
    temperature: float
    pressure: float
    concentration_A: float
    concentration_B: float
    flow_rate_in: float
    coolant_flow: float
    agitator_speed: float
    reaction_rate: float

    def to_dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "pressure": self.pressure,
            "concentration_A": self.concentration_A,
            "concentration_B": self.concentration_B,
            "flow_rate_in": self.flow_rate_in,
            "coolant_flow": self.coolant_flow,
            "agitator_speed": self.agitator_speed,
            "reaction_rate": self.reaction_rate,
        }


class CSTRDataGenerator:
    """CSTR 模拟数据生成器。"""

    # 噪声标准差
    NOISE = {
        "temperature": 2.0,
        "pressure": 0.5,
        "concentration_A": 0.1,
        "concentration_B": 0.1,
        "flow_rate_in": 1.0,
        "coolant_flow": 2.0,
        "agitator_speed": 5.0,
        "reaction_rate": 0.1,
    }

    def _add_noise(self, value: float, key: str) -> float:
        return value + random.gauss(0, self.NOISE.get(key, 1.0))

    def normal_tick(self, state: CSTRState) -> CSTRState:
        """稳态噪声数据。"""
        return CSTRState(
            temperature=self._add_noise(state.temperature, "temperature"),
            pressure=self._add_noise(state.pressure, "pressure"),
            concentration_A=self._add_noise(state.concentration_A, "concentration_A"),
            concentration_B=self._add_noise(state.concentration_B, "concentration_B"),
            flow_rate_in=self._add_noise(state.flow_rate_in, "flow_rate_in"),
            coolant_flow=self._add_noise(state.coolant_flow, "coolant_flow"),
            agitator_speed=self._add_noise(state.agitator_speed, "agitator_speed"),
            reaction_rate=self._add_noise(state.reaction_rate, "reaction_rate"),
        )

    def startup_tick(self, state: CSTRState, target_temp: float, progress: float) -> CSTRState:
        """启动升温：线性插值到目标温度。"""
        new_temp = state.temperature + (target_temp - state.temperature) * 0.1
        new_pressure = 1.0 + (12.0 - 1.0) * progress
        new_flow = target_temp * progress * 0.28  # 线性增加进料
        new_coolant = 100.0 * progress
        new_agitator = 300.0 * progress
        return CSTRState(
            temperature=self._add_noise(new_temp, "temperature"),
            pressure=self._add_noise(new_pressure, "pressure"),
            concentration_A=self._add_noise(3.0 - 1.2 * progress, "concentration_A"),
            concentration_B=self._add_noise(1.2 * progress, "concentration_B"),
            flow_rate_in=self._add_noise(new_flow, "flow_rate_in"),
            coolant_flow=self._add_noise(new_coolant, "coolant_flow"),
            agitator_speed=self._add_noise(new_agitator, "agitator_speed"),
            reaction_rate=self._add_noise(2.0 * progress, "reaction_rate"),
        )

    def drift_tick(self, state: CSTRState, drift_variable: str, drift_rate: float) -> CSTRState:
        """传感器漂移：指定变量持续偏移。"""
        d = state.to_dict()
        d[drift_variable] += drift_rate
        return CSTRState(**{k: self._add_noise(v, k) for k, v in d.items()})

    def emergency_tick(self, state: CSTRState, target_temp: float = 290.0) -> CSTRState:
        """紧急工况：冷却失效，温度飙升。"""
        new_coolant = max(state.coolant_flow - 15, 0)
        temp_rise = (target_temp - state.temperature) * 0.08 + 2.0
        new_temp = state.temperature + temp_rise
        new_pressure = state.pressure + 0.5
        return CSTRState(
            temperature=self._add_noise(new_temp, "temperature"),
            pressure=self._add_noise(new_pressure, "pressure"),
            concentration_A=self._add_noise(state.concentration_A * 0.97, "concentration_A"),
            concentration_B=self._add_noise(state.concentration_B * 1.02, "concentration_B"),
            flow_rate_in=self._add_noise(state.flow_rate_in, "flow_rate_in"),
            coolant_flow=self._add_noise(new_coolant, "coolant_flow"),
            agitator_speed=self._add_noise(state.agitator_speed, "agitator_speed"),
            reaction_rate=self._add_noise(state.reaction_rate * 1.05, "reaction_rate"),
        )

    def recovery_tick(self, state: CSTRState, target: dict) -> CSTRState:
        """恢复：向目标状态逐步靠近。"""
        d = state.to_dict()
        for key, target_val in target.items():
            if key in d:
                d[key] = d[key] + (target_val - d[key]) * 0.08
        return CSTRState(**{k: self._add_noise(v, k) for k, v in d.items()})
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/demo/test_data_generator.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
mkdir -p demos/chemical_process
git add demos/chemical_process/data_generator.py tests/demo/test_data_generator.py
git commit -m "feat(demo): add CSTR simulation data generator"
```

---

## Task 3: 场景 JSON 文件

**Files:**
- Create: `demos/chemical_process/scenarios/01_startup.json` ~ `06_recovery.json`

**Purpose:** 预计算的场景数据文件，可直接被 demo_runner 使用或单独测试。

- [ ] **Step 1: 编写场景生成脚本**

```python
# scripts/generate_scenarios.py
"""生成 CSTR 演示场景 JSON 文件。运行一次即可。"""
import json
import sys
sys.path.insert(0, ".")
from demos.chemical_process.data_generator import CSTRDataGenerator, CSTRState

gen = CSTRDataGenerator()
scenarios_dir = "demos/chemical_process/scenarios"

import os
os.makedirs(scenarios_dir, exist_ok=True)


def save_scenario(name: str, ticks: list):
    path = os.path.join(scenarios_dir, f"{name}.json")
    with open(path, "w") as f:
        json.dump(ticks, f, indent=2)
    print(f"  {name}: {len(ticks)} ticks → {path}")


def gen_startup():
    """01_startup: 30 ticks, temp 25→180°C"""
    state = CSTRState(25, 1, 3, 0, 0, 0, 0, 0)
    ticks = []
    for i in range(30):
        progress = i / 29
        state = gen.startup_tick(state, 180.0, progress)
        ticks.append({"timestamp": round(i * 1.0, 1), "values": state.to_dict(), "interval_ms": 1000})
    return ticks


def gen_steady():
    """02_steady_state: 60 ticks, 全部在目标值波动"""
    state = CSTRState(180, 12, 1.8, 1.2, 50, 100, 300, 2.0)
    ticks = []
    for i in range(60):
        state = gen.normal_tick(state)
        ticks.append({"timestamp": round(30 + i * 1.0, 1), "values": state.to_dict(), "interval_ms": 1000})
    return ticks


def gen_drift():
    """03_sensor_drift: 30 ticks, temperature 传感器漂移"""
    state = CSTRState(180, 12, 1.8, 1.2, 50, 100, 300, 2.0)
    ticks = []
    for i in range(30):
        state = gen.drift_tick(state, "temperature", 0.5)
        ticks.append({"timestamp": round(90 + i * 1.0, 1), "values": state.to_dict(), "interval_ms": 1000})
    return ticks


def gen_spike():
    """04_temperature_spike: 20 ticks, coolant 下降, temp 升到 260°C"""
    state = CSTRState(195, 13, 1.5, 1.5, 50, 100, 300, 2.5)
    ticks = []
    for i in range(20):
        state = gen.emergency_tick(state, target_temp=260.0)
        ticks.append({"timestamp": round(120 + i * 1.0, 1), "values": state.to_dict(), "interval_ms": 1000})
    return ticks


def gen_emergency():
    """05_emergency: 10 ticks, temp 突破 280°C"""
    state = CSTRState(260, 18, 1.2, 1.8, 40, 15, 250, 3.5)
    ticks = []
    for i in range(10):
        state = gen.emergency_tick(state, target_temp=300.0)
        ticks.append({"timestamp": round(140 + i * 1.0, 1), "values": state.to_dict(), "interval_ms": 1000})
    return ticks


def gen_recovery():
    """06_recovery: 30 ticks, 回落到安全状态"""
    state = CSTRState(280, 20, 1.0, 2.0, 0, 200, 0, 1.0)
    target = {"temperature": 50.0, "pressure": 1.0, "flow_rate_in": 0.0}
    ticks = []
    for i in range(30):
        state = gen.recovery_tick(state, target)
        ticks.append({"timestamp": round(150 + i * 1.0, 1), "values": state.to_dict(), "interval_ms": 1000})
    return ticks


if __name__ == "__main__":
    print("生成 CSTR 演示场景...")
    save_scenario("01_startup", gen_startup())
    save_scenario("02_steady_state", gen_steady())
    save_scenario("03_sensor_drift", gen_drift())
    save_scenario("04_temperature_spike", gen_spike())
    save_scenario("05_emergency", gen_emergency())
    save_scenario("06_recovery", gen_recovery())
    print("完成!")
```

- [ ] **Step 2: 运行生成脚本**

```bash
python scripts/generate_scenarios.py
```

- [ ] **Step 3: Commit**

```bash
git add demos/chemical_process/scenarios/ scripts/generate_scenarios.py
git commit -m "feat(demo): add 6 CSTR scenario JSON files"
```

---

## Task 4: API 客户端与演示脚本

**Files:**
- Create: `demos/chemical_process/api_client.py`
- Create: `demos/chemical_process/demo_runner.py`
- Create: `demos/chemical_process/README.md`

**Purpose:** 通过 REST API 推送场景数据，驱动完整六阶段演示。

- [ ] **Step 1: 实现 API 客户端**

```python
# demos/chemical_process/api_client.py
from __future__ import annotations

import json
from pathlib import Path

import httpx


class APIClient:
    """Polymorphic-Twin API 客户端。"""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def upload_domain_pack(self, yaml_path: str) -> str:
        content = Path(yaml_path).read_text()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/domain-packs/",
                headers=self.headers,
                json={"format": "yaml", "content": content},
            )
            resp.raise_for_status()
            return resp.json()["pack_id"]

    async def create_twin(self, name: str, domain_pack_id: str, initial_state: dict) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/twins/",
                headers=self.headers,
                json={
                    "name": name,
                    "domain_pack_id": domain_pack_id,
                    "initial_state": initial_state,
                },
            )
            resp.raise_for_status()
            return resp.json()["twin_id"]

    async def update_state(self, twin_id: str, values: dict) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/api/v1/twins/{twin_id}/state/",
                headers=self.headers,
                json=values,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_constraint_status(self, twin_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/twins/{twin_id}/constraints/",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()
```

- [ ] **Step 2: 实现演示脚本**

```python
#!/usr/bin/env python3
# demos/chemical_process/demo_runner.py
"""CSTR 六阶段完整演示脚本。"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from demos.chemical_process.api_client import APIClient

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
SCENARIO_FILES = [
    ("01_startup", "启动升温"),
    ("02_steady_state", "稳态运行"),
    ("03_sensor_drift", "传感器漂移"),
    ("04_temperature_spike", "温度飙升"),
    ("05_emergency", "紧急工况"),
    ("06_recovery", "恢复"),
]


async def run_demo(api_url: str, api_key: str) -> None:
    client = APIClient(api_url, api_key)

    # Phase 0: 准备
    print("=" * 60)
    print("Polymorphic-Twin CSTR 演示")
    print("=" * 60)

    print("\n[Phase 0] 准备环境...")
    pack_id = await client.upload_domain_pack("configs/examples/cstr-standard.yaml")
    print(f"  DomainPack: {pack_id}")

    twin_id = await client.create_twin(
        "CSTR-Demo-001", pack_id,
        initial_state={"temperature": 25.0, "pressure": 1.0, "concentration_A": 3.0,
                       "concentration_B": 0.0, "flow_rate_in": 0.0, "coolant_flow": 0.0,
                       "agitator_speed": 0.0, "reaction_rate": 0.0},
    )
    print(f"  TwinObject: {twin_id}")

    # Phase 1-6: 运行场景
    for scenario_file, scenario_name in SCENARIO_FILES:
        path = SCENARIOS_DIR / f"{scenario_file}.json"
        if not path.exists():
            print(f"\n[跳过] {scenario_name}: 文件不存在 {path}")
            continue

        ticks = json.loads(path.read_text())
        print(f"\n[Phase] {scenario_name} ({len(ticks)} ticks)")

        fallback_triggered = False
        for tick in ticks:
            result = await client.update_state(twin_id, tick["values"])
            status = result.get("safety_status", "unknown")
            temp = tick["values"].get("temperature", 0)
            print(f"  {tick['timestamp']:6.1f}s  temp={temp:6.1f}°C  → {status}")

            if status == "fallback_triggered" and not fallback_triggered:
                fallback_triggered = True
                fb = result.get("fallback_action", "?")
                ms = result.get("fallback_duration_ms", "?")
                print(f"  ⚠ 安全回落触发: {fb} ({ms}ms)")

            interval = tick.get("interval_ms", 1000) / 1000.0
            await asyncio.sleep(min(interval, 0.1))  # 演示时加速

    # 总结
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


def main():
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "ptw_admin_key"
    asyncio.run(run_demo(api_url, api_key))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 编写 README**

```markdown
# CSTR 化学工艺演示

## 快速开始

```bash
# 1. 启动 API 服务
docker-compose up -d

# 2. 运行演示
python demos/chemical_process/demo_runner.py http://localhost:8000 ptw_admin_key

# 3. 打开可视化面板
open demos/chemical_process/dashboard/index.html
```

## 六阶段演示

| 阶段 | 时长 | 描述 |
|------|------|------|
| 启动 | 30s | 温度 25→180°C |
| 稳态 | 60s | 全部参数在目标值波动 |
| 漂移 | 30s | 温度传感器逐渐偏离 |
| 飙升 | 20s | 冷却水故障，温度升至 260°C |
| 紧急 | 10s | 温度突破 280°C，触发安全回落 |
| 恢复 | 30s | 系统逐步恢复到安全状态 |
```

- [ ] **Step 4: Commit**

```bash
git add demos/chemical_process/api_client.py demos/chemical_process/demo_runner.py demos/chemical_process/README.md
git commit -m "feat(demo): add API client and demo runner script"
```

---

## Task 5: 端到端集成测试

**Files:**
- Create: `tests/demo/test_demo_e2e.py`

**Purpose:** 验证演示流程的数据完整性和一致性。

- [ ] **Step 1: 编写 E2E 测试**

```python
# tests/demo/test_demo_e2e.py
"""端到端演示验证测试。

注意：这些测试需要 API 服务运行。在 CI 中通过 docker-compose 启动。
本地可通过 pytest --skip-e2e 跳过。
"""

import json
import os
from pathlib import Path

import pytest

SCENARIOS_DIR = Path("demos/chemical_process/scenarios")

skip_e2e = pytest.mark.skipif(
    os.environ.get("SKIP_E2E") == "1",
    reason="E2E tests skipped (SKIP_E2E=1)",
)


class TestScenarioData:
    """不需要 API 服务的场景数据验证。"""

    @pytest.mark.parametrize("filename", [
        "01_startup", "02_steady_state", "03_sensor_drift",
        "04_temperature_spike", "05_emergency", "06_recovery",
    ])
    def test_scenario_file_exists(self, filename):
        path = SCENARIOS_DIR / f"{filename}.json"
        assert path.exists(), f"Scenario file missing: {path}"

    @pytest.mark.parametrize("filename", [
        "01_startup", "02_steady_state", "03_sensor_drift",
        "04_temperature_spike", "05_emergency", "06_recovery",
    ])
    def test_scenario_valid_json(self, filename):
        path = SCENARIOS_DIR / f"{filename}.json"
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.parametrize("filename", [
        "01_startup", "02_steady_state", "03_sensor_drift",
        "04_temperature_spike", "05_emergency", "06_recovery",
    ])
    def test_scenario_tick_structure(self, filename):
        path = SCENARIOS_DIR / f"{filename}.json"
        data = json.loads(path.read_text())
        for tick in data:
            assert "timestamp" in tick
            assert "values" in tick
            assert "temperature" in tick["values"]

    def test_startup_starts_cold(self):
        path = SCENARIOS_DIR / "01_startup.json"
        data = json.loads(path.read_text())
        assert data[0]["values"]["temperature"] < 50

    def test_emergency_exceeds_280(self):
        path = SCENARIOS_DIR / "05_emergency.json"
        data = json.loads(path.read_text())
        max_temp = max(t["values"]["temperature"] for t in data)
        assert max_temp >= 280, f"Emergency scenario max temp only {max_temp}"

    def test_recovery_ends_below_200(self):
        path = SCENARIOS_DIR / "06_recovery.json"
        data = json.loads(path.read_text())
        final_temp = data[-1]["values"]["temperature"]
        assert final_temp < 200, f"Recovery final temp {final_temp}, expected < 200"


class TestDataGenerator:
    """验证数据生成器可独立运行。"""

    def test_import_generator(self):
        from demos.chemical_process.data_generator import CSTRDataGenerator, CSTRState
        gen = CSTRDataGenerator()
        assert gen is not None

    def test_import_api_client(self):
        from demos.chemical_process.api_client import APIClient
        client = APIClient("http://localhost:8000", "test_key")
        assert client is not None
```

- [ ] **Step 2: 运行测试确认通过**

```bash
pytest tests/demo/test_demo_e2e.py -v
```

Expected: ~14 passed

- [ ] **Step 3: Commit**

```bash
git add tests/demo/test_demo_e2e.py
git commit -m "test(demo): add scenario data validation and e2e tests"
```

---

## Quality Gate Checklist

- [ ] `configs/examples/cstr-standard.yaml` 可被引擎加载
- [ ] 数据生成器 5 种 tick 方法全部有测试
- [ ] 6 个场景 JSON 文件格式正确、温度数据合理
- [ ] `python demos/chemical_process/demo_runner.py --help` 不报错
- [ ] `pytest tests/demo/ -v` 全部通过
