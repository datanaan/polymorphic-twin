# M6: 多场景 DomainPack 验证

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 证明系统可以通过替换 DomainPack 适配不同场景，不需要修改 Core/Lab/Bridge 代码。创建三个不同场景的 DomainPack，每个都通过刚性-关键性检查和闭环测试。

**Architecture:** 纯配置验证。不修改任何代码，只创建新的 DomainPack YAML 文件，加载后运行 M5 的测试套件。

**Spec reference:** §3.6 DomainPack, §2.5 演化闭环

**Depends on:** M5 (闭环集成通过)

**Quality gate (M6-C1 ~ C3):**
- C1: 跨场景零代码修改 — 切换 DomainPack 后 Core/Lab/Bridge 的 Git diff = 0
- C2: DomainPack 创建耗时 — 单个 DomainPack 初稿 < 1 工作日
- C3: 多场景并行运行 — 两个不同场景的 TwinObject 实例互不干扰

---

## File Structure

```
configs/examples/
├── minimal-domain-pack.yaml              # M0 已创建
├── chemical-reactor-thermal-0.1.0.yaml   # Task 1: 化工反应器温度控制
├── wind-turbine-bearing-0.1.0.yaml       # Task 2: 风机轴承退化监测
├── knowledge-management-0.1.0.yaml        # Task 3: 个人知识管理（理论文档推荐场景）
tests/integration/
├── test_multiscene_switch.py             # Task 4: 场景切换测试
├── test_multiscene_parallel.py           # Task 5: 并行场景测试
├── test_multiscene_zero_diff.py          # Task 6: 零代码修改验证
└── test_evolution_loop.py                # Task 7: 演化闭环端到端
```

---

## Task 1: 化工反应器温度控制 DomainPack

**Files:** `configs/examples/chemical-reactor-thermal-0.1.0.yaml`

**场景：** 简化化工反应器的温度控制系统。

**状态变量（至少 5 个）：**
- reactor_temp (°C), coolant_flow (L/min), reaction_rate (mol/s), product_quality (%), vessel_pressure (bar)

**约束卡片：**
- safety_critical: reactor_temp 上限 350°C（absolute）
- safety_critical: vessel_pressure 上限 15 bar（absolute）
- identity_critical: 反应速率应在 Arrhenius 预测的 ±20% 内
- operational: 冷却能力与产热平衡
- soft: product_quality 目标 ≥ 92%

**安全回落：** 注入冷却剂，降至安全温度

- [ ] **Step 1: 编写 YAML**
- [ ] **Step 2: 运行 validate_domainpack.py**
- [ ] **Step 3: Commit**

---

## Task 2: 风机轴承退化监测 DomainPack

**Files:** `configs/examples/wind-turbine-bearing-0.1.0.yaml`

**场景：** 风力发电机主轴承的退化监测。

**状态变量：**
- vibration_freq (Hz), bearing_temp (°C), rotor_speed (RPM), power_output (kW), oil_quality_index (0-1)

**约束卡片：**
- safety_critical: vibration_freq 不超过 2500 Hz
- identity_critical: 温度-转速耦合在物理合理范围
- operational: 功率输出在额定范围内
- soft: 润滑油质量指数 ≥ 0.7

**安全回落：** 降速停机

- [ ] **Step 1: 编写 YAML**
- [ ] **Step 2: 运行 validate_domainpack.py**
- [ ] **Step 3: Commit**

---

## Task 3: 个人知识管理 DomainPack

**Files:** `configs/examples/knowledge-management-0.1.0.yaml`

**场景：** 理论文档 §07 推荐的首个 MVP 场景。将用户知识统一建模为 TwinObject。

**状态变量：**
- knowledge_freshness (days), link_density (count), coverage_ratio (0-1), contradiction_count (count), usage_frequency (count/week)

**约束：**
- operational: knowledge_freshness < 90 days
- soft: coverage_ratio ≥ 0.6
- soft: contradiction_count < 3

**安全回落：** 标记为需人工审查

- [ ] **Step 1: 编写 YAML**
- [ ] **Step 2: 运行 validate_domainpack.py**
- [ ] **Step 3: Commit**

---

## Task 4: 场景切换测试

**Files:** `tests/integration/test_multiscene_switch.py`

```python
class TestSceneSwitch:
    async def test_switch_domainpack_and_rerun_tests(self, api_client):
        """M6-C1: 切换 DomainPack 后运行测试，Core/Lab/Bridge 行为正确。"""
        for dp_file in ["minimal-domain-pack.yaml", "chemical-reactor-thermal-0.1.0.yaml",
                         "wind-turbine-bearing-0.1.0.yaml"]:
            # 加载 DomainPack
            await api_client.post("/api/v1/domainpack/load", files={"file": open(f"configs/examples/{dp_file}")})
            # 运行感知闭环
            response = await api_client.post("/api/v1/tom/objects", json={...})
            assert response.status_code == 201
            # 运行约束验证
            response = await api_client.post("/api/v1/core/validate", json={...})
            assert response.status_code == 200
```

- [ ] **Step 1-5: TDD**

---

## Task 5: 并行场景测试

**Files:** `tests/integration/test_multiscene_parallel.py`

```python
class TestParallelScenes:
    async def test_two_scenes_independent(self, api_client):
        """M6-C3: 两个不同场景的 TwinObject 实例互不干扰。"""
        # 加载两个 DomainPack
        # 创建对象 A (场景 1)
        # 创建对象 B (场景 2)
        # 修改 A 的状态
        # B 的状态不受影响
```

- [ ] **Step 1-5: TDD**

---

## Task 6: 零代码修改验证

**Files:** `tests/integration/test_multiscene_zero_diff.py`

```python
class TestZeroCodeModification:
    def test_core_lab_bridge_no_diff_after_multiscene(self):
        """M6-C1: 验证 Core/Lab/Bridge 代码无修改。"""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "src/polytwin/core/", "src/polytwin/lab/", "src/polytwin/bridge/"],
            capture_output=True, text=True,
        )
        assert result.stdout == "", f"Code was modified: {result.stdout}"
```

- [ ] **Step 1-5: TDD**

---

## Task 7: 演化闭环端到端验证

**Files:** `tests/integration/test_evolution_loop.py`

**⚠️ 此 Task 修复自检缺口 1.3：Spec §2.5 演化闭环无实现任务。**

**Spec §2.5 验收：** 执行闭环的累积结果 → Core 分析证据模式 → Lab 发现新约束假设 → 提交检疫 → 人类审批 → DomainPack 更新 → Bridge 失效。

```python
class TestEvolutionLoop:
    async def test_lab_discovers_new_constraint_from_cumulative_failures(self, api_client, loaded_domainpack):
        """§2.5 验收 1: Lab 能从累积失败日志中发现至少一个新模式。"""
        # 1. 创建 TwinObject 并产生多次约束违规
        obj_id = (await api_client.post("/api/v1/tom/objects", json={
            "type": "device",
            "state_semantics": {"current_values": {"temperature": 185.0}},
        })).json()["id"]
        # 多次触发违规，产生累积日志
        for _ in range(5):
            await api_client.post("/api/v1/core/validate", json={
                "object_id": obj_id,
                "state_values": {"temperature": 185.0},
            })
        # 2. Lab 探索假设
        response = await api_client.post("/api/v1/lab/explore/hypothesis", json={
            "object_id": obj_id,
            "focus": "constraint_pattern",
        })
        assert response.status_code == 200
        hypotheses = response.json()["hypotheses"]
        assert len(hypotheses) >= 1

    async def test_approved_hypothesis_updates_domainpack(self, api_client, loaded_domainpack):
        """§2.5 验收 2: 新约束假设经人类审批后能更新 DomainPack。"""
        # 提交假设 → 检疫 → 人类审批 → DomainPack 版本更新
        ...

    async def test_domainpack_update_invalidates_bridge_output(self, api_client, loaded_domainpack):
        """§2.5 验收 3: DomainPack 版本更新后，活跃的 BridgeOutput 被标记为失效。"""
        # 生成 BridgeOutput → 更新 DomainPack → 验证 BridgeOutput invalid
        ...

    async def test_twin_object_lineage_records_evolution(self, api_client, loaded_domainpack):
        """§2.5 验收 4: TwinObject 谱系正确记录演化来源。"""
        # 更新 DomainPack 后检查 TwinObject 的 lineage 追溯链
        ...
```

- [ ] **Step 1-5: TDD**

---

## M6 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M6-C1: 零代码修改** | `pytest tests/integration/test_multiscene_zero_diff.py -v` | Git diff = 0 |
| **M6-C2: 创建耗时** | 人工记录 | 每个 < 1 工作日 |
| **M6-C3: 并行隔离** | `pytest tests/integration/test_multiscene_parallel.py -v` | 互不干扰 |
| **§2.5 演化闭环** | `pytest tests/integration/test_evolution_loop.py -v` | 四项验收全部 PASSED |

---

## Jelly 集成任务 (Spec v2.1.0 §3.7)

> **详细设计**: `2026-05-08-jelly-mcp-client-integration.md §6.2`
> **Jelly Phase 依赖**: Phase 1-3 (Group 1: DomainPack 搜索, Group 4: 领域知识查询)

### Jelly Task: 多场景 DomainPack 从 Jelly 搜索和加载

**Files:**
- Modify: `tests/integration/test_multiscene_*.py` — 新增 Jelly 来源测试
- Test: `tests/integration/test_jelly_multiscene.py`

**目的:** 验证 M6 的三个额外 DomainPack（化学反应器、风机轴承、知识管理）可从 Jelly MCP 获取并加载。

**新增测试:**

```python
# tests/integration/test_jelly_multiscene.py

async def test_jelly_search_finds_cstr():
    """twin.search_domain_packs(keywords=["chemical", "reactor"]) 返回 CSTR"""
    results = jelly_client.search_domain_packs(keywords=["chemical", "reactor"])
    assert any(r.domain_id == "cstr.standard" for r in results)

async def test_jelly_domain_pack_loads_into_registry():
    """从 Jelly 获取的 DomainPack 能通过 PT 加载时验证"""
    jdp = jelly_client.get_domain_pack("chemical-reactor-thermal", caller="core")
    dp = convert_jelly_domain_pack(jdp)
    registry.register(dp)
    # 验证刚性-关键性兼容检查通过
```

**降级测试:** 三个场景在 Jelly 不可用时仍可使用本地 YAML 正常运行。
