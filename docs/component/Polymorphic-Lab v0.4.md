Polymorphic-Lab v0.4

探索证据供应链系统——核心原则稿（定稿版）

〇、版本说明
v0.4 是 Polymorphic-Lab 核心原则的定稿版。相比 v0.3，本次修订仅闭合剩余的系统级边界问题，不新增模块，不展开架构细节。具体修改：

修改项	内容
新增原则11	Lab产物进入Core前必须通过检疫
新增原则12	Core对Lab的反馈必须限制粒度，不泄露审判机制
新增原则13	Lab必须接受探索健康度监控
NegativeResultPackage 扩展	增加 confidence_level、alternative_explanations、expiration_condition
数据撤回传播规则	派生物治理规则中增加撤回传播条款
成功指标去信息泄漏	验证方式列不再暴露 hidden_challenge_set 的 membership
ScenarioPackage 定义	在模块四中补充反事实场景证据包结构
反馈隔离原则	新增两句话原则，声明反馈不包含隐藏集信息且可能被脱敏
一、系统B的定位
Polymorphic-Lab 是一个与物理世界完全隔离的探索证据供应链系统。它的产出不是真理，不是上线模型，不是约束定律——而是经过初步筛选的、可复现的、可被独立审判的探索证据包。

Lab 永远是证据生成者、反例发现者、未知域扩展者、失败模式挖掘者。

Lab 永远不是证书颁发者、约束制定者、生产模型上线者、真实探测执行者、隐藏验证集访问者。

Lab 的成功是：Core 因为 Lab 的证据而更清楚自己不知道什么。

二、隔离探索宪法（十三条）
原则1：Lab只提出，不释放
Lab 的任何产出只能提交到 Core 的 sandbox 链路。从 sandbox 向上的迁移，必须由 Core 独立执行完整的 HardGate + RiskGate。

原则2：Lab只生成证据包，不生成证书
Lab 可生成 UncertaintyEvidencePackage、ActiveProbeProposal、ConstraintHypothesis。证书只能由 Core 的 Certifier Registry 或授权人工签发。

原则3：Lab只生成约束假设，不生成绝对约束
Lab 产出的是 ConstraintHypothesisPackage——包含支持证据、反证据、可证伪测试、混杂因素分析。约束卡片只能由 Core 在人工审查后生成。Lab 无权建议 rigidity 级别高于 soft。

原则4：Lab不可访问隐藏验证基准
建立验证防火墙，Lab 永远不可见：audit_benchmark、hidden_challenge_set、production_acceptance_suite、heldout_redteam_scenarios。

原则5：Lab不可执行真实主动探测
Lab 只能生成 ActiveProbeProposal。真实物理探测必须由 Core 经过 ActiveProbe Certificate + SafeFallbackPolicy + Control Qualification 后执行。

原则6：Lab数据输入必须是DataReleasePackage
Lab 不能直接读取生产数据库或原始传感器流。每个数据集必须是经过正式审计的 DataReleasePackage。Lab 不拥有数据，只租用被授权的数据视图。

原则7：Lab产物必须可复现
每个提交到 Core sandbox 的产物必须携带完整的可复现信息：数据 lineage、随机种子、目标函数、计算预算、已知失败案例、约束违反报告。

原则8：Lab成功不等于进入 production
Lab 成功的核心定义是扩展知识边界：发现新失效模式、提高验证集覆盖、降低生产模型不确定性、生成可证伪假设、减少“未知域”。

原则9：Lab的派生物也受数据治理
任何从 DataReleasePackage 派生的数据必须绑定到原始包的 lineage，继承其使用限制和保留策略。原始包过期或被撤回时，其所有派生物和依赖产物同步失效或标记为 invalidated。

原则10：Lab必须主动搜索反例与负面结果
Lab 必须投入指定比例的资源专门用于寻找现有模型的失效案例、复现已发现的失效模式、验证约束假设是否可证伪、生成负面结果。负面结果和反例发现同样是 Lab 的成功产出。

原则11（新增）：Lab产物进入Core前必须通过检疫
Lab 提交到 Core sandbox 的任何产物必须经过检疫扫描（恶意代码、敏感信息泄露、资源异常）。检疫未通过的产物不得进入 Core 的任何链路。检疫结构和扫描策略在架构设计中定义。

原则12（新增）：Core对Lab的反馈必须限制粒度
Core 可以向 Lab 返回产物的接收状态和简要拒绝原因摘要，但：

不得向 Lab 暴露 hidden_challenge_set、audit_benchmark、production_acceptance_suite 中的任何信息

不得告知 Lab 某个发现是否命中了隐藏验证集

拒绝原因可能被聚合、延迟或脱敏后反馈
Lab 的成功指标验证方式中，不包含任何隐藏集的 membership 判定信息。

原则13（新增）：Lab必须接受探索健康度监控
必须监控 Lab 是否出现候选同质化、公开集过拟合、负结果率异常下降、预算分配严重偏离。具体健康度量在架构设计中定义。当健康度持续恶化时，Lab 的提交权限可被降级。

三、六大模块 + 场景定义
模块一：数据释放与使用治理
设计原则：Lab 不拥有数据。它只租用被授权的数据视图。派生物也受治理。撤回可传播。

DataReleasePackage（完整结构）
text
DataReleasePackage = {
  dataset_id,
  source,
  deidentification_method,
  aggregation_level,
  permitted_tasks,
  forbidden_tasks,
  privacy_risk_assessment,
  retention_policy,
  synthetic_or_real,
  lineage,
  expiry,
  issued_by,
  audit_hash,
  allowed_derivatives,
  derivative_retention_policy,
  cross_package_join_allowed,
  export_policy,
  membership_inference_risk
}
派生物治理规则（含撤回传播）
任何从 DataReleasePackage 派生的数据，必须在 lineage 中声明 derivative_of 字段，指向原始包。

派生物继承原始包的 permitted_tasks、forbidden_tasks、retention_policy。

原始包过期或被撤回时，其所有派生物同步失效。所有依赖该数据包的证据包、候选模型、约束假设、场景必须标记为 invalidated 或 requires_revalidation。 撤回传播的具体机制在架构设计中定义。

Lab 实例终止时，所有 DataReleasePackage 及其派生物必须按保留策略处置。

跨包关联仅在双方包的 cross_package_join_allowed 均为 true 时允许。

模块二：验证防火墙与评估集生命周期
设计原则：公开评估集可训练可筛选，但不能作为最终泛化证据。隐藏集永不暴露。新生产失败先隔离审查。公开集过期后仅作回归测试。

评估集生命周期结构
text
EvaluationSetLifecycle = {
  public_eval_set,
  rotating_public_eval_set,
  stale_eval_set,
  hidden_challenge_set,       // Lab永远不可见
  quarantine_set,             // 新失败先隔离
  release_policy,             // 从quarantine释放到public的条件
  retirement_policy,          // 公开集退役条件
  release_approval: human_required
}
评估集流转规则
text
新生产失败案例 → quarantine_set → (审查+人工批准) → rotating_public_eval_set → public_eval_set → (过期) → stale_eval_set
关键约束：

hidden_challenge_set：无论何时都不向 Lab 开放

quarantine_set：新失败案例必须先完成安全审查

release_approval：从 quarantine 释放必须人工批准

retirement_policy：公开集过期后降级为 stale_eval_set，Lab 不能再将其作为模型筛选的性能依据

模块三：失败日志治理
设计原则：失败日志不是自由资源，而是高敏感探索燃料。

FailureLogReleasePackage
text
FailureLogReleasePackage = {
  log_id,
  source_event_type,
  redaction_method,
  privacy_risk_assessment,
  security_risk_assessment,
  released_fields,
  withheld_fields,
  permitted_analysis,
  expiry,
  lineage,
  audit_hash
}
释放规则
任何生产失败事件在释放给 Lab 前，必须经过隐私和安全风险评估。

暴露系统脆弱性的失败事件，必须先修补后决定是否释放。

包含可追溯个体信息的失败事件，必须脱敏且排除所有准标识符。

Lab 对 FailureLogReleasePackage 的分析仅限于 permitted_analysis 声明的范围。

失败日志过期后，Lab 必须按 expiry 处置。

模块四：候选产物证据包
设计原则：Lab 输出的一切必须可审计、可复现、可拒绝。包括负面结果包和反事实场景包。

六类证据包
证据包	用途
CandidateModelPackage	候选模型
ConstraintHypothesisPackage	约束假设
UncertaintyEvidencePackage	不确定性证据
ActiveProbeProposal	主动探测提案
NegativeResultPackage	负面结果
ScenarioPackage	反事实场景
NegativeResultPackage（v0.4 扩展）
text
NegativeResultPackage = {
  target,
  negative_claim,
  evidence,
  reproduction_recipe,
  scope,
  confidence_level,              // v0.4新增：证据强度（high/medium/low/insufficient）
  search_budget_coverage,        // v0.4新增：搜索覆盖度
  alternative_explanations,      // v0.4新增：该负面结果可能的替代解释
  expiration_condition,          // v0.4新增：该结论可能失效的条件
  falsification_of_negative_result, // v0.4新增：如何证伪这个负面结果本身
  implication_for_core,
  recommended_stop_condition     // 建议的停止条件，非永久封死
}
规则：负面结果不能永久封死方向，只能在声明的 scope 和 expiration_condition 内降低探索优先级。

ScenarioPackage（v0.4 新增定义）
text
ScenarioPackage = {
  scenario_id,
  generation_method,
  scenario_description,
  source_data_lineage,
  physical_plausibility_basis,
  constraint_violation_status,
  domain_gap_estimate,
  models_divergence_score,
  safety_relevance_selfcheck,
  reproducibility_recipe
}
CoreCompatibilityPrecheck 限权声明
CoreCompatibilityPrecheck 仅检验提交包的格式完整性、必填字段齐全、数据 lineage 可追溯、可复现信息完整。它不具有资格判定效力。Core 的 HardGate 是唯一权威判决。 它不检验约束满足、不确定性水平或物理合理性。

模块五：探索空间治理
设计原则：探索可以自由，但提交必须报告约束状态。

三层探索空间
空间	约束规则	产物去向
unconstrained_hypothesis_space	无约束限制，允许违反一切	内部探索，不直接提交 Core
constraint_aware_candidate_space	不强制满足约束，但必须报告违反了什么	筛选后打包为证据包
submission_precheck_space	运行 CoreCompatibilityPrecheck	通过后提交 Core sandbox
流转规则
不受限空间中生成的候选，必须进入约束感知空间完成约束违反检测和报告。

约束违反报告完整的候选进入提交预检空间。CoreCompatibilityPrecheck 只检查完整性和可复现性。

通过预检的产物提交 Core sandbox。之后一切由 Core 独立处理。

模块六：探索预算分配
设计原则：Lab 不能只做 Core 的“提问回答机”。

预算分配
text
ExplorationBudgetAllocation = {
  priority_driven: 40%,
  open_ended_search: 25%,
  adversarial_counterexample_search: 25%,
  replication_and_negative_results: 10%
}
硬约束：open_ended_search 不低于 15%，adversarial_counterexample_search 不低于 15%。

四、Lab 与 Core 的接口
系统A → 系统B
text
ExplorationContext = {
  state_semantics,
  constraint_cards,
  registered_models_public_info,
  available_data_packages,
  active_invariants,
  exploration_budget_allocation,
  priority_questions,
  public_eval_set,
  stale_eval_set,
  released_failure_log_packages
}
Lab 不可见：hidden_challenge_set、quarantine_set（未释放部分）、production_acceptance_suite、audit_benchmark、A/B盲测标签、未发布的主动探测结果。

系统B → 系统A
text
ExplorationOutput = {
  candidate_models: list of CandidateModelPackage,
  constraint_hypotheses: list of ConstraintHypothesisPackage,
  uncertainty_evidence: list of UncertaintyEvidencePackage,
  active_probe_proposals: list of ActiveProbeProposal,
  negative_results: list of NegativeResultPackage,
  candidate_scenarios: list of ScenarioPackage,
  exploration_summary: {
    budget_consumed_per_category,
    structures_searched,
    hypotheses_generated,
    hypotheses_falsified,
    failure_modes_discovered,
    negative_results_produced,
    unknown_domains_identified,
    data_packages_used,
    resources_consumed
  }
}
所有产出在进入 Core sandbox 前必须通过检疫（原则11）。 Core 独立决定链路升级。

五、Lab 成功指标（v0.4 去信息泄漏版）
Lab 成功的核心定义是扩展了系统生态的知识边界。

指标	定义	验证方式
发现新失效模式	反例或负面结果暴露了在已有验证集中未被发现的模型失效	Core 内部确认，仅向Lab返回"已记录"信号，不暴露是否命中隐藏集
提高验证集覆盖	Lab 生成的场景被 Core 采纳为 public_eval_set 扩展	Core 记录评估集版本变更，Lab 可见采纳结果（不涉及隐藏集）
降低生产模型不确定性	Lab 产出的校准证据使 Core 中至少一个模型的证书有效域扩展	Core 的 Certifier Registry 记录
生成可证伪的约束假设	约束假设包含清晰的可证伪测试且被检验	Core 的约束审查日志
减少 Core 的“未知域”	Core 在某个状态域从“无知状态”升级为“至少有一个 diagnostic 模型”	Core 链路状态变更记录
提交被拒绝但有价值的证据	候选模型被 HardGate 拒绝，但其失败原因指向 Core 约束或风险门槛的改进点	Core 审计记录
证明某条路不该走	NegativeResultPackage 被 Core 采纳	Core 的约束/模型管理日志
Lab 不被告知某个发现是否命中 hidden_challenge_set。Lab 只收到“贡献已记录/未记录”的抽象反馈。 进入 production 只是可能的结果之一，不是 Lab 的目标函数。

六、Lab 不做什么（终版）
Lab 不能：

颁发任何证书

制定或升级约束的 rigidity 级别

执行任何物理世界的探测或控制

访问 Core 的隐藏验证基准

直接读取生产数据或未脱敏的历史数据

将自己的产出从 sandbox 升级

修改 Core 的约束宪法或身份不变量

使用超出声明范围的 DataReleasePackage

绕过数据派生物治理规则

将 released_failure_logs 用于超出 permitted_analysis 的分析

跨包关联被 forbidden_tasks 禁止的数据集

将其 CoreCompatibilityPrecheck 结果当作资格判定对待

从 Core 的反馈中提取隐藏验证集的 membership 信息

七、定位声明
Polymorphic-Lab v0.4 是一个与物理世界完全隔离的探索证据供应链系统。它以受治理的数据释放包为唯一数据来源，在三层探索空间中生成可复现、可审计、可证伪的候选模型包、约束假设包、不确定性证据包、主动探测提案、反事实场景包和负面结果包。它永不自颁证书、永不自定约束、永不接触隐藏验证基准、永不执行真实探测、永不被反馈信号泄露审判机制。它的成功不是上线数量，而是让 Core 更清楚自己不知道什么。

隔离不止于物理和数据——也隔离于审判机制和敏感反馈。