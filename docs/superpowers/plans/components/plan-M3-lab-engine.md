# M3: Lab 隔离探索引擎最小子集

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 搭建 Lab 的隔离沙箱环境、可插拔策略引擎（抽象基类 + 纯算法首个实现）、提交链路（CoreCompatibilityPrecheck → 检疫 → 证据准入 → 脱敏反馈）、内部评估筛选。M3 完成后，探索闭环（§2.2）的 Lab 侧全通。

**Architecture:** Lab 是隔离的——只能访问 LabExplorationView 投影的数据，只能通过 SubmissionQuarantine 向 Core 提交。策略引擎是可插拔的：抽象基类定义 6 个必须实现的方法（explore, reproducibility_manifest, constraint_awareness, data_requirements, exploration_space_mapping, health_indicators），具体策略（algorithmic/ml/llm）实现基类。沙箱强制输入类型为 LabExplorationView，资源受限。

**Tech Stack:** Python 3.11+, Pydantic v2, numpy/scikit-learn (optional, for ML strategy)

**Spec reference:** §3.4 Lab, §2.2 探索闭环

**Depends on:** M1 (TOM + 视图投影), M2 (Core quarantine + prescreen + evidence)

**注意：** 虽然里程碑文档将 M2/M3/M4 标记为可并行开发，但 M3 的提交链路功能依赖 M2 的 SubmissionQuarantine 和 PrescreenLibrary。并行开发时，M3 可先实现沙箱和策略引擎（Task 1-5），等 M2 完成后再实现提交链路（Task 6-11）。

**Quality gate (M3-C1 ~ C4):**
- C1: 隔离验证 — Lab 尝试访问 Core 内部接口 → 全部被拒绝
- C2: CoreCompatibilityPrecheck 限权 — 格式不完整的候选被拒绝，不模拟 HardGate
- C3: 完整提交链路 — 候选生成 → Precheck → 打包 → 检疫 → Core 证据准入 → 接收反馈，全链路有日志
- C4: 反馈不泄露隐藏集信息 — 多次被拒绝后分析反馈，无法区分原因

---

## File Structure

```
src/polytwin/lab/
├── __init__.py
├── types.py               # Task 1: Lab-specific types (ExplorationBudget, ExplorationResult, Finding, Hypothesis, etc.)
├── strategies/
│   ├── __init__.py
│   ├── base.py            # Task 2: ExplorationStrategy ABC (6 abstract methods)
│   └── algorithmic.py     # Task 3: 首个实现 — 纯算法策略（状态空间网格搜索 + 反例检测）
├── sandbox.py             # Task 4: Sandbox 执行环境（输入类型强制 + 资源限制）
├── explorer.py            # Task 5: LabExplorer 四用途调度 + 帕累托筛选
├── data_release.py        # Task 6: DataReleaseManager (Core → Lab 数据释放)
├── counterexample.py      # Task 7: 反例发现引擎
├── hypothesis.py          # Task 8: 假设生成与验证（含 falsification_tests）
├── failure_analyzer.py    # Task 9: 失效日志关联分析
├── counterfactual.py      # Task 10: 反事实场景生成
└── submission.py          # Task 11: 提交链路（Precheck → 打包 → 检疫 → 反馈处理）
tests/unit/
├── test_lab_types.py
├── test_strategy_base.py
├── test_algorithmic_strategy.py
├── test_sandbox.py
├── test_explorer.py
├── test_data_release.py
├── test_counterexample.py
├── test_hypothesis.py
├── test_failure_analyzer.py
├── test_counterfactual.py
└── test_submission.py
```

---

## Task 1: Lab 类型定义

**Files:** `src/polytwin/lab/types.py`, `tests/unit/test_lab_types.py`

**类型列表：**

| 类型 | 用途 | 关键字段 |
|------|------|----------|
| `ExplorationBudget` | 探索预算控制 | max_iterations, max_time_seconds, max_memory_mb, max_cpu_percent |
| `Finding` | 探索发现 | finding_id, type(counterexample/pattern/anomaly), description, confidence, data |
| `Hypothesis` | 约束假设 | hypothesis_id, statement, falsification_tests: list[dict], supporting_evidence, confidence |
| `Counterexample` | 反例 | counterexample_id, model_id, state_at_failure, constraint_violated, severity |
| `CounterfactualScenario` | 反事实场景 | scenario_id, base_state, modified_state, divergence_score, models_disagree |
| `CorrelationFinding` | 失效关联 | finding_id, event_sequence, correlation_strength, statistical_significance |
| `ExplorationResult` | 综合结果 | findings, hypotheses, counterexamples, confidence_scores, strategy_manifest |
| `CandidateModelPackage` | 候选模型 | model_id, architecture_description, training_data_lineage, constraint_violation_report: str ("预筛结果，非权威"), reproducibility_recipe |
| `LabSubmission` | 提交包 | submission_id, items: list[CandidateModelPackage], strategy_manifest, is_prescreen: bool=True |
| `LabSubmissionResponse` | 脱敏反馈 | submission_id, item_results: list[dict], aggregate_summary: str, hidden_set_info_exposed: bool=False |
| `StrategyManifest` | 策略元信息 | name, version, reproducibility: dict, constraint_awareness_level: str |

- [ ] **Step 1-5: TDD**

---

## Task 2: 策略抽象基类

**Files:** `src/polytwin/lab/strategies/base.py`, `tests/unit/test_strategy_base.py`

**Spec §3.4: 五条保护规则要求每个策略独立声明。**

```python
from abc import ABC, abstractmethod

class ExplorationStrategy(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def explore(self, data: LabExplorationView, constraints: list[dict], budget: ExplorationBudget) -> ExplorationResult: ...

    @abstractmethod
    def reproducibility_manifest(self) -> dict:
        """返回：随机种子、依赖版本、数据 lineage、确定性保证级别"""

    @abstractmethod
    def constraint_awareness(self) -> str:
        """返回：algorithmic | ml | llm — 该策略对约束违反的检测能力"""

    @abstractmethod
    def data_requirements(self) -> list[str]:
        """返回：该策略需要的数据字段列表（用于 DataReleasePackage 授权粒度）"""

    @abstractmethod
    def exploration_space_mapping(self) -> dict:
        """返回：该策略在三层探索空间中的自由度"""

    @abstractmethod
    def health_indicators(self) -> dict:
        """返回：策略健康度指标（检测刷分退化）"""
```

**测试：** 定义一个 MinimalStubStrategy 实现所有抽象方法，验证接口完整。

- [ ] **Step 1-5: TDD**

---

## Task 3: 纯算法策略（首个实现）

**Files:** `src/polytwin/lab/strategies/algorithmic.py`, `tests/unit/test_algorithmic_strategy.py`

**实现思路：** 状态空间网格搜索 + 反例检测。给定状态变量的范围，在网格点上评估约束违反，找出约束边界附近的反例。

**关键测试：**

| 测试 | 验证 |
|------|------|
| 返回 ExplorationResult | 包含 findings + counterexamples |
| constraint_violation_report 标注 "预筛结果" | 非权威标记 |
| reproducibility_manifest 包含种子和版本 | 可复现 |
| constraint_awareness == "algorithmic" | 声明为算法级约束感知 |
| budget 耗尽时停止 | max_iterations 限制有效 |

- [ ] **Step 1-5: TDD**

---

## Task 4: 沙箱执行环境

**Files:** `src/polytwin/lab/sandbox.py`, `tests/unit/test_sandbox.py`

**M3-C1 验收的关键组件：**

```python
class Sandbox:
    async def execute(
        self,
        strategy: ExplorationStrategy,
        data: LabExplorationView,  # 强制类型：只能传入 Lab 视图
        budget: ExplorationBudget,
    ) -> ExplorationResult:
        # 1. isinstance 检查
        assert isinstance(data, LabExplorationView)
        # 2. 设置资源限制
        # 3. 执行策略
        result = strategy.explore(data, [], budget)
        # 4. 注入 reproducibility_manifest
        enriched = self._inject_manifest(result, strategy.reproducibility_manifest())
        # 5. 返回
        return enriched
```

**测试：**

| 测试 | 验证 |
|------|------|
| 正常执行 | LabExplorationView 输入 → ExplorationResult 输出 |
| 非 LabExplorationView 被拒绝 | 传入 CoreRuntimeView → AssertionError |
| budget 超时 | 执行超时 → ExplorationBudgetExceeded |
| manifest 自动注入 | 结果包含 strategy_manifest |

- [ ] **Step 1-5: TDD**

---

## Task 5: 探索编排器（四用途调度）

**Files:** `src/polytwin/lab/explorer.py`, `tests/unit/test_explorer.py`

**四个方法：**

```python
class LabExplorer:
    async def run_counterexample_search(self, target_domain, budget) -> list[Counterexample]: ...
    async def run_constraint_hypothesis(self, failure_logs, budget) -> list[Hypothesis]: ...
    async def run_failure_correlation(self, failure_logs) -> list[CorrelationFinding]: ...
    async def run_counterfactual_generation(self, model_ids, budget) -> list[CounterfactualScenario]: ...

    def _select_strategies(self, task_type: str) -> list[ExplorationStrategy]:
        """按优先级选择策略：algorithmic > ml > llm"""

    async def _submit_to_core(self, findings) -> None:
        """所有提交必须经过 quarantine"""
```

- [ ] **Step 1-5: TDD**

---

## Task 6: DataReleaseManager

**Files:** `src/polytwin/lab/data_release.py`, `tests/unit/test_data_release.py`

**Core → Lab 数据释放通道。隐藏验证集永远不通过此接口暴露。**

```python
class DataReleaseManager:
    async def release_failure_logs(self, dp_id: str, session_id: str) -> FailureLogReleasePackage: ...
    async def get_authorized_data(self, dp_id: str) -> LabExplorationView: ...
    async def get_public_eval_set(self, dp_id: str) -> list[dict]: ...
    # 以下方法不存在 — 隐藏验证集不可访问
    # async def get_hidden_challenge_set(self, ...) → 永远不存在此方法
```

- [ ] **Step 1-5: TDD**

---

## Task 7-10: 四用途探索模块

**Files:** counterexample.py, hypothesis.py, failure_analyzer.py, counterfactual.py

每个模块一个 Task，按 TDD 展开。每个模块的测试必须验证：
- 输入只能是 LabExplorationView 或脱敏数据
- 输出包含 reproducibility_manifest
- constraint_violation_report 标注 "预筛结果，非权威"

- [ ] **Task 7: 反例发现** — 在授权数据中系统性遍历状态空间
- [ ] **Task 8: 假设生成** — 生成带 falsification_tests 的 ConstraintHypothesis
- [ ] **Task 9: 失效关联** — 跨事件关联分析
- [ ] **Task 10: 反事实生成** — 搜索模型预测分歧区域

---

## Task 11: 提交链路

**Files:** `src/polytwin/lab/submission.py`, `tests/unit/test_submission.py`

**完整链路（M3-C3 验收）：**

```
候选模型生成
  → CoreCompatibilityPrecheck（格式完整性 + lineage 可追溯，不模拟 HardGate）
  → 打包为 LabSubmission（is_prescreen=True）
  → SubmissionQuarantine（检疫）
  → Core.Evidence（证据准入）
  → 写入 TwinObject.knowledge_state.admitted_lab_evidence
  → 返回 LabSubmissionResponse（脱敏反馈）
```

**M3-C2 测试：** 提交缺失 lineage 的候选 → Precheck 拒绝，且不模拟 HardGate 判断。

**M3-C4 测试：** 提交 10 个被拒绝的模型，检查所有反馈格式一致，无法区分"隐藏集被拒"vs"公开集不足被拒"。

- [ ] **Step 1-5: TDD**

---

## M3 验收检查点

| 检查点 | 验证命令 | 预期结果 |
|--------|----------|----------|
| **M3-C1: 隔离验证** | `pytest tests/unit/test_sandbox.py tests/unit/test_data_release.py -v` | 非 Lab 视图被拒绝，隐藏集方法不存在 |
| **M3-C2: Precheck 限权** | `pytest tests/unit/test_submission.py::TestPrecheckLimit -v` | 格式不全被拒，不模拟 HardGate |
| **M3-C3: 完整提交链路** | `pytest tests/unit/test_submission.py::TestFullChain -v` | 全链路有日志可追溯 |
| **M3-C4: 反馈不泄露** | `pytest tests/unit/test_submission.py::TestFeedbackNoLeak -v` | 无法区分拒绝原因 |
| **CI 隔离检查** | `python scripts/check_import_isolation.py` | lab/ 无违规 import |

---

## Jelly 集成任务 (Spec v2.1.0 §3.7)

> **详细设计**: `2026-05-08-jelly-mcp-client-integration.md §6.2`
> **Jelly Phase 依赖**: Phase 2 (Group 3: twin.get_exploration_data, twin.get_failure_logs, twin.query_operational_history)

### Jelly Task: Lab 探索数据从 Jelly 获取

**Files:**
- Modify: `src/polytwin/lab/data_release.py` — 新增 Jelly 探索数据源
- Modify: `src/polytwin/lab/explorer.py` — 可选 Jelly 领域知识查询
- Test: `tests/unit/test_jelly_exploration.py`

**目的:** Lab 的假设探索可从 Jelly 获取授权数据空间，增强探索质量。

**集成方式:**

```python
class LabExplorer:
    def __init__(self, jelly: JellyClient | None): ...

    def get_exploration_data(self, domain_id, data_release_id):
        """优先使用 Core 释放的本地数据。
        如果本地数据不足，从 Jelly twin.get_exploration_data 补充。
        caller="lab" → Jelly 侧自动过滤敏感字段。
        """
        local_data = self._get_local_data(domain_id, data_release_id)
        if self.jelly and len(local_data.records) < threshold:
            jelly_data = self.jelly.get_exploration_data(
                domain_id, data_release_id, caller="lab"
            )
            return merge(local_data, jelly_data)
        return local_data

    def get_failure_logs(self, domain_id, time_range):
        """从 Jelly twin.get_failure_logs 获取脱敏失效日志。"""

    def query_domain_knowledge(self, domain_id, hypothesis):
        """假设生成时查询 Jelly 领域知识（Phase 3 可用）。"""
```

**降级:** Jelly 不可用时仅使用 Core DataReleaseManager 释放的本地数据。

**安全约束:** Lab 通过 JellyClient 调用时 caller="lab"，Jelly 侧过滤确保不返回 audit_benchmark、production_acceptance、安全回落策略细节。
