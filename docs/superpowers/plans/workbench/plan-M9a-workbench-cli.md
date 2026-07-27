# M9a: DomainPack Workbench — CLI 框架与校验

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 `ptw` CLI 工具框架，实现 init、templates、validate 命令，让域专家可以创建和校验 DomainPack。

**Architecture:** Click CLI 框架 + Rich 终端输出。CLI 直接调用 SDK（不经过 API 服务）。校验流水线分三级：syntax → semantic → compatibility，可独立运行也可级联。

**Spec reference:** `docs/superpowers/specs/2026-05-07-product-workbench.md` v1.0.0 §2

**Quality gate:**
- `ptw version` 输出版本号
- `ptw workbench templates` 列出 3 个模板
- `ptw workbench init --template chemical-process --name test` 生成可校验通过的 YAML
- `ptw workbench validate` 正确检测 5 种典型错误

**Depends on:** plan-M8-sdk-packaging.md (SDK 必须可 import)

---

## File Structure

```
polymorphic_twin/
├── workbench/
│   ├── __init__.py
│   ├── cli.py                     # Task 1: CLI 入口
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── init.py                # Task 3
│   │   ├── templates.py           # Task 2
│   │   └── validate.py            # Task 6
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── pipeline.py            # Task 4
│   │   ├── syntax_checker.py      # Task 4
│   │   ├── semantic_checker.py    # Task 5
│   │   └── compatibility_checker.py # Task 5
│   └── templates/                 # Task 3
│       ├── chemical-process.yaml
│       ├── robot.yaml
│       └── minimal.yaml
└── tests/workbench/
    └── unit/
        ├── test_cli.py
        ├── test_templates_cmd.py
        ├── test_init_cmd.py
        ├── test_syntax_checker.py
        ├── test_semantic_checker.py
        └── test_validate_cmd.py
```

---

## Task 1: CLI 框架与 version 命令

**Files:**
- Create: `polymorphic_twin/workbench/__init__.py`
- Create: `polymorphic_twin/workbench/cli.py`
- Create: `tests/workbench/unit/test_cli.py`

**Purpose:** 搭建 Click CLI 骨架，`ptw version` 和 `ptw --help` 可用。

- [ ] **Step 1: 编写 CLI 测试**

```python
# tests/workbench/unit/test_cli.py
from click.testing import CliRunner
from polymorphic_twin.workbench.cli import main


def test_version_command():
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help_shows_workbench_group():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "workbench" in result.output


def test_workbench_help_shows_commands():
    runner = CliRunner()
    result = runner.invoke(main, ["workbench", "--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "validate" in result.output
    assert "templates" in result.output
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/workbench/unit/test_cli.py -v
```

- [ ] **Step 3: 实现 CLI**

```python
# polymorphic_twin/workbench/__init__.py
```

```python
# polymorphic_twin/workbench/cli.py
import click

VERSION = "0.1.0"


@click.group()
def main() -> None:
    """Polymorphic-Twin CLI — 数字孪生治理工具。"""


@main.command()
def version() -> None:
    """显示版本信息。"""
    click.echo(f"polymorphic-twin {VERSION}")


@main.group()
def workbench() -> None:
    """DomainPack 工作台：创建、校验、模拟。"""


# 命令在各自模块中定义后注册
# Task 2-6 中逐个添加


def entry_point() -> None:
    """pyproject.toml 中的 console_scripts 入口。"""
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/workbench/unit/test_cli.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/workbench/__init__.py polymorphic_twin/workbench/cli.py tests/workbench/unit/test_cli.py
git commit -m "feat(workbench): add CLI framework with version command"
```

---

## Task 2: Templates 命令

**Files:**
- Create: `polymorphic_twin/workbench/commands/__init__.py`
- Create: `polymorphic_twin/workbench/commands/templates.py`
- Create: `polymorphic_twin/workbench/templates/__init__.py` (占位)
- Create: `tests/workbench/unit/test_templates_cmd.py`

**Purpose:** `ptw workbench templates` 列出内置模板。

- [ ] **Step 1: 编写测试**

```python
# tests/workbench/unit/test_templates_cmd.py
from click.testing import CliRunner
from polymorphic_twin.workbench.cli import main


def test_templates_lists_all():
    runner = CliRunner()
    result = runner.invoke(main, ["workbench", "templates"])
    assert result.exit_code == 0
    assert "chemical-process" in result.output
    assert "robot" in result.output
    assert "minimal" in result.output


def test_templates_shows_descriptions():
    runner = CliRunner()
    result = runner.invoke(main, ["workbench", "templates"])
    assert "CSTR" in result.output or "化学" in result.output or "chemical" in result.output.lower()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/workbench/unit/test_templates_cmd.py -v
```

- [ ] **Step 3: 实现 templates 命令**

```python
# polymorphic_twin/workbench/commands/__init__.py
```

```python
# polymorphic_twin/workbench/commands/templates.py
import click

TEMPLATES = {
    "chemical-process": "化学工艺优化（CSTR反应器）",
    "robot": "机器人运动控制（6轴机械臂）",
    "minimal": "最小示例（设备监控）",
}


@click.command()
def templates() -> None:
    """列出可用的 DomainPack 模板。"""
    click.echo("可用模板:\n")
    for name, desc in TEMPLATES.items():
        click.echo(f"  {name:<20s} {desc}")
```

- [ ] **Step 4: 在 cli.py 中注册命令**

```python
# 在 cli.py 中添加 import 和注册
from polymorphic_twin.workbench.commands.templates import templates as templates_cmd

# 在 workbench group 定义后添加:
workbench.add_command(templates_cmd, "templates")
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/workbench/unit/test_templates_cmd.py -v
```

- [ ] **Step 6: 创建模板占位目录**

```bash
mkdir -p polymorphic_twin/workbench/templates
touch polymorphic_twin/workbench/templates/__init__.py
```

- [ ] **Step 7: Commit**

```bash
git add polymorphic_twin/workbench/commands/ polymorphic_twin/workbench/templates/ tests/workbench/unit/test_templates_cmd.py
git commit -m "feat(workbench): add templates command"
```

---

## Task 3: Init 命令与模板文件

**Files:**
- Create: `polymorphic_twin/workbench/commands/init.py`
- Create: `polymorphic_twin/workbench/templates/chemical-process.yaml`
- Create: `polymorphic_twin/workbench/templates/robot.yaml`
- Create: `polymorphic_twin/workbench/templates/minimal.yaml`
- Create: `tests/workbench/unit/test_init_cmd.py`

**Purpose:** `ptw workbench init --template <name> --name <name>` 从模板创建 DomainPack YAML。

- [ ] **Step 1: 编写测试**

```python
# tests/workbench/unit/test_init_cmd.py
import os
import tempfile
from click.testing import CliRunner
from polymorphic_twin.workbench.cli import main


def test_init_creates_yaml():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, [
            "workbench", "init",
            "--template", "minimal",
            "--name", "test-device",
        ])
        assert result.exit_code == 0
        assert os.path.exists("test-device.yaml")


def test_init_yaml_has_correct_name():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, [
            "workbench", "init",
            "--template", "minimal",
            "--name", "my-sensor",
        ])
        with open("my-sensor.yaml") as f:
            content = f.read()
        assert "my-sensor" in content


def test_init_custom_output_path():
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.makedirs("output", exist_ok=True)
        result = runner.invoke(main, [
            "workbench", "init",
            "--template", "minimal",
            "--name", "test",
            "--output", "output/custom.yaml",
        ])
        assert result.exit_code == 0
        assert os.path.exists("output/custom.yaml")


def test_init_invalid_template():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, [
            "workbench", "init",
            "--template", "nonexistent",
            "--name", "test",
        ])
        assert result.exit_code != 0
```

- [ ] **Step 2: 编写最小模板 YAML**

```yaml
# polymorphic_twin/workbench/templates/minimal.yaml
domain_id: "{{DOMAIN_ID}}"
domain_name: "{{NAME}}"
domain_version: "0.1.0"

inheritance_policy:
  can_relax_parent_absolute_constraints: false
  can_lower_parent_criticality: false
  conflict_resolution: "stricter_wins"

state_variables:
  - name: "temperature"
    unit: "°C"
    physical_range: [0, 500]
    observable: true
    controllable: true
    description: "设备温度"
  - name: "pressure"
    unit: "atm"
    physical_range: [0, 100]
    observable: true
    controllable: true
    description: "设备压力"
  - name: "status"
    unit: ""
    physical_range: [0, 3]
    observable: true
    controllable: false
    description: "运行状态"

constraints:
  - id: "max_temperature"
    description: "温度安全上限"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "temperature"
      operator: "<="
      threshold: 400.0
  - id: "max_pressure"
    description: "压力安全上限"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "pressure"
      operator: "<="
      threshold: 80.0
  - id: "operational_range"
    description: "正常运行范围"
    criticality: "operational"
    rigidity: "soft"
    certifier:
      type: "threshold"
      variable: "temperature"
      operator: "<="
      threshold: 300.0

fallback_strategy:
  name: "safe_shutdown"
  trigger: "any safety_critical constraint violation"
  steps:
    - action: "reduce_temperature"
      target_variable: "temperature"
      set_value: 25.0
      order: 1
  target_state:
    temperature: 25.0
    pressure: 1.0
  timeout_ms: 200

action_templates: []
human_roles: []
```

- [ ] **Step 3: 编写 chemical-process 模板**

```yaml
# polymorphic_twin/workbench/templates/chemical-process.yaml
# CSTR DomainPack 模板（简化版，5 约束）— init 命令起步用
# 完整生产版（8 约束 + identity invariants）见 configs/examples/cstr-standard.yaml（M11a canonical source）
# 占位符: {{DOMAIN_ID}}, {{NAME}}

domain_id: "{{DOMAIN_ID}}"
domain_name: "{{NAME}}"
domain_version: "0.1.0"
description: "CSTR连续搅拌釜反应器 — 从模板创建"

inheritance_policy:
  can_relax_parent_absolute_constraints: false
  can_lower_parent_criticality: false
  conflict_resolution: "stricter_wins"

state_variables:
  - name: "temperature"
    unit: "°C"
    physical_range: [20, 350]
    observable: true
    controllable: true
  - name: "pressure"
    unit: "atm"
    physical_range: [0.5, 50]
    observable: true
    controllable: true
  - name: "concentration_A"
    unit: "mol/L"
    physical_range: [0, 5]
    observable: true
    controllable: false
  - name: "concentration_B"
    unit: "mol/L"
    physical_range: [0, 5]
    observable: true
    controllable: false
  - name: "flow_rate_in"
    unit: "L/min"
    physical_range: [0, 100]
    observable: true
    controllable: true
  - name: "coolant_flow"
    unit: "L/min"
    physical_range: [0, 200]
    observable: true
    controllable: true
  - name: "agitator_speed"
    unit: "RPM"
    physical_range: [0, 500]
    observable: true
    controllable: true
  - name: "reaction_rate"
    unit: "mol/(L·min)"
    physical_range: [0, 10]
    observable: true
    controllable: false

constraints:
  - id: "max_temperature"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "temperature"
      operator: "<="
      threshold: 280.0
  - id: "max_pressure"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "pressure"
      operator: "<="
      threshold: 45.0
  - id: "min_coolant_flow"
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
  - id: "agitator_integrity"
    criticality: "operational"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "agitator_speed"
      operator: "<="
      threshold: 450.0
  - id: "reaction_efficiency"
    criticality: "operational"
    rigidity: "soft"
    certifier:
      type: "custom"
      expression: "concentration_B / (concentration_A + concentration_B) >= 0.7"

fallback_strategy:
  name: "emergency_shutdown"
  trigger: "any safety_critical constraint violation"
  steps:
    - action: "close_feed"
      target_variable: "flow_rate_in"
      set_value: 0
      order: 1
    - action: "max_coolant"
      target_variable: "coolant_flow"
      set_value: 200
      order: 2
    - action: "stop_agitator"
      target_variable: "agitator_speed"
      set_value: 0
      order: 3
  target_state:
    temperature: 50.0
    pressure: 1.0
  timeout_ms: 200

action_templates: []
human_roles: []
```

- [ ] **Step 4: 编写 robot 模板**

```yaml
# polymorphic_twin/workbench/templates/robot.yaml
domain_id: "{{DOMAIN_ID}}"
domain_name: "{{NAME}}"
domain_version: "0.1.0"
description: "6轴机械臂运动控制"

inheritance_policy:
  can_relax_parent_absolute_constraints: false
  can_lower_parent_criticality: false
  conflict_resolution: "stricter_wins"

state_variables:
  - name: "joint_1_angle"
    unit: "°"
    physical_range: [-180, 180]
    observable: true
    controllable: true
  - name: "joint_2_angle"
    unit: "°"
    physical_range: [-180, 180]
    observable: true
    controllable: true
  - name: "joint_3_angle"
    unit: "°"
    physical_range: [-180, 180]
    observable: true
    controllable: true
  - name: "payload_weight"
    unit: "kg"
    physical_range: [0, 50]
    observable: true
    controllable: false
  - name: "speed"
    unit: "m/s"
    physical_range: [0, 5]
    observable: true
    controllable: true
  - name: "torque"
    unit: "N·m"
    physical_range: [0, 200]
    observable: true
    controllable: false

constraints:
  - id: "max_torque"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "torque"
      operator: "<="
      threshold: 150.0
  - id: "max_speed"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "speed"
      operator: "<="
      threshold: 3.0
  - id: "max_payload"
    criticality: "safety_critical"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "payload_weight"
      operator: "<="
      threshold: 40.0
  - id: "joint_1_range"
    criticality: "operational"
    rigidity: "absolute"
    certifier:
      type: "threshold"
      variable: "joint_1_angle"
      operator: "<="
      threshold: 170.0
  - id: "energy_efficiency"
    criticality: "operational"
    rigidity: "soft"
    certifier:
      type: "custom"
      expression: "torque * speed < 200"
  - id: "smooth_motion"
    criticality: "operational"
    rigidity: "learnable"
    certifier:
      type: "learnable"
      target_metric: "speed"
      optimization: "maximize"

fallback_strategy:
  name: "emergency_stop"
  trigger: "any safety_critical constraint violation"
  steps:
    - action: "stop_motion"
      target_variable: "speed"
      set_value: 0
      order: 1
  target_state:
    speed: 0.0
  timeout_ms: 200

action_templates: []
human_roles: []
```

- [ ] **Step 5: 实现 init 命令**

```python
# polymorphic_twin/workbench/commands/init.py
from __future__ import annotations

import shutil
from pathlib import Path

import click

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
AVAILABLE_TEMPLATES = ["chemical-process", "robot", "minimal"]


@click.command()
@click.option("--template", required=True, type=click.Choice(AVAILABLE_TEMPLATES),
              help="模板名称")
@click.option("--name", required=True, help="DomainPack 名称")
@click.option("--output", default=None, help="输出路径（默认 ./<name>.yaml）")
def init(template: str, name: str, output: str | None) -> None:
    """从模板创建新 DomainPack。"""
    template_path = TEMPLATES_DIR / f"{template}.yaml"
    if not template_path.exists():
        msg = f"模板文件不存在: {template_path}"
        raise click.ClickException(msg)

    content = template_path.read_text(encoding="utf-8")
    # 替换占位符
    domain_id = name.lower().replace(" ", "_").replace("-", "_")
    content = content.replace("{{DOMAIN_ID}}", domain_id)
    content = content.replace("{{NAME}}", name)

    output_path = Path(output) if output else Path(f"./{domain_id}.yaml")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    click.secho(f"✓ DomainPack 已创建: {output_path}", fg="green")
    click.echo(f"  模板: {template}")
    click.echo(f"  下一步: 编辑 {output_path} 然后运行 ptw workbench validate {output_path}")
```

- [ ] **Step 6: 在 cli.py 中注册 init 命令**

```python
# cli.py 中添加
from polymorphic_twin.workbench.commands.init import init as init_cmd
workbench.add_command(init_cmd, "init")
```

- [ ] **Step 7: 运行测试确认通过**

```bash
pytest tests/workbench/unit/test_init_cmd.py -v
```

Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add polymorphic_twin/workbench/commands/init.py polymorphic_twin/workbench/templates/ tests/workbench/unit/test_init_cmd.py
git commit -m "feat(workbench): add init command with 3 templates"
```

---

## Task 4: 校验流水线 — Syntax 检查

**Files:**
- Create: `polymorphic_twin/workbench/validation/__init__.py`
- Create: `polymorphic_twin/workbench/validation/syntax_checker.py`
- Create: `polymorphic_twin/workbench/validation/pipeline.py`
- Create: `tests/workbench/unit/test_syntax_checker.py`

**Purpose:** YAML 解析和 Schema 基本结构校验。

- [ ] **Step 1: 编写语法校验测试**

```python
# tests/workbench/unit/test_syntax_checker.py
import pytest
import tempfile
from pathlib import Path
from polymorphic_twin.workbench.validation.syntax_checker import SyntaxChecker


@pytest.fixture
def checker():
    return SyntaxChecker()


def _write_yaml(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def test_valid_yaml_passes(checker):
    path = _write_yaml("domain_id: test\nstate_variables: []\n")
    results = checker.check(path)
    assert all(r.result == "pass" for r in results)


def test_invalid_yaml_fails(checker):
    path = _write_yaml("domain_id: test\n  bad indent: [\n")
    results = checker.check(path)
    assert any(r.result == "fail" for r in results)


def test_missing_required_field(checker):
    yaml_content = "domain_id: test\n"
    path = _write_yaml(yaml_content)
    results = checker.check(path)
    # state_variables 和 constraints 和 fallback_strategy 缺失
    failed = [r for r in results if r.result == "fail"]
    assert len(failed) >= 2


def test_nonexistent_file_fails(checker):
    results = checker.check(Path("/nonexistent/file.yaml"))
    assert any(r.result == "fail" for r in results)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/workbench/unit/test_syntax_checker.py -v
```

- [ ] **Step 3: 实现 SyntaxChecker**

```python
# polymorphic_twin/workbench/validation/__init__.py
```

```python
# polymorphic_twin/workbench/validation/syntax_checker.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class CheckResult:
    category: str
    result: str  # "pass" | "fail" | "warn"
    message: str
    fix_suggestion: str | None = None


REQUIRED_FIELDS = [
    "domain_id",
    "domain_name",
    "domain_version",
    "state_variables",
    "constraints",
    "fallback_strategy",
]


class SyntaxChecker:
    """语法级校验：YAML 解析 + 必填字段检查。"""

    def check(self, path: Path) -> list[CheckResult]:
        results: list[CheckResult] = []

        # 检查 1: 文件存在
        if not path.exists():
            return [CheckResult("file", "fail", f"文件不存在: {path}")]

        # 检查 2: YAML 解析
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return [CheckResult("syntax", "fail", f"YAML 解析错误: {e}",
                                fix_suggestion="检查缩进和语法")]

        results.append(CheckResult("syntax", "pass", "YAML 解析正确"))

        # 检查 3: 必填字段
        for field_name in REQUIRED_FIELDS:
            if field_name not in data:
                results.append(CheckResult(
                    "schema", "fail",
                    f"缺少必填字段: {field_name}",
                    fix_suggestion=f"在 DomainPack 中添加 {field_name} 字段",
                ))
            else:
                results.append(CheckResult("schema", "pass", f"字段存在: {field_name}"))

        return results
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/workbench/unit/test_syntax_checker.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/workbench/validation/ tests/workbench/unit/test_syntax_checker.py
git commit -m "feat(workbench): add syntax validation checker"
```

---

## Task 5: 校验流水线 — Semantic + Compatibility 检查

**Files:**
- Create: `polymorphic_twin/workbench/validation/semantic_checker.py`
- Create: `polymorphic_twin/workbench/validation/compatibility_checker.py`
- Create: `tests/workbench/unit/test_semantic_checker.py`

**Purpose:** 引用完整性检查（约束引用的状态变量是否存在）和刚性-关键性兼容性检查。

- [ ] **Step 1: 编写语义校验测试**

```python
# tests/workbench/unit/test_semantic_checker.py
import pytest
import tempfile
from pathlib import Path
import yaml
from polymorphic_twin.workbench.validation.semantic_checker import SemanticChecker
from polymorphic_twin.workbench.validation.compatibility_checker import CompatibilityChecker


def _write_pack(data: dict) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, f)
    f.close()
    return Path(f.name)


VALID_PACK = {
    "domain_id": "test",
    "state_variables": [
        {"name": "temperature", "unit": "°C", "physical_range": [0, 500],
         "observable": True, "controllable": True},
    ],
    "constraints": [
        {"id": "max_temp", "criticality": "safety_critical", "rigidity": "absolute",
         "certifier": {"type": "threshold", "variable": "temperature", "operator": "<=", "threshold": 400}},
    ],
    "fallback_strategy": {"name": "shutdown", "steps": [], "target_state": {}, "timeout_ms": 200},
}


class TestSemanticChecker:
    def test_valid_pack_passes(self):
        path = _write_pack(VALID_PACK)
        checker = SemanticChecker()
        results = checker.check(path)
        assert all(r.result == "pass" for r in results)

    def test_constraint_references_unknown_variable(self):
        pack = {
            **VALID_PACK,
            "constraints": [
                {"id": "bad_ref", "criticality": "safety_critical", "rigidity": "absolute",
                 "certifier": {"type": "threshold", "variable": "nonexistent", "operator": "<=", "threshold": 100}},
            ],
        }
        path = _write_pack(pack)
        checker = SemanticChecker()
        results = checker.check(path)
        failed = [r for r in results if r.result == "fail"]
        assert len(failed) >= 1
        assert "nonexistent" in failed[0].message

    def test_fallback_missing_timeout(self):
        pack = {
            **VALID_PACK,
            "fallback_strategy": {"name": "shutdown", "steps": [], "target_state": {}},
        }
        path = _write_pack(pack)
        checker = SemanticChecker()
        results = checker.check(path)
        failed = [r for r in results if r.result == "fail"]
        assert any("timeout" in r.message.lower() for r in failed)


class TestCompatibilityChecker:
    def test_safety_critical_absolute_passes(self):
        path = _write_pack(VALID_PACK)
        checker = CompatibilityChecker()
        results = checker.check(path)
        assert all(r.result == "pass" for r in results)

    def test_safety_critical_soft_fails(self):
        pack = {
            **VALID_PACK,
            "constraints": [
                {"id": "max_temp", "criticality": "safety_critical", "rigidity": "soft",
                 "certifier": {"type": "threshold", "variable": "temperature", "operator": "<=", "threshold": 400}},
            ],
        }
        path = _write_pack(pack)
        checker = CompatibilityChecker()
        results = checker.check(path)
        failed = [r for r in results if r.result == "fail"]
        assert len(failed) == 1
        assert "safety_critical" in failed[0].message
        assert "absolute" in failed[0].message

    def test_operational_any_rigidity_passes(self):
        for rigidity in ["absolute", "soft", "learnable"]:
            pack = {
                **VALID_PACK,
                "constraints": [
                    {"id": "op", "criticality": "operational", "rigidity": rigidity,
                     "certifier": {"type": "threshold", "variable": "temperature", "operator": "<=", "threshold": 400}},
                ],
            }
            path = _write_pack(pack)
            checker = CompatibilityChecker()
            results = checker.check(path)
            assert all(r.result == "pass" for r in results), f"Failed for rigidity={rigidity}"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/workbench/unit/test_semantic_checker.py -v
```

- [ ] **Step 3: 实现 SemanticChecker**

```python
# polymorphic_twin/workbench/validation/semantic_checker.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class CheckResult:
    category: str
    result: str
    message: str
    fix_suggestion: str | None = None


class SemanticChecker:
    """语义级校验：引用完整性、fallback 完整性。"""

    def check(self, path: Path) -> list[CheckResult]:
        results: list[CheckResult] = []
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        var_names = {v["name"] for v in data.get("state_variables", [])}

        # 检查约束引用的状态变量
        for c in data.get("constraints", []):
            certifier = c.get("certifier", {})
            var = certifier.get("variable")
            if var and var not in var_names:
                results.append(CheckResult(
                    "reference", "fail",
                    f"约束 {c.get('id', '?')} 引用了未定义的状态变量: {var}",
                    fix_suggestion=f"在 state_variables 中添加 {var} 或修改约束引用",
                ))

        # 检查 domain_of_validity 引用
        for c in data.get("constraints", []):
            dov = c.get("domain_of_validity", {})
            for cond in dov.get("conditions", []):
                var = cond.get("variable")
                if var and var not in var_names:
                    results.append(CheckResult(
                        "reference", "fail",
                        f"约束 {c.get('id', '?')} 适用域引用了未定义变量: {var}",
                    ))

        # 检查 fallback 完整性
        fallback = data.get("fallback_strategy", {})
        if "timeout_ms" not in fallback:
            results.append(CheckResult(
                "fallback", "fail",
                "安全回落策略缺少 timeout_ms 字段",
                fix_suggestion="在 fallback_strategy 中添加 timeout_ms",
            ))

        if not results:
            results.append(CheckResult("semantic", "pass", "语义校验通过"))

        return results
```

- [ ] **Step 4: 实现 CompatibilityChecker**

```python
# polymorphic_twin/workbench/validation/compatibility_checker.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class CheckResult:
    category: str
    result: str
    message: str
    fix_suggestion: str | None = None


# 刚性-关键性兼容规则（来自引擎 Spec）
COMPATIBILITY_RULES: dict[str, list[str]] = {
    "safety_critical": ["absolute"],
    "identity_critical": ["absolute", "learnable"],
    "operational": ["absolute", "soft", "learnable"],
    "informational": ["soft", "learnable"],
}


class CompatibilityChecker:
    """刚性-关键性兼容性校验。"""

    def check(self, path: Path) -> list[CheckResult]:
        results: list[CheckResult] = []
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for c in data.get("constraints", []):
            criticality = c.get("criticality", "")
            rigidity = c.get("rigidity", "")
            cid = c.get("id", "?")

            allowed = COMPATIBILITY_RULES.get(criticality, [])
            if allowed and rigidity not in allowed:
                results.append(CheckResult(
                    "compatibility", "fail",
                    f"约束 {cid}: {criticality} 不允许 {rigidity} 刚性"
                    f"（允许: {', '.join(allowed)}）",
                    fix_suggestion=f"将约束 {cid} 的 rigidity 改为 {allowed[0]}",
                ))

        if not results:
            results.append(CheckResult("compatibility", "pass", "刚性-关键性兼容检查通过"))

        return results
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/workbench/unit/test_semantic_checker.py -v
```

Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add polymorphic_twin/workbench/validation/semantic_checker.py polymorphic_twin/workbench/validation/compatibility_checker.py tests/workbench/unit/test_semantic_checker.py
git commit -m "feat(workbench): add semantic and compatibility validation checkers"
```

---

## Task 6: Validate 命令 — CLI 集成

**Files:**
- Create: `polymorphic_twin/workbench/validation/pipeline.py`
- Create: `polymorphic_twin/workbench/commands/validate.py`
- Create: `tests/workbench/unit/test_validate_cmd.py`

**Purpose:** `ptw workbench validate <file>` 命令整合三级校验，Rich 终端输出。

- [ ] **Step 1: 编写 validate 命令测试**

```python
# tests/workbench/unit/test_validate_cmd.py
import tempfile
from pathlib import Path
from click.testing import CliRunner
import yaml
from polymorphic_twin.workbench.cli import main


def _write_valid_pack() -> Path:
    data = {
        "domain_id": "test",
        "domain_name": "Test",
        "domain_version": "0.1.0",
        "state_variables": [
            {"name": "temp", "unit": "C", "physical_range": [0, 500],
             "observable": True, "controllable": True},
        ],
        "constraints": [
            {"id": "max_temp", "criticality": "safety_critical", "rigidity": "absolute",
             "certifier": {"type": "threshold", "variable": "temp", "operator": "<=", "threshold": 400}},
        ],
        "fallback_strategy": {"name": "stop", "steps": [], "target_state": {}, "timeout_ms": 200},
    }
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, f)
    f.close()
    return Path(f.name)


def test_validate_valid_pack():
    path = _write_valid_pack()
    runner = CliRunner()
    result = runner.invoke(main, ["workbench", "validate", str(path)])
    assert result.exit_code == 0
    assert "PASS" in result.output or "pass" in result.output.lower()


def test_validate_invalid_yaml():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write("bad: [\n  broken")
    f.close()
    runner = CliRunner()
    result = runner.invoke(main, ["workbench", "validate", f.name])
    assert "FAIL" in result.output or "fail" in result.output.lower()
```

- [ ] **Step 2: 实现校验流水线**

```python
# polymorphic_twin/workbench/validation/pipeline.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polymorphic_twin.workbench.validation.syntax_checker import (
    CheckResult,
    SyntaxChecker,
)
from polymorphic_twin.workbench.validation.semantic_checker import SemanticChecker
from polymorphic_twin.workbench.validation.compatibility_checker import CompatibilityChecker


@dataclass
class ValidationReport:
    file_path: str
    level: str
    checks: list[CheckResult]
    overall_result: str
    passed_count: int
    failed_count: int


class ValidationPipeline:
    """三级校验流水线。"""

    def __init__(self) -> None:
        self.syntax = SyntaxChecker()
        self.semantic = SemanticChecker()
        self.compatibility = CompatibilityChecker()

    def run(self, path: Path, level: str = "full") -> ValidationReport:
        all_checks: list[CheckResult] = []

        # Level 1: Syntax (always)
        all_checks.extend(self.syntax.check(path))

        # 如果 syntax 有失败且不是 full 级别，可以提前返回
        syntax_failed = any(c.result == "fail" and c.category == "syntax" for c in all_checks)
        if syntax_failed:
            return self._build_report(path, level, all_checks)

        if level in ("semantic", "full"):
            all_checks.extend(self.semantic.check(path))

        if level == "full":
            all_checks.extend(self.compatibility.check(path))

        return self._build_report(path, level, all_checks)

    def _build_report(self, path: Path, level: str, checks: list[CheckResult]) -> ValidationReport:
        passed = sum(1 for c in checks if c.result == "pass")
        failed = sum(1 for c in checks if c.result == "fail")
        overall = "PASS" if failed == 0 else "FAIL"
        return ValidationReport(
            file_path=str(path),
            level=level,
            checks=checks,
            overall_result=overall,
            passed_count=passed,
            failed_count=failed,
        )
```

- [ ] **Step 3: 实现 validate 命令**

```python
# polymorphic_twin/workbench/commands/validate.py
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from polymorphic_twin.workbench.validation.pipeline import ValidationPipeline


@click.command()
@click.argument("file_path", type=click.Path(exists=False))
@click.option("--level", type=click.Choice(["syntax", "semantic", "full"]),
              default="full", help="校验级别")
@click.option("--output", default=None, help="报告输出路径")
def validate(file_path: str, level: str, output: str | None) -> None:
    """校验 DomainPack 文件。"""
    path = Path(file_path)
    pipeline = ValidationPipeline()
    report = pipeline.run(path, level)

    console = Console()

    # 终端输出
    console.print(f"\n[bold]DomainPack 校验报告[/bold]")
    console.print(f"文件: {report.file_path}")
    console.print(f"级别: {report.level}\n")

    table = Table(show_header=True)
    table.add_column("状态", width=6)
    table.add_column("类别", width=15)
    table.add_column("信息")

    for check in report.checks:
        icon = "✓" if check.result == "pass" else "✗" if check.result == "fail" else "⚠"
        style = "green" if check.result == "pass" else "red" if check.result == "fail" else "yellow"
        table.add_row(f"[{style}]{icon}[/{style}]", check.category, check.message)

    console.print(table)
    console.print(f"\n结果: [bold {'green' if report.overall_result == 'PASS' else 'red'}]"
                  f"{report.overall_result}[/bold] "
                  f"({report.passed_count}/{report.passed_count + report.failed_count} 通过)")

    # Markdown 报告输出
    if output:
        _write_markdown_report(report, output)
        console.print(f"报告已保存: {output}")

    if report.overall_result == "FAIL":
        raise SystemExit(1)


def _write_markdown_report(report, output_path: str) -> None:
    lines = [
        f"# DomainPack 校验报告",
        f"",
        f"- 文件: `{report.file_path}`",
        f"- 级别: {report.level}",
        f"- 结果: **{report.overall_result}**",
        f"- 通过: {report.passed_count}/{report.passed_count + report.failed_count}",
        f"",
        f"## 检查明细",
        f"",
        f"| 状态 | 类别 | 信息 |",
        f"|------|------|------|",
    ]
    for check in report.checks:
        icon = "✓" if check.result == "pass" else "✗"
        lines.append(f"| {icon} | {check.category} | {check.message} |")
        if check.fix_suggestion:
            lines.append(f"| → | | _修复建议: {check.fix_suggestion}_ |")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 4: 在 cli.py 中注册 validate 命令**

```python
# cli.py 中添加
from polymorphic_twin.workbench.commands.validate import validate as validate_cmd
workbench.add_command(validate_cmd, "validate")
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/workbench/unit/test_validate_cmd.py -v
```

Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add polymorphic_twin/workbench/validation/pipeline.py polymorphic_twin/workbench/commands/validate.py tests/workbench/unit/test_validate_cmd.py
git commit -m "feat(workbench): add validate command with Rich output and pipeline"
```

---

## Task 7: `ptw domainpack` 子命令

**Files:**
- Create: `polymorphic_twin/workbench/commands/domainpack.py`
- Create: `tests/workbench/unit/test_domainpack_cmd.py`

**Purpose:** Spec §2.1 定义了 `ptw domainpack` 子命令组：load、list、show、validate。这些是直接操作引擎的快捷命令，不经过 API 服务。

- [ ] **Step 1: 编写测试**

```python
# tests/workbench/unit/test_domainpack_cmd.py
import tempfile
import yaml
from pathlib import Path
from click.testing import CliRunner
from polymorphic_twin.workbench.cli import main


def _write_pack() -> str:
    data = {
        "domain_id": "dp_test", "domain_name": "DP Test", "domain_version": "0.1.0",
        "state_variables": [
            {"name": "temp", "unit": "C", "physical_range": [0, 500],
             "observable": True, "controllable": True},
        ],
        "constraints": [
            {"id": "max_t", "criticality": "safety_critical", "rigidity": "absolute",
             "certifier": {"type": "threshold", "variable": "temp", "operator": "<=", "threshold": 400}},
        ],
        "fallback_strategy": {"name": "stop", "steps": [], "target_state": {}, "timeout_ms": 200},
    }
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, f)
    f.close()
    return f.name


def test_domainpack_validate():
    runner = CliRunner()
    result = runner.invoke(main, ["domainpack", "validate", _write_pack()])
    assert result.exit_code == 0


def test_domainpack_validate_invalid():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write("domain_id: test\n")
    f.close()
    runner = CliRunner()
    result = runner.invoke(main, ["domainpack", "validate", f.name])
    assert "FAIL" in result.output or result.exit_code != 0


def test_domainpack_help():
    runner = CliRunner()
    result = runner.invoke(main, ["domainpack", "--help"])
    assert result.exit_code == 0
    assert "validate" in result.output
```

- [ ] **Step 2: 实现 domainpack 命令组**

```python
# polymorphic_twin/workbench/commands/domainpack.py
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from polymorphic_twin.workbench.validation.pipeline import ValidationPipeline


@click.group()
def domainpack() -> None:
    """DomainPack 管理命令。"""


@domainpack.command()
@click.argument("file_path", type=click.Path(exists=False))
@click.option("--level", type=click.Choice(["syntax", "semantic", "full"]),
              default="full")
def validate(file_path: str, level: str) -> None:
    """独立校验 DomainPack（不启动引擎）。"""
    path = Path(file_path)
    pipeline = ValidationPipeline()
    report = pipeline.run(path, level)

    console = Console()
    passed = report.passed_count
    total = passed + report.failed_count
    icon = "✓" if report.overall_result == "PASS" else "✗"
    color = "green" if report.overall_result == "PASS" else "red"

    console.print(f"[{color}]{icon}[/{color}] {path.name}: "
                  f"{report.overall_result} ({passed}/{total})")

    for check in report.checks:
        if check.result == "fail":
            console.print(f"  ✗ {check.category}: {check.message}")
            if check.fix_suggestion:
                console.print(f"    → {check.fix_suggestion}", style="dim")

    if report.overall_result == "FAIL":
        raise SystemExit(1)


@domainpack.command()
def list_packs() -> None:
    """列出当前目录下的 DomainPack 文件。"""
    import glob
    console = Console()
    yaml_files = glob.glob("*.yaml") + glob.glob("*.yml")
    if not yaml_files:
        console.print("[dim]当前目录无 YAML 文件。[/dim]")
        return
    for f in sorted(yaml_files):
        try:
            data = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
            did = data.get("domain_id", "?")
            ver = data.get("domain_version", "?")
            console.print(f"  {f:<30s} {did} v{ver}")
        except Exception:
            console.print(f"  {f:<30s} [dim](解析失败)[/dim]")


@domainpack.command()
@click.argument("file_path", type=click.Path(exists=True))
def show(file_path: str) -> None:
    """显示 DomainPack 详情。"""
    import yaml
    from rich.console import Console
    from rich.table import Table

    console = Console()
    data = yaml.safe_load(Path(file_path).read_text(encoding="utf-8"))

    console.print(f"[bold]{data.get('domain_name', '?')}[/bold]")
    console.print(f"  ID: {data.get('domain_id')}")
    console.print(f"  Version: {data.get('domain_version')}")
    console.print(f"  State Variables: {len(data.get('state_variables', []))}")
    console.print(f"  Constraints: {len(data.get('constraints', []))}")
    console.print(f"  Action Templates: {len(data.get('action_templates', []))}")
    console.print(f"  Human Roles: {len(data.get('human_roles', []))}")

    if data.get("constraints"):
        table = Table(title="Constraints")
        table.add_column("ID")
        table.add_column("Criticality")
        table.add_column("Rigidity")
        for c in data["constraints"]:
            table.add_row(c.get("id", "?"), c.get("criticality", "?"), c.get("rigidity", "?"))
        console.print(table)
```

- [ ] **Step 3: 在 cli.py 中注册**

```python
# cli.py 中添加
from polymorphic_twin.workbench.commands.domainpack import domainpack as domainpack_cmd
main.add_command(domainpack_cmd, "domainpack")
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/workbench/unit/test_domainpack_cmd.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add polymorphic_twin/workbench/commands/domainpack.py tests/workbench/unit/test_domainpack_cmd.py
git commit -m "feat(workbench): add ptw domainpack validate/list/show subcommands"
```

---

## Quality Gate Checklist

- [ ] `ptw version` 输出 `polymorphic-twin 0.1.0`
- [ ] `ptw workbench templates` 列出 3 个模板
- [ ] `ptw workbench init --template minimal --name test` 生成可校验通过的 YAML
- [ ] `ptw workbench validate <file>` 正确报告通过/失败
- [ ] `ptw domainpack validate <file>` 独立校验可用
- [ ] 5 种典型错误可检测：YAML 语法错误、缺字段、引用未定义变量、刚性-关键性冲突、fallback 缺字段
- [ ] `pytest tests/workbench/ -v` 全部通过
