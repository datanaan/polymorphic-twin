# Polymorphic-Twin 系统设计规范

> **版本**: 2.2.0
> **日期**: 2026-05-07
> **状态**: 待审核（第三轮）
> **技术栈**: Python 单语言单体
> **里程碑基准**: `docs/struc/Polymorphic-Twin 开发里程碑与关键检查点.md`

---

## 1. 设计决策

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 产品形态 | 平台优先 | 核心引擎稳定后再包装终端应用 |
| 技术栈 | Python 3.11+ 单体 | 独立开发者效率最高，Lab 的 ML 生态原生 |
| Lab 探索策略 | 可插拔引擎 | 五条保护规则的工程必然 |
| Lab 约束感知 | Core 提供无状态预筛函数 | Lab 可调用但不作为权威结论，Core 仍做终审 |
| 身份连续性 | IdentityMonitor 运行时组件 | 独立模块，周期性评估身份不变量漂移 |
| 外部知识来源 | 可选 Jelly MCP 集成 | Jelly 提供领域数据增强，但 PT 核心不依赖外部系统。详见 `2026-05-08-jelly-mcp-client-integration.md` |
| 开发节奏 | 对齐 M0-M7 里程碑 | 以检查点为验收标准 |

---

## 2. 五闭环定义

### 2.1 感知闭环 (Perception Loop)

**职责**：将外部输入转化为 TwinObject 并匹配到场景。

```
外部输入（传感器/用户/API）
  → TOM：创建/更新 TwinObject，写入 state_semantics.current_values
  → TOM：根据当前 DomainPack 执行视图投影
  → DomainPack.Registry：场景匹配（基于对象类型和状态域）
    → 如果 Jelly 可达：Registry 优先使用 Jelly 提供的 DomainPack（`twin.get_domain_pack`）
    → 如果 Jelly 不可达：Registry 使用本地 YAML 兜底
  → 输出：匹配的 domain_pack_id 或"无匹配场景"
```

**验收断言 (M1)**：
- 给定一组状态变量输入，系统能在 < 50ms 内完成对象创建和视图投影
- 给定一个对象和一个已注册的 DomainPack，系统能正确返回匹配/不匹配
- 无匹配场景时不崩溃，返回明确错误

**涉及的模块**：TOM (facade, store) + DomainPack (registry)

---

### 2.2 探索闭环 (Exploration Loop)

**职责**：Lab 在授权数据空间内生成假设并排序。

```
Core → DataReleaseManager：释放脱敏历史数据 + FailureLogReleasePackage + 公开评估集
  → 数据来源（优先级）：
    1. 本地运行时累积数据（首选）
    2. Jelly `twin.get_exploration_data`（历史数据增强，Phase 2 可用）
    3. Jelly `twin.get_failure_logs`（失效模式补充，Phase 2 可用）
  → Lab.Sandbox：接收 LabExplorationView 投影的数据
  → Lab.Strategies：策略执行（反例发现 / 约束假设 / 失效关联 / 反事实生成）
    ↕ Lab 内部迭代：预筛函数评估候选 → 淘汰明显不合格的 → 深入有潜力的
  → Lab.Explorer：汇总发现，排序假设（帕累托前沿过滤）
  → 输出：排序后的 ExplorationResult（含假设集、反例集、置信度）
```

**验收断言 (M3)**：
- Lab 能从授权数据中生成至少 N 个假设
- 每个假设附带 falsification_tests（可证伪测试）
- 每个假设附带策略的 reproducibility_manifest
- Lab 的约束违反报告明确标注为"预筛结果，非权威结论"
- 隔离验证：Lab 尝试访问 Core 内部接口 → 全部被拒绝 (M3-C1)

**涉及的模块**：Lab (sandbox, explorer, strategies, data_release) + Core (data_release_manager)

---

### 2.3 决策闭环 (Decision Loop)

**职责**：Core 对 Lab 输出进行资格审判，Bridge 编排行动空间。

```
Lab.Explorer 输出 ExplorationResult
  → Core.Quarantine：检疫（格式完整性、资源异常、敏感信息扫描）
  → Core.Evidence：证据准入（item 级独立判决）
    → 验证数据来源：
      1. DomainPack 内嵌引用（本地）
      2. Jelly `twin.get_validation_set` (set_type="production_acceptance")
    → Core 使用 Jelly 数据前执行二次视图过滤兜底（契约 Q10）
    → 模型类证据：sandbox 级 HardGate（不含隐藏验证集）
    → 约束假设类：标记为 candidate
  → Core.HardGate：链路权限判决（六项检验）
  → TOM.update：写入 knowledge_state.admitted_lab_evidence
  → Bridge.Orchestrator：读取 BridgeDecisionView
  → Bridge.ActionSpace：构建四分类行动空间（immediate / conditional / forbidden / undetermined）
  → Bridge 输出 BridgeOutput（含有效期）
  → 审计：全程写入 AuditTrail
```

**验收断言 (M5)**：
- 从 Lab 提交到 Bridge 输出行动空间，全链路可追溯
- 有效 item 被准入，无效 item 被拒绝，拒绝不影响同批次其他 item (M2-C4)
- 反馈脱敏：Lab 无法区分"因隐藏集被拒"和"因公开集性能不足被拒" (M2-C5)
- Bridge 输出的 forbidden_actions 与 Core 判决一致 (M4-C1)

**涉及的模块**：Core (quarantine, evidence, hardgate) + TOM (facade, update) + Bridge (orchestrator, action_space)

---

### 2.4 执行闭环 (Execution Loop)

**职责**：将 Bridge 的行动空间转化为实际执行并收集结果。

```
BridgeOutput 中的行动项
  → Bridge.HumanResponse：验证有效期和角色权限
  → 执行层：工具调用 / API 调用 / 控制指令
  → 结果回收
  → TOM.update：更新 TwinObject 的 state_semantics.current_values
  → Core.Engine：对新状态执行约束验证
  → Core.IdentityMonitor：对新状态评估身份不变量漂移
  → 若约束违规 → 触发安全回落
  → 若身份漂移超限 → 触发 identity_uncertain
```

**验收断言 (M5)**：
- 执行结果能更新 TwinObject 状态
- 更新后 Core 自动重新验证约束
- safety_critical 违规在 200ms 内触发安全回落 (M5-C2)
- 执行结果写入审计日志，不可篡改

**涉及的模块**：Bridge (human_response) + TOM (facade, update) + Core (engine, identity_monitor, fallback)

---

### 2.5 演化闭环 (Evolution Loop)

**职责**：从执行结果中学习新约束，更新场景配置，推动谱系演化。

```
执行闭环的累积结果
  → Core.Evidence：统计分析准入证据的长期模式
  → Lab.ConstraintHypothesis：从累积失败日志中发现新约束假设
    → 知识来源（可选增强）：
      1. 累积失败日志（内部）
      2. Jelly `twin.query_domain_knowledge`（领域知识增强，Phase 3 可用）
      3. Jelly `twin.get_physical_limits`（物理极限验证，Phase 3 可用）
  → Lab 提交约束假设 → Core.Quarantine → 标记为 candidate
  → 人类审批（通过 Bridge）：确认/拒绝约束假设
  → 确认后 → DomainPack.Lifecycle：更新约束卡片（新增/调整参数）
  → TOM.Identity：记录谱系演化（新版本 TwinObject + 继承链）
  → 新 DomainPack 版本 → 所有已激活的 BridgeOutput 立即失效
```

**验收断言 (M6)**：
- Lab 能从累积失败日志中发现至少一个新模式
- 新约束假设经人类审批后能更新 DomainPack
- DomainPack 版本更新后，活跃的 BridgeOutput 被标记为失效
- TwinObject 谱系正确记录演化来源

**涉及的模块**：Lab (hypothesis) + Core (quarantine, evidence) + Bridge (validity) + DomainPack (lifecycle) + TOM (identity)

---

## 3. 组件职责与接口契约

### 3.1 TOM (TwinObject Model)

**职责**：
- 统一数据表示：所有实体建模为 TwinObject
- 视图投影：五种视图，按调用者身份返回不可变快照
- 快照管理：不可变版本快照，append-only
- 身份谱系：来源链追踪，支持溯源
- 变更追踪：关键字段变更记录时间戳和来源

**接口契约**：

| 接口 | 输入 | 输出 | 权限 |
|------|------|------|------|
| create | TwinObjectInternal | id (str) | core, api |
| get_view | (view_type, caller) | frozen ViewSnapshot | 所有组件（按视图权限） |
| update | (caller, changes) | void | core_runtime（写约束/状态），bridge（写行动），audit（只读） |
| create_snapshot | object_id | snapshot_id | core, audit |
| get_snapshot | snapshot_id | TwinObjectInternal | core, audit |
| get_change_history | object_id | list[ChangeRecord] | audit |

**五种视图访问矩阵**：

| 调用者 | CoreRuntime | CoreCertification | BridgeDecision | LabExploration | Audit |
|--------|:-----------:|:-----------------:|:--------------:|:--------------:|:-----:|
| core_runtime | ✓ | ✗ | ✓ | ✓ | ✗ |
| core_certification | ✓ | ✓ | ✗ | ✗ | ✗ |
| lab | ✗ | ✗ | ✗ | ✓ | ✗ |
| bridge | ✗ | ✗ | ✓ | ✗ | ✗ |
| audit | ✓ | ✗ | ✗ | ✗ | ✓ |

**数据协议**：

TwinObject 由通用底层（Identity, Lineage, State, Relationships）和类型化顶层组成：

| 顶层模块 | 关键字段 | 强制语义 |
|----------|----------|----------|
| StateSemantics | variables{name, unit, range, observable, controllable}, current_values | 状态变量的物理含义，不是自由字典 |
| ConstraintState | active_constraints, suspended_constraints, last_evaluation | 约束治理状态，四态判决结果 |
| IdentityInvariants | invariants{name, expected, actual, confidence}, overall_confidence, identity_status | 身份连续性指标，支持漂移计算 |
| ModelGovernanceState | active_links, qualification_history, active_certificates | 模型链路权限，不是泛化的 Relationship |
| KnowledgeState | admitted_lab_evidence, pending_submissions | Core 准入的 Lab 证据 |
| ActionState | current_safe_action_set, fallback_available | 当前安全行动集 |
| AuditTrail | events[] | 只追加，不可删除/修改 |

**快照格式**：`{twin_id}_{timestamp}_{hash}`，不可删除，不可修改。

---

### 3.2 Core (约束治理引擎)

**职责**：
- 约束验证：四态判决（passed / uncertain / failed / not_applicable）
- HardGate 资格审判：六项检验，输出链路权限
- 安全回落：safety_critical 违规时立即触发，不可被中断
- 检疫：Lab 提交物的唯一入口
- 证据准入：item 级独立判决
- 身份监控：周期性评估身份不变量漂移
- 预筛函数库：向 Lab 提供无状态约束验证函数

**模块间隔离规则**：

```
runtime.py ←→ hardgate.py ←→ identity_monitor.py     （运行时层，Lab 不可见）
certification.py                                      （认证层，runtime 和 Lab 都不可见）
quarantine.py                                         （Lab → Core 唯一入口）

runtime.py ≠/→ certification.py    禁止调用
hardgate.py ≠/→ certification.py   禁止调用
Lab 代码 ≠/→ core.certification    禁止 import（CI 强制）
Lab 代码 ≠/→ core.hardgate         禁止 import（CI 强制）
```

**约束求值器的四态判决**：

| 状态 | 触发条件 | 后续动作 |
|------|----------|----------|
| passed | 验证函数返回通过，且在适用域内 | 记录结果，继续下一约束 |
| uncertain | 验证函数返回不确定 | 记录结果，标记需人工判断 |
| failed | 验证函数返回失败，且在适用域内 | safety_critical → 立即触发安全回落；其他 → 记录违规 |
| not_applicable | 当前状态不在约束的 domain_of_validity 内 | 约束挂起（suspension），不触发安全回落 |

**HardGate 六项检验**：
1. 状态语义兼容检查
2. 约束适用域匹配检查
3. 所需观测齐备检查
4. 任务类型允许检查（autonomous_control 强制要求安全证书）
5. 安全边界前置检查（不确定性传播后的最坏情况）
6. 干预有效性检查（仅 production_control 和 physical_probe）

**输出**：HardGateResult = {granted_links, degraded_links, denied_links}

---

### 3.3 IdentityMonitor（身份连续性监控）

**职责**：作为 Core 运行时的独立模块，周期性评估系统身份是否连续。

**数据流**：

```
TOM.IdentityInvariants（当前值）
  → IdentityMonitor：采样当前状态
  → 计算 invariant drift = |actual - expected| / expected
  → 与历史样本比较时序趋势
  → 判定结果：
    - confirmed（所有不变量在容差内）
    - uncertain（部分不变量漂移超限，但未确认断裂）
    - forked（确认身份断裂，需要重建）
  → 更新 TwinObject.identity_invariants.identity_status
  → 若 identity_status = uncertain → Bridge 在行动空间中禁止不可逆操作
  → 若 identity_status = forked → 触发人工审批流程（通过 Bridge）
  → 写入审计日志
```

**关键参数**（由 DomainPack 定义）：

| 参数 | 含义 | 示例 |
|------|------|------|
| identity_check_interval | 检查周期 | 1s |
| drift_tolerance | 单次漂移容差 | 0.05（5%） |
| drift_trend_window | 趋势分析窗口 | 100 个样本 |
| drift_trend_threshold | 趋势超限阈值 | 0.02（2% 持续上升） |
| identity_uncertain_timeout | uncertain 超时 | 30s（超时触发安全回落） |

**接口契约**：

| 接口 | 输入 | 输出 |
|------|------|------|
| check_identity | TwinObject.id | IdentityCheckResult |
| get_drift_history | TwinObject.id, window | list[DriftSample] |

**验收断言**：
- 当传感器持续漂移时，系统能在 identity_uncertain_timeout 内进入 identity_uncertain 状态
- identity_uncertain 状态下 Bridge 的 forbidden_actions 包含所有不可逆操作
- 身份确认断裂后能触发人工审批流程

---

### 3.4 Lab (隔离探索引擎)

**职责**：
- 在授权数据空间内进行假设驱动的探索
- 生成反例、约束假设、失效关联、反事实场景
- 通过可插拔策略引擎支持不同探索方法
- 所有向 Core 的提交必须经过检疫

**约束感知方案**：

Lab 不执行权威的约束评估。Lab 的约束感知通过以下机制实现：

**机制一：Core 预筛函数库**

Core 导出一个无状态的约束预筛函数集 `PrescreenLibrary`：

- 函数包含实际的验证逻辑（不是摘要），但不包含隐藏验证集
- 函数是无状态的：输入状态变量值 + 约束参数 → 输出 passed/uncertain/failed/not_applicable
- Lab 可以在沙箱内调用这些函数对候选模型进行预筛
- **关键声明**：预筛结果仅供 Lab 内部排序和淘汰使用，不是权威结论，不作为证据提交的一部分
- Core 的 quarantine 和 evidence 模块仍做完整的权威评估

```
Core.PrescreenLibrary（导出）
  → Lab.Sandbox（导入，在沙箱内调用）
  → Lab 对候选模型预筛 → 淘汰明显不合格的
  → 预筛通过的候选 → 打包为 LabSubmission
  → 提交时标注：constraint_violation_report = "预筛结果，非权威"
  → Core.Quarantine → Core.Evidence（权威评估，可能拒绝预筛通过的候选）
```

**机制二：证据如实报告**

Lab 产物中的 constraint_violation_report 必须如实填写。即使候选模型在 Lab 内部违反了约束，也必须报告，不能隐瞒。这是硬性要求。

**接口契约**：

| 接口 | 输入 | 输出 |
|------|------|------|
| run_exploration | (task_type, data_release_id, budget) | ExplorationResult |
| get_strategies | — | list[StrategyManifest] |
| submit_to_core | LabSubmission | QuarantineResult（脱敏反馈） |
| get_data_release | domain_pack_id | LabExplorationView |

---

### 3.5 Bridge (决策接口层)

**职责**：
- 从 TwinObject 的 BridgeDecisionView 构建行动空间
- 行动空间四分类，含 prohibition_reason
- 有效期管理，版本不匹配立即失效
- 人类行动响应验证
- 审计记录通过接口输出，不自己持久化

**行动空间四分类**：

| 分类 | 条件 | 内容 |
|------|------|------|
| immediate_actions | 所有前置条件已满足，无安全风险 | 含 execution_mode, risk_level |
| conditional_actions | 存在未满足前置条件 | 含 unmet_prerequisites + lawful_unlock_path |
| forbidden_actions | 违反 safety_critical/identity_critical 约束 | 含 prohibition_reason, lawful_unlock_conditions, permanently_forbidden |
| undetermined_actions | 信息不足，无法判定 | 需要更多数据或人工判断 |

**Bridge 宪法**：
- 输出中不得出现"建议"一词或同义表述
- 每次生成行动空间必须写入审计事件
- 不向物理执行器直接发送指令
- exception_request ≠ override：permanently_forbidden 行动只能发起审查流程

**有效期管理**：

| 失效触发 | 动作 |
|----------|------|
| TwinObject 主版本号变化 | BridgeOutput 立即失效 |
| DomainPack 版本号变化 | BridgeOutput 立即失效 |
| 约束状态变化 | 标记需重新生成 |
| 身份状态变化 | 标记需重新生成 |
| 安全回落不可用 | 标记需重新生成 |

---

### 3.6 DomainPack (场景配置系统)

**职责**：
- 定义场景边界、状态变量、约束卡片、安全回落、行动模板、人类角色
- 加载时严格执行刚性-关键性兼容验证
- 生命周期管理：draft → review → active → deprecated → archived

**约束卡片中的 domain_of_validity（适用域）**：

适用域是一个可计算的结构，用于判断约束在当前状态下是否应被激活。求值器据此判断 not_applicable vs applicable。

**适用域 schema**：

```yaml
domain_of_validity:
  # 条件列表，全部满足时约束适用
  conditions:
    - type: "state_range"              # 状态变量范围
      variable: "temperature"
      min: 100.0
      max: 800.0
      inclusive: true                  # [min, max] vs (min, max)

    - type: "state_enum"               # 状态变量枚举
      variable: "operating_mode"
      values: ["normal", "startup", "shutdown"]

    - type: "sensor_status"            # 传感器状态要求
      sensor_id: "thermocouple_1"
      required_status: "active"        # active | degraded | offline

    - type: "composite"                # 组合条件
      operator: "and"                  # and | or
      sub_conditions:
        - type: "state_range"
          variable: "pressure"
          min: 0
          max: 50

    - type: "identity_confidence"      # 身份置信度要求
      min_confidence: 0.8              # 身份不确定时约束挂起
  match_mode: "all"                    # all = AND, any = OR
```

**求值算法**：

```
对于 domain_of_validity 中的每个 condition:
  state_range:  检查 TwinObject.state_semantics.current_values[variable] 是否在 [min, max] 内
  state_enum:   检查 current_values[variable] 是否在 values 列表中
  sensor_status: 检查对应传感器的状态
  composite:    递归求值 sub_conditions，按 operator 组合
  identity_confidence: 检查 TwinObject.identity_invariants.overall_confidence

match_mode = "all" → 所有条件必须为真
match_mode = "any" → 至少一个条件为真

全部为真 → 约束适用 → 继续验证
任一为假 → 约束 not_applicable → 挂起
```

**假阴性和假阳性的防护**：

| 风险 | 防护机制 |
|------|----------|
| 假阴性（本该适用却被挂起） | domain_of_validity 默认为宽松：未定义 domain_of_validity 的约束卡片默认始终适用。适用域是"缩小范围"而非"扩大范围"。 |
| 假阳性（本不该适用却强制执行） | 求值算法偏向保守：当状态变量缺失或传感器状态未知时，视为"在适用域内"（宁可多检查一次，不可漏检）。 |

**加载时验证**（不变）：
- safety_critical 必须是 absolute → 否则拒绝加载
- identity_critical + learnable 必须有审计配置
- 安全回落策略必须存在
- domain_of_validity 中引用的状态变量必须已在 DomainPack 中定义

---

### 3.7 JellyMCPClient (可选外部数据集成层)

**职责**：
- 封装 Jelly 15 个 MCP 工具为 Python 接口
- 管理 HTTP/SSE 连接（默认 `:9091`）和重试策略（指数退避 1s/2s/4s）
- 提供 mock 模式用于开发和测试（Jelly 不可用时 PT 仍可运行）
- 注入 caller 身份，执行二次视图过滤兜底（契约 Q10 双层保障）

**模块结构**：

```
src/polytwin/jelly/
├── __init__.py              # 公开 API: JellyClient, JellyConfig
├── client.py                # JellyClient — 15 工具 Python 封装
├── config.py                # JellyConfig 连接配置
├── protocol.py              # MCP HTTP/SSE 协议层
├── caller.py                # domain_id 双格式映射 + caller 注入
├── view_filter.py           # 二次视图过滤兜底
├── retry.py                 # 重试策略
├── mock.py                  # MockProvider（本地文件回退）
├── exceptions.py            # JellyError 层次结构
└── types.py                 # 返回类型（Pydantic 模型）
```

**接口契约**：

| 接口 | 输入 | 输出 | 权限 |
|------|------|------|------|
| get_domain_pack | (domain_id, caller) | JellyDomainPack or None | 所有组件 |
| search_domain_packs | (keywords, industry, equipment_type) | list[JellyDomainPackSummary] | 所有组件 |
| get_validation_set | (domain_id, set_type, caller) | JellyValidationSet or None | core, audit（lab 仅 public_eval） |
| get_exploration_data | (domain_id, data_release_id, caller) | JellyExplorationData | lab, core |
| get_failure_logs | (domain_id, time_range, severity, caller) | JellyFailureLogPackage | lab, core |
| query_domain_knowledge | (domain_id, query) | JellyKnowledgeAnswer | 所有组件 |
| get_physical_limits | (domain_id, variable) | list[JellyPhysicalLimit] | 所有组件 |
| get_equipment_spec | (domain_id, equipment_id) | JellyEquipmentSpec | 所有组件 |
| get_safety_standards | (domain_id, standard_ref) | JellySafetyStandard | 所有组件 |
| validate_data_alignment | (domain_id, data) | JellyAlignmentResult | 所有组件 |

**降级规则**：

| 场景 | 降级行为 |
|------|----------|
| Jelly 启动时不可达 | 记录告警，使用本地 YAML + mock 数据 |
| 运行中 Jelly 断连 | 重试 3 次（1s/2s/4s），失败后降级到 mock |
| 请求的 domain_id 在 Jelly 不存在 | 返回 None，上层使用本地版本 |
| 数据对齐失败 | 拒绝加载该条数据，记录审计日志 |

**详细设计**：见 `docs/superpowers/specs/2026-05-08-jelly-mcp-client-integration.md`

---

## 4. 视图隔离强制执行

**代码层**：TwinObject 内部数据通过 `_internal` 私有属性存储，外部只通过 `get_view(view_type, caller)` 获取 frozen 快照。

**CI 层**：静态分析扫描违规 import：
- `lab/` 不得 import `core.certification`, `core.evidence`, `core.audit`, `core.hardgate`
- `core/runtime.py` 和 `core/hardgate.py` 不得 import `core.certification`
- 出现即构建失败

**运行时层**：`CallerIdentity` 校验组件是否有权请求该视图类型，越权抛出 `PermissionDeniedError`。

**测试层**（M1-C2）：每个视图的每条可见性规则有正向和负向测试，覆盖率 ≥ 95%。

---

## 5. 里程碑对齐

| 里程碑 | Spec 对应 | 关键交付物 | 验收检查点 |
|--------|-----------|-----------|-----------|
| M0 | §3.6, §3.7 | 首个 DomainPack YAML + 知识库对接规范 + JellyConfig/client 骨架 + MockProvider | C1 配置完整性, C2 刚性-关键性兼容, mock 模式通过 |
| M1 | §3.1, §3.7 | TOM 数据结构 + 五种视图投影引擎 + 快照系统 + DomainPack 双源加载 | C1 字段完整性, C2 视图投影测试 ≥ 95%, C3 快照不可变, C4 写入权限矩阵 |
| M2 | §3.2, §3.3 | Core 四态约束验证 + HardGate + 安全回落 + 证据准入 + IdentityMonitor + Jelly 验证集集成 | C1 约束验证正确性, C2 safety_critical 优先中断, C3 安全回落 200ms, C4 item 级独立性, C5 反馈脱敏 |
| M3 | §3.4, §3.7 | Lab 沙箱 + 预筛函数库 + 提交链路 + Jelly 探索数据/失效日志集成 | C1 隔离验证, C2 预筛限权, C3 完整提交链路, C4 反馈不泄露隐藏集 |
| M4 | §3.5 | Bridge 四分类 + 有效期管理 + 人类响应 + 审计 | C1 分类正确性, C2 有效期管理, C3 exception_request ≠ override, C4 审计不可修改 |
| M5 | §2.1-2.5 | 端到端四场景闭环验证 + Jelly 集成测试（mock + 可选真实） | C1 全程自动化, C2 安全回落 < 200ms, C3 Bridge 更新 < 1s, C4 组件隔离有效 |
| M6 | §3.6, §3.7 | 三个场景 DomainPack + 跨场景零代码修改 + Jelly 多场景搜索 | C1 Core/Lab/Bridge 零 diff, C2 DomainPack 创建 < 1 工作日 |
| M7 | 全系统, §3.7 | 性能基准 + 安全渗透测试 + 文档 + Jelly MCP 安全测试 | C1 渗透全部被阻止, C2 性能达标, C3 文档完整 |

---

## 6. 工程质量标准

> 本节为所有里程碑的横切质量要求。每个 Task 的 TDD 步骤自动继承这些标准。

### 6.1 工具链

| 工具 | 用途 | 强制命令 |
|------|------|----------|
| Ruff | lint + format | `ruff check src/ tests/` 零 warning |
| mypy | 类型检查 | `mypy --strict src/` 零 error |
| pytest | 测试运行 | `pytest tests/ --tb=short` |
| pytest-cov | 覆盖率 | `pytest --cov=src/polytwin --cov-report=term-missing` |

commit 前必须全部通过。CI 管线强制执行，本地可通过 `pre-commit` 自动化。

### 6.2 测试覆盖率

| 模块 | 最低覆盖率 | 理由 |
|------|-----------|------|
| `core/` | ≥ 90% | 安全关键，零容忍 |
| `tom/` | ≥ 90% | 数据完整性关键 |
| `lab/` | ≥ 85% | 策略逻辑需充分覆盖 |
| `bridge/` | ≥ 85% | 决策逻辑需充分覆盖 |
| `api/` | ≥ 80% | 集成测试为主 |
| `jelly/` | ≥ 80% | mock 模式覆盖 |
| 整体 | ≥ 85% | 全项目底线 |

覆盖率不达标 = 该 Task 质量门控未通过。

### 6.3 测试质量标准

每个公开接口必须有 **三类测试**：

| 类型 | 要求 | 示例 |
|------|------|------|
| 正向测试 | 合法输入 → 正确输出 | temperature=150 在适用域内 → passed |
| 边界测试 | 边界值附近 → 行为正确 | temperature=180.0(上限)→passed; 180.01→failed |
| 异常测试 | 非法/缺失/越权 → 安全拒绝 | 缺失 caller → PermissionDeniedError |

**边界测试必检项：**
- 数值参数的上限、下限、零值
- 空列表/空字典/None 输入
- 权限矩阵每个交叉点（正向 + 反向）
- domain_of_validity 的"缺失变量"场景（应保守求值）

### 6.4 实现验证检查清单

每个 Task 完成前逐项确认：

```
□ ruff check src/ tests/ — 零 warning
□ mypy --strict src/ — 零 error
□ pytest tests/ — 全部 PASSED
□ pytest --cov — 覆盖率达标（§6.2）
□ 里程碑质量门控 — 对应 C1~Cn 全部通过
□ 无违规 import — check_import_isolation.py 通过（适用时）
```

任何一项未通过 = Task 未完成，不可 commit。

### 6.5 提交规范

**Commit message 格式：**

```
<scope>: <简述>

[可选：详细说明]
```

scope 选项：`core`, `tom`, `lab`, `bridge`, `api`, `jelly`, `domainpack`, `tests`, `docs`, `infra`, `chore`

示例：
- `core: add 4-state constraint evaluator with domain_of_validity`
- `tom: enforce view access matrix with frozen snapshots`
- `tests: add boundary tests for constraint evaluator`

**PR 粒度：**
- 一个 PR = 一个 Task（通常 1-3 个源文件 + 对应测试）
- 大 Task 例外：M10b 可拆分为两个 PR（CRUD 端点 + 集成测试）
- PR 描述包含：任务编号、测试清单、§6.4 检查清单结果

---

## 7. 审核修订记录

### v1.0.0 → v1.1.0
- 拆分通用/类型化双层模型
- Bridge 增加 ConstraintProhibition（含 prohibition_reason）
- ConstraintStatus 增加四态判决 + domain_of_validity 检查
- 视图系统从 4 种扩展为 5 种

### v1.1.0 → v2.0.0

| 审核意见 | 修订内容 |
|----------|----------|
| P0: 五闭环未定义 | 新增 §2，定义五个闭环的精确数据流、经过模块、终点、验收断言 |
| P0: domain_of_validity 未定义 | 新增 §3.6 适用域 schema（5 种条件类型 + 求值算法 + 假阴/假阳性防护） |
| P0: Lab 约束感知矛盾 | 新增 §3.4 约束感知方案：Core 导出无状态预筛函数库，Lab 调用但不作为权威结论 |
| P0: 身份连续性缺失 | 新增 §3.3 IdentityMonitor 模块（职责、数据流、参数、接口契约、验收断言） |
| P1: 代码蓝图过度详细 | 全文重构：移除 Python 类定义和伪代码，改为组件职责 + 接口契约 + 数据协议 + 验收标准 |

### v2.0.0 → v2.1.0

| 变更 | 修订内容 |
|------|----------|
| Jelly 契约集成 | 新增 §3.7 JellyMCPClient 组件定义（接口契约、降级规则、模块结构） |
| 外部知识来源 | §1 设计决策表新增"可选 Jelly MCP 集成"行 |
| 感知闭环增强 | §2.1 新增 Registry 双源加载（Jelly 优先 + 本地兜底） |
| 探索闭环增强 | §2.2 新增探索数据三来源（本地/Jelly 探索数据/Jelly 失效日志） |
| 决策闭环增强 | §2.3 新增验证集双来源 + 二次视图过滤兜底 |
| 演化闭环增强 | §2.5 新增领域知识增强来源（Jelly 知识查询/物理极限） |
| 里程碑更新 | §5 对齐表更新：M0-M7 增加 Jelly 集成交付物 |
| 详细设计 | 引用独立文档 `2026-05-08-jelly-mcp-client-integration.md` |

### v2.1.0 → v2.2.0

| 变更 | 修订内容 |
|------|----------|
| 新增 §6 | 工程质量标准：工具链(ruff+mypy+pytest)、测试覆盖率(核心≥90%)、测试质量(三类测试)、实现验证检查清单、提交规范 |
