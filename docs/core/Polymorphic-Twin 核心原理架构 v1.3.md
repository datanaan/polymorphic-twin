# Polymorphic-Twin 核心原理架构 v1.3

**约束治理下的可证伪数字孪生基础设施**

---

## 〇、版本修订说明：v1.2 → v1.3

本版本不重构核心方向，只关闭 `v1.2` 中剩余的架构边界漏洞。

| 修改项 | v1.2 问题 | v1.3 修正 |
|---|---|---|
| `suspended` 约束处理 | 约束挂起后一律允许继续运行，可能绕过安全关键约束 | 引入 `criticality`，安全关键约束挂起时关闭 `production` |
| 链路权限 | `production > diagnostic > shadow > sandbox` 被建成线性层级 | 改为权限矩阵，区分输出、控制、学习、影子、真实数据访问 |
| 证书缺失 | 不确定性证书缺失时仍允许低置信 `production` | 按任务风险分级处理，安全相关输出必须有有效证书 |
| `SafeFallbackPolicy` | 缺少自身适用域、已验证初始集、安全不变集 | 增加 `domain_of_validity`、`verified_initial_set`、`invariant_safe_set`、`unavailable_action` |
| `sandbox` 与主动探测 | `sandbox` 同时包含离线实验和真实主动探测 | 拆分为 `offline_sandbox` 与 `physical_probe` |
| 主动探测 | 缺少信息收益、可逆性和终止条件 | 扩展 `ActiveProbe Certificate` |
| 验证器可信度 | `certifier` 自身未被审计 | 增加验证器版本、适用域、假设、失效模式 |
| 身份连续性 | `TwinLineage` 在 v1.2 中被压缩 | 恢复最小身份谱系结构 |

---

## 一、孪生对象定义

数字孪生的根本问题不是预测未来状态，而是：

> 在目标系统经历变化时，什么构成了“它仍然是同一个系统”的连续性？

本框架定义数字孪生的本体对象为：

> **系统身份在变化中的连续性** —— 在状态演化、参数漂移、结构变迁、环境扰动、外部干预下，维持可识别、可解释、可干预的“同一系统”语义的最小不变结构。

该不变结构由以下支柱共同承托：

1. **状态语义定义**  
   每个状态变量测量什么，单位是什么，范围是什么，是否可观测、可估计、可控制。

2. **约束体系**  
   包括物理、生理、安全、逻辑、因果、工艺、量纲和边界约束。

3. **观测-干预接口规范**  
   包括观测精度、采样频率、延迟、可操控量、控制输入范围、执行器限制。

4. **身份不变量集合**  
   包括审计基准集、安全边界、误差评估协议、状态语义版本、决策追溯记录。

数字孪生的工程任务是：

> 在这些不变结构约束下，建立并持续维护一个可证伪的动态表征。

---

## 二、最高价值：可证伪性

本框架的最高价值不是预测精度、控制性能、模型复杂度或计算效率，而是：

> **可证伪性**：孪生体必须能够判定自己在什么情况下可能是错的，并在出错时执行安全退化行为。

如果一个数字孪生无法定义自己的失败条件，它就是不可证伪的，因而在核心原理上不成立。

价值排序如下：

1. 安全边界；
2. 约束一致性；
3. 身份连续性；
4. 可证伪性与可退化性；
5. 预测精度；
6. 控制性能；
7. 计算效率；
8. 自动进化能力。

---

## 三、约束体系的结构化定义

### 3.1 Constraint Card

每一条约束必须被声明为结构化约束卡片。

```text
Constraint Card = {
  id,
  name,
  expression,
  rigidity: absolute | soft | learnable,

  criticality: safety_critical | identity_critical | operational | informational,

  domain_of_validity,
  required_observables,
  tolerance,

  violation_hypotheses: ordered_list of {
    hypothesis,
    priority,
    diagnostic_test,
    evidence_required,
    safety_response
  },

  certifier: {
    certifier_id,
    certifier_version,
    certifier_domain,
    certifier_assumptions,
    certifier_failure_mode,
    certifier_audit_record,
    execute(input) -> {pass, uncertain, fail, not_applicable}
  },

  fallback_action,
  audit_level: hard_gate | risk_gate | utility_gate
}
```

### 3.2 刚性分级

#### 绝对约束

不可被学习系统修改。  
但绝对约束必须具备：

- 明确适用域；
- 所需观测变量；
- 容差；
- 可执行验证器；
- 失效处理协议。

没有这些字段的约束，不能进入硬门槛，只能作为偏好约束或声明式元约束。

#### 偏好约束

可以软化，但必须：

- 显式声明；
- 记录修改历史；
- 说明软化原因；
- 不得覆盖安全关键约束。

#### 可学习约束

可从数据中估计，例如摩擦系数、阻尼参数、代谢率。  
但必须有：

- 学习率上限；
- 变化范围；
- 漂移检测；
- 回滚机制。

---

## 四、约束状态与挂起规则

约束验证器输出四值状态：

```text
pass            当前域内满足
uncertain       观测不足，无法判定
fail            当前域内明确违反
not_applicable  当前状态不在约束适用域内
```

当约束返回 `not_applicable` 时，进入 `suspended` 状态。

但 `suspended` 的后果取决于 `criticality`。

| criticality | suspended 后果 |
|---|---|
| `safety_critical` | 关闭 `production`，触发 `safe_fallback` 或安全接管 |
| `identity_critical` | 进入身份不确定状态，冻结自适应与自动上线 |
| `operational` | 可继续运行，但相关模型降权，输出必须显式标注 |
| `informational` | 仅记录，不影响链路权限 |

原则：

> `suspended` 不等于软化，不等于放弃，也不等于系统可以无条件继续生产输出。

---

## 五、数据与约束冲突诊断协议

当观测数据与绝对约束冲突，即验证器返回 `fail` 时，系统不得立即学习该冲突，也不得立即放弃约束，而必须进入诊断流程。

诊断顺序：

1. 检查约束适用域；
2. 检查观测完整性；
3. 检查传感器健康；
4. 根据 `violation_hypotheses` 执行假设检验；
5. 检查是否存在未建模外部通量或隐变量；
6. 检查是否发生身份断裂；
7. 检查是否进入不可辨识状态。

诊断结果：

| 诊断结果 | 动作 |
|---|---|
| 传感器/观测问题 | 标记观测不可信，降级到安全保守模式 |
| 约束适用域失效 | 约束进入 `suspended`，触发约束卡片审查 |
| 隐变量/外部通量 | 标记模型不完备，触发观测扩展或模型修订 |
| 身份断裂 | 触发 `identity_branch` 或 `identity_rebuild` |
| 无法区分 | 进入身份不确定状态，冻结控制和自适应 |

若连续 \(N\) 步无法消解冲突：

> 关闭 `production`，进入冻结诊断模式，请求人工或上层知识介入。

---

## 六、可观测性与可辨识性原则

### 6.1 原理

系统退化与模型漂移的区分不是无条件可判定的。

当观测证据不足以区分以下情形时：

- 真实系统退化；
- 模型失效；
- 传感器漂移；
- 外部扰动；
- 控制输入分布变化；
- 约束适用域变化；
- 身份断裂；

框架不得给出确定身份判断，必须进入：

```text
identity_uncertain_state
```

该状态下：

- 冻结自适应学习；
- 禁止自动模型上线；
- 暂停非安全控制；
- 保留全部证据链；
- 允许请求主动探测或人工判定。

### 6.2 主动探测

当可辨识性不足时，系统可以请求主动探测，但主动探测属于受限控制行为，不属于自由沙盒实验。

必须持有：

```text
ActiveProbe Certificate = {
  probe_id,
  objective_hypotheses,
  signal_form,
  amplitude_bounds,
  duration_max,

  probe_domain_of_validity,
  expected_information_gain,
  reversibility,
  max_allowed_risk,
  abort_condition,

  safe_hold_policy,
  approval_required: human | automatic,
  certifier
}
```

主动探测必须满足：

1. 不违反安全关键约束；
2. 位于 `probe_domain_of_validity` 内；
3. 具备可逆性或可安全回落；
4. 预期信息收益超过风险阈值；
5. 具备明确中止条件；
6. 绑定 `SafeFallbackPolicy`。

若无法设计安全探测信号：

> 标记“当前可辨识性不足且无法安全探测”，进入冻结并请求人工。

---

## 七、模型资格函数 Q

### 7.1 总体结构

模型资格函数不再输出单一等级，而是输出权限矩阵。

```text
Q(m, s, T, C) =
  HardGate(m, s, T, C)
  -> RiskGate(m, s, T, C)
  -> UtilityRank(m, s, T, C)
```

其中：

- `m`：候选模型；
- `s`：当前系统状态域；
- `T`：任务上下文；
- `C`：当前有效约束集。

### 7.2 LinkPermission 权限矩阵

```text
LinkPermission = {
  can_output_prediction: bool,
  can_output_diagnostic: bool,
  can_affect_control: bool,
  can_run_shadow: bool,
  can_run_offline_sandbox: bool,
  can_train_or_evolve: bool,
  can_access_live_data: bool,
  can_request_physical_probe: bool,
  can_upgrade_without_human: bool
}
```

原则：

> `production`、`diagnostic`、`shadow`、`sandbox` 不是线性层级，而是不同权限维度的组合。

例如：

- 某模型可 `shadow`，但不可对外 `diagnostic`；
- 某模型可 `diagnostic`，但不可控制；
- 某模型可离线 `sandbox`，但不可访问实时数据；
- 某模型可生产预测，但不可生产控制；
- 某模型可请求主动探测，但必须额外通过探测证书审查。

### 7.3 HardGate

`HardGate` 负责不可妥协的资格判定。

硬门槛包括：

1. 状态语义兼容；
2. 约束适用域匹配；
3. 所需观测变量满足任务要求；
4. 安全关键约束未被 `fail`；
5. 安全关键约束未被危险 `suspended`；
6. 任务接口匹配；
7. 控制任务具备干预接口；
8. 主动探测任务具备 `ActiveProbe Certificate`；
9. 自主控制具备稳定性或安全证书；
10. 输出可被约束验证器审查。

若硬门槛失败：

- 生产链路关闭；
- 可根据失败类型允许 `shadow` 或 `offline_sandbox`；
- 安全关键失败不得进入任何影响现实的链路。

### 7.4 RiskGate

`RiskGate` 不决定模型是否“存在”，而决定模型可以在多大风险等级下使用。

风险项包括：

1. 不确定性证书有效性；
2. OOD 程度；
3. 可辨识性置信度；
4. 历史失效率；
5. 身份一致性；
6. 控制风险上界；
7. 约束验证器置信度；
8. 数据新鲜度；
9. 证书是否过期；
10. 当前任务是否安全关键。

风险结果：

| 风险状态 | 允许行为 |
|---|---|
| 低风险 | 可进入对应生产链路 |
| 中风险 | 降权、标注、不允许自主控制 |
| 高风险 | 仅诊断或影子 |
| 不可判定 | 进入身份不确定或安全回落 |

### 7.5 UtilityRank

只有在模型通过 `HardGate` 和 `RiskGate` 后，才进入效用排序。

效用指标：

- 预测精度；
- 计算成本；
- 可解释性；
- 约束残差；
- 控制收益；
- 历史稳定性；
- 任务相关性。

原则：

> 效用排序不得覆盖硬门槛或风险门槛。

---

## 八、不确定性证书

框架不允许使用模型自报的未校准不确定性作为安全依据。

```text
Uncertainty Certificate = {
  certificate_id,
  calibration_set,
  confidence_level,
  coverage_guarantee,

  distribution_assumption,
  data_dependence_model,
  exchangeability_condition,

  domain,
  closed_loop_domain,
  intervention_domain,

  expiry_condition,
  certifier_method,
  issuer,
  audit_record
}
```

### 8.1 证书缺失处理

| 任务类型 | 证书缺失/过期时 |
|---|---|
| `autonomous_control` | 禁止生产控制，触发 `safe_fallback` 或降至诊断 |
| `supervised_control` | 不得直接控制，仅可请求人类确认 |
| `advisory` | 可输出，但必须标记“无安全证书，仅供参考” |
| 低风险预测 | 可低置信输出，但不得进入控制链路 |
| 安全关键诊断 | 可告警，但必须标记证据等级 |

原则：

> 安全相关输出必须持有当前域内有效证书。  
> 低风险解释性输出可以无证书，但必须显式标注。

---

## 九、控制任务分级与干预有效性

### 9.1 控制等级

```text
Control Level = advisory | supervised | autonomous
```

| 等级 | 定义 |
|---|---|
| `advisory` | 输出仅供人类参考，不直接驱动物理执行器 |
| `supervised` | 模型输出可驱动执行器，但人类或独立安全控制器可接管 |
| `autonomous` | 模型输出直接驱动物理执行器，人类不在实时回路中 |

### 9.2 控制资格要求

| 要求项 | advisory | supervised | autonomous |
|---|---|---|---|
| HardGate | 必须 | 必须 | 必须 |
| 不确定性证书 | 建议 | 强制 | 强制，且闭环有效 |
| 干预有效性 | 建议 | 强制 | 强制 |
| 稳定性/安全证书 | 不需要 | 建议或安全控制器覆盖 | 强制 |
| SafeFallbackPolicy | 不需要 | 强制 | 强制 |
| 人类接管延迟 | 不适用 | 必须定义 | 若依赖人类则必须定义，否则不允许 |

### 9.3 干预有效性审查

控制模型必须证明其不仅能预测，还能在干预条件下保持有效。

审查项：

1. 控制输入是否具有充分激励；
2. 是否能区分相关性与因果性；
3. 是否有干预分布下的数据；
4. 是否在不同控制律下验证过；
5. 是否存在反事实有效性证据；
6. 是否具备安全动作集；
7. 闭环策略是否有安全证书。

### 9.4 稳定性或安全证书

```text
StabilityOrSafetyCertificate = {
  certificate_id,
  type: lyapunov | reachability | barrier | invariant_set | certified_safe_policy,
  domain_of_validity,
  assumptions,
  verifier,
  robustness_margin,
  expiry
}
```

对于 `autonomous` 控制：

> 没有稳定性或安全证书，模型权限不得超过诊断链路。

---

## 十、安全回落策略

### 10.1 原则

不再接受“最后安全动作默认安全”或“维持当前控制策略默认安全”。

所有系统配置必须绑定预先验证的：

```text
SafeFallbackPolicy
```

### 10.2 SafeFallbackPolicy 结构

```text
SafeFallbackPolicy = {
  policy_id,

  domain_of_validity,
  verified_initial_set,
  invariant_safe_set,
  robustness_margin,

  trigger_conditions,
  target_state,
  trajectory_constraints,

  completion_certificate,
  max_duration,

  unavailable_action: human_takeover | safe_shutdown | freeze,
  post_fallback_action: hold | handoff_to_human | shutdown
}
```

### 10.3 回落策略要求

回落策略必须说明：

1. 从哪些初始状态验证过；
2. 在哪些扰动范围内有效；
3. 回落过程中是否保持在安全不变集；
4. 何时认为回落完成；
5. 回落失败时执行什么动作。

如果当前状态不在 `verified_initial_set` 或 `domain_of_validity` 内：

> 不得假设回落可达，必须触发 `unavailable_action`。

---

## 十一、sandbox、shadow 与 physical_probe

### 11.1 离线沙盒

```text
offline_sandbox
```

只允许：

- 仿真；
- 历史数据回放；
- 离线结构搜索；
- 离线模型变异；
- 离线约束压力测试。

特征：

- 不影响物理世界；
- 不输出生产决策；
- 不访问执行器；
- 结果迁出必须重新验证。

### 11.2 影子链路

```text
shadow
```

允许模型在后台运行，与生产模型比较，但：

- 不对外输出；
- 不影响控制；
- 不触发执行器；
- 可用于收集评估证据。

### 11.3 真实主动探测

```text
physical_probe
```

真实主动探测不是沙盒，而是受限控制行为。

必须同时满足：

1. `ActiveProbe Certificate`；
2. 控制资格审查；
3. 安全关键约束通过；
4. `SafeFallbackPolicy` 绑定；
5. 必要时人类批准。

原则：

> 任何接触真实物理系统的探测，都不属于自由沙盒。

---

## 十二、进化机制边界

### 12.1 进化只允许在隔离域中自由探索

进化算法可以在 `offline_sandbox` 中生成违反约束的候选模型。

但任何候选模型迁出沙盒时，必须逐级验证。

### 12.2 权限迁移

```text
offline_sandbox -> shadow:
  通过 HardGate(shadow) + 基础约束验证

shadow -> diagnostic:
  通过 HardGate(diagnostic) + 风险关键项

diagnostic -> production:
  通过 HardGate(production) + RiskGate + 必要证书

production_prediction -> production_control:
  额外通过干预有效性和控制安全证书
```

迁移失败：

- 保留在当前链路；
- 记录失败原因；
- 不自动上线；
- 不自动回滚生产模型。

### 12.3 进化承诺

框架不承诺：

> 进化不会产生违反硬约束的候选模型。

框架只承诺：

> 未通过当前链路资格验证的进化产物，不得离开其隔离链路影响真实决策。

---

## 十三、身份连续性与 TwinLineage

### 13.1 身份演化类型

```text
Identity Event = version_update | identity_branch | identity_rebuild
```

| 类型 | 含义 |
|---|---|
| `version_update` | 身份连续，参数或模型更新，不改变状态语义和核心约束 |
| `identity_branch` | 身份发生结构性变化，但与旧身份有可追溯关系 |
| `identity_rebuild` | 旧身份不再适用，需要重新定义状态语义和约束体系 |

### 13.2 TwinLineage

```text
TwinLineage = {
  twin_id,
  parent_twin,

  event_type: version_update | identity_branch | identity_rebuild,
  branch_event,

  inherited_invariants,
  broken_invariants,
  new_identity_scope,

  audit_benchmark,
  current_validation_set,

  state_semantics_version,
  constraint_set_version,
  safety_boundary_version,

  timestamp,
  approval_record
}
```

### 13.3 基准集分离

```text
audit_benchmark
```

不可变，用于历史追溯和身份证明。

```text
current_validation_set
```

可版本化更新，用于当前模型资格判断。

原则：

> 不能用当前验证集替代历史审计基准。  
> 不能为了让新模型通过而静默修改身份基准。

---

## 十四、链路权限架构

本框架定义以下运行链路：

| 链路 | 作用 | 是否影响物理世界 |
|---|---|---|
| `production_prediction` | 生产预测 | 间接影响 |
| `production_diagnostic` | 生产诊断/告警 | 间接影响 |
| `production_control` | 生产控制 | 直接影响 |
| `diagnostic_only` | 仅诊断 | 否 |
| `shadow` | 后台评估 | 否 |
| `offline_sandbox` | 离线实验/进化 | 否 |
| `physical_probe` | 真实主动探测 | 是 |
| `safe_fallback` | 安全回落 | 是 |
| `human_takeover` | 人工接管 | 是 |

任何模型或策略进入对应链路前，必须获得相应权限。

---

## 十五、失败理论

### 15.1 运行时失败条件

| 失败条件 | 响应 |
|---|---|
| 安全关键约束 `fail` | 关闭 `production_control`，执行 `safe_fallback` |
| 安全关键约束 `suspended` | 关闭相关生产链路，进入安全审查 |
| 身份关键约束 `suspended` | 进入身份不确定状态 |
| 所有模型无生产资格 | 降级至诊断/影子，必要时 `safe_fallback` |
| 证书缺失且任务安全相关 | 禁止生产输出 |
| 不确定性超出安全阈值 | 关闭控制，执行安全保持或接管 |
| 数据与约束持续冲突 | 冻结学习，进入诊断，请求人工 |
| 主动探测失败 | 中止探测，执行安全回落 |
| 进化产物无法通过验证 | 停留在沙盒，不释放 |
| SafeFallbackPolicy 不适用 | 执行 `unavailable_action` |

### 15.2 退化行为

从轻到重：

1. 标注低置信；
2. 降级至诊断；
3. 关闭生产控制；
4. 安全保持；
5. 控制移交；
6. 安全停机；
7. 冻结自适应；
8. 人工接管；
9. 身份分叉或重建。

---

## 十六、能力边界

### 16.1 本框架保证

1. 不释放未通过对应链路权限审查的输出；
2. 不释放未通过当前域约束验证的安全相关输出；
3. 证书缺失时不进入安全相关生产链路；
4. 进化产物离开隔离链路前必须重新验证；
5. 生产链路失效时执行预先声明的退化协议；
6. 所有链路迁移、资格判定、证书状态、约束状态可追溯。

### 16.2 本框架不保证

1. 多模型融合一定优于最佳单模型；
2. 进化一定收敛；
3. 所有系统都能找到生产级模型；
4. 约束稀疏或观测不足时仍能有效运作；
5. `SafeFallbackPolicy` 在所有物理工况下可达；
6. 验证器永远正确；
7. 主动探测一定能获得足够信息；
8. 身份连续性在观测不足时一定可判定。

### 16.3 本框架不是

- 物理仿真引擎；
- 大语言模型；
- 自动机器学习平台；
- 开箱即用工具；
- 直接替代底层安全控制器的系统；
- 在无约束、无观测、无验证基准场景下仍可靠的万能框架。

---

## 十七、守门原则总结

1. **孪生本体优先**  
   孪生对象是系统身份连续性，不是单纯状态预测。

2. **状态语义先于模型骨架**  
   先定义状态、观测、控制、约束，再选择模型。

3. **约束为最高秩序**  
   但约束必须结构化，具备适用域、验证器和关键性分级。

4. **约束挂起不是软化**  
   `suspended` 的后果由 `criticality` 决定。

5. **仲裁是资格审判**  
   模型必须通过 `HardGate / RiskGate / UtilityRank`。

6. **链路权限不是线性等级**  
   必须用权限矩阵区分输出、控制、学习、影子、探测。

7. **控制资格强于预测资格**  
   预测通过不代表可以控制。

8. **安全相关输出必须有证书**  
   证书缺失只能进入低风险或诊断链路。

9. **主动探测是受限控制行为**  
   不属于自由沙盒。

10. **进化只在隔离链路中自由**  
    任何迁出都必须重新验证。

11. **安全回落必须有适用域**  
    不能假设全域可达。

12. **身份变化必须可追溯**  
    区分版本更新、身份分叉、身份重建。

13. **框架必须知道何时退下**  
    可证伪性和退化能力是完整性的一部分。

---

## 十八、最终定位声明

`Polymorphic-Twin v1.3` 是一个：

> **约束治理下的、可证伪的、链路权限矩阵化的数字孪生基础设施。**

它以：

- 系统身份连续性为孪生对象；
- 结构化约束卡片为最高秩序；
- 权限矩阵化资格函数为模型仲裁机制；
- 证书化不确定性为安全门槛；
- 干预有效性审查为控制前提；
- 适用域明确的安全回落策略为最后防线；
- 离线沙盒隔离进化为持续改进空间；
- 身份谱系管理为连续性保证。

它不承诺永不犯错。

它承诺：

> 每个输出都知道自己来自哪个链路，经过了什么验证，拥有什么证书，在哪些适用域内有效，何时必须撤回；当所有生产链路失效时，系统知道应当降级、冻结、回落、停机、分叉，或请求人工接管。
