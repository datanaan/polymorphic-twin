TwinObjectModel v0.3
统一孪生对象模型——核心定义（定稿版）

〇、版本说明
v0.3 是针对 v0.2 审核意见的修订版。具体修改：

修改项	内容
P0-1 修复	current_link 改为 active_links，对齐 Core v1.3 的链路权限矩阵
P0-2 修复	safe_action_set_nonempty 从 IdentityInvariants 移至 ActionState
P0-3 修复	CoreOperationalView 拆分为 CoreRuntimeView / CoreCertificationView / CoreAuditView
P1 修复	生命周期状态机明确 identity_branch / identity_rebuild 事件路径
版本引用更新	文档中对 Core 的引用从 v1.2 更新为 v1.3
〇、定位声明
TwinObjectModel 不是第三个运行时系统。它是 Core、Lab、Bridge 共同操作的唯一数据对象定义。

在 Core v1.3 和 Lab v0.4 的理论定稿中，“状态语义”、“身份不变量”、“约束体系”、“链路权限”这些概念反复出现，但它们在各自文档中独立定义，缺少统一结构。TwinObjectModel 就是那个统一结构。

它的核心职责：让 Core、Lab、Bridge 围绕同一个“孪生对象”工作，而不是各自维护一套世界观。

一、设计原则
原则1：TwinObjectModel 是三系统共同对象，不是某个系统的内部状态
Core、Lab、Bridge 各自读写 TwinObject 的不同字段。任何系统不得独占写入权。

原则2：必须支持多视图
TwinObject 不裸暴露给所有系统。不同系统看到不同视图：

CoreRuntimeView：运行时资格判定、安全退化所需的状态、约束、模型资格

CoreCertificationView：链路升级、证书签发、隐藏验证集访问——仅供认证流程使用，运行时不可见

CoreAuditView：完整审计追溯——仅供离线审计，不参与运行时决策

LabExplorationView：状态语义公开视图、约束摘要、公开评估集——不含隐藏验证集、不含生产模型完整资格状态

BridgeDecisionView：资格摘要、知识状态、行动模板——不含 Core 内部审判细节、不含隐藏验证集

AuditView：完整审计追溯——仅用于审计，不参与运行时决策

原则3：关键状态变更必须追加，不可静默覆盖
约束挂起、证书过期、模型降权、身份不确定、身份分叉、身份重建、人类选择、安全回落——这些事件只能追加记录，不可原地修改覆盖。

二、TwinObject 完整结构
2.1 根结构
text
TwinObject = {
  // ===== 身份标识 =====
  twin_id,                          // 全局唯一标识
  twin_type,                        // 孪生类型（物理资产/生理系统/化学过程/...）
  active_domain_pack_id,            // 当前生效的DomainPack
  created_at,
  last_modified_at,

  // ===== 身份与谱系 =====
  identity: TwinIdentity,

  // ===== 状态语义 =====
  state_semantics: StateSemantics,

  // ===== 约束状态 =====
  constraint_state: ConstraintState,

  // ===== 身份不变量 =====
  identity_invariants: IdentityInvariants,

  // ===== 模型治理状态 =====
  model_governance_state: ModelGovernanceState,

  // ===== 知识状态 =====
  knowledge_state: KnowledgeState,

  // ===== 行动与安全状态 =====
  action_state: ActionState,

  // ===== 审计追溯 =====
  audit: AuditTrail
}
2.2 身份与谱系
text
TwinIdentity = {
  identity_state: initializing | active | identity_uncertain | degraded | frozen | retired,
  identity_confidence: high | medium | low | undetermined,
  lineage_id,                       // 指向 TwinLineage 记录
  parent_twin_id,                   // 直接父孪生（若当前为分支）
  lineage_type: version_update | identity_branch | identity_rebuild,
  identity_branch_event_id,         // 若为分支，指向分支事件
  last_identity_change_at,
  last_identity_change_reason
}
生命周期状态迁移（v0.3 补充分支/重建路径）：

text
initializing → active
active → identity_uncertain                    （Core 可辨识性置信度不足）
identity_uncertain → active                     （证据恢复或人工确认）
identity_uncertain → active + version_update    （确认身份连续，同时版本更新）
identity_uncertain → identity_branch            （确认身份断裂，创建分支子孪生）
identity_uncertain → identity_rebuild           （确认身份不可恢复，重建）
identity_uncertain → degraded                   （超时未解决，触发安全回落）
degraded → active                               （人工确认恢复）
degraded → frozen                               （回落策略无法维持）
active → frozen                                 （身份断裂且无法自动分支）
active → identity_branch                        （人工确认分支，当前孪生继续运行）
任意状态 → retired                               （人工退役）
2.3 状态语义
text
StateSemantics = {
  version,                            // 语义版本号
  ontology_reference,                 // 外部知识库中的本体定义引用
  variables: list of {
    name,                             // 变量名
    physical_meaning,                 // 物理/生理/信息含义
    unit,                             // 单位
    range_min,                        // 有效范围下界
    range_max,                        // 有效范围上界
    observability: direct | derived | unobserved,
    controllability: direct | indirect | uncontrollable,
    measurement_source               // 数据来源引用
  },
  derived_quantities: list            // 派生量定义
}
修改规则：version 变更必须触发全系统重新认证。变量语义的修改必须显式记录变更原因。

2.4 约束状态
text
ConstraintState = {
  constraint_set_version,             // 约束体系版本号
  knowledge_base_reference,           // 外部约束知识库引用

  active_constraints: {
    absolute: list of {
      constraint_id,
      status: active | uncertain,
      last_verification_result: pass | uncertain | fail,
      last_verification_at
    },
    soft: list of {
      constraint_id,
      weight,
      status: active | relaxed
    },
    learnable: list of {
      constraint_id,
      current_value,
      learning_rate_limit,
      last_updated_at
    }
  },

  suspended_constraints: list of {
    constraint_id,
    suspend_reason: domain_not_applicable | observability_insufficient | under_review,
    suspended_at,
    required_resolution,
    resolution_deadline
  },

  failed_constraints: list of {
    constraint_id,
    failure_type: violation_detected | conflict_with_other_constraint | certifier_unavailable,
    detected_at,
    diagnostic_state: unresolved | under_investigation | resolved,
    resolution
  }
}
2.5 身份不变量
text
IdentityInvariants = {
  // 审计基准集（不可变）
  audit_benchmark: {
    benchmark_id,
    reference,                        // 外部数据设施中的验证数据集引用
    created_at,
    version,                          // 一旦设定，不可修改
    domain_description                // 覆盖的状态域描述
  },

  // 当前验证集（可版本化更新）
  current_validation_set: {
    validation_set_id,
    reference,
    version,
    last_updated_at,
    update_reason
  },

  // 安全边界定义
  safety_boundaries: {
    state_bounds: list of {
      variable_name,
      min,
      max,
      criticality: safety_critical | operational | informational
    },
    control_bounds: list of {
      control_variable,
      min,
      max,
      max_rate
    },
    prediction_horizon_max,           // 最大预测时域
    safe_action_set_definition        // 安全动作集的定义（什么构成安全动作）
  },

  // 误差评估协议
  error_evaluation_protocol: {
    protocol_version,
    metrics: list,                    // 使用的误差度量
    thresholds: list,                 // 可接受阈值
    last_updated_at
  }
}
v0.3 修改：safe_action_set_nonempty 从身份不变量中移除。它是运行时判断，不是身份定义。身份不变量只保留 safe_action_set_definition——定义什么构成安全动作，不判断当前是否有安全动作可用。

2.6 模型治理状态
text
ModelGovernanceState = {
  registered_models: list of {
    model_id,
    model_type,                       // 骨架类型

    // v0.3 修改：从 current_link 改为 active_links，对齐 Core v1.3
    active_links: list of {
      link_type: production_prediction | production_diagnostic | production_control | diagnostic_only | shadow | offline_sandbox | physical_probe | rejected,
      status,
      granted_at,
      granted_by,
      expiry
    },

    qualification_history: list of {
      timestamp,
      from_links,
      to_links,
      reason,
      hardgate_result,
      riskgate_result
    },

    active_certificates: list of {
      certificate_id,
      certificate_type,
      expiry
    }
  },

  production_model_id,                // 当前生产链路主模型（用于摘要展示）
  fallback_model_id,                  // 退化模型

  last_qualification_change_at,
  last_qualification_change_reason
}
v0.3 关键修改：

current_link 不再作为单一权限判定字段。

改为 active_links：一个模型可以同时持有多个链路权限（如同时具有 production_prediction 和 diagnostic_only）。

控制权限必须通过 link_type 中的 production_control 或 physical_probe 判断，不能仅凭 production_model_id 推定。

production_model_id 降级为摘要展示字段，不参与权限判定。

Lab 不可见此字段的完整内容。 Lab 仅可见 registered_models 中模型的公开摘要（模型ID、模型类型、是否有 sandbox 以上权限的指示），不可见具体 active_links、资格历史、证书详情和 production_model_id。

2.7 知识状态
text
KnowledgeState = {
  // Core 判决的知识状态
  primary_uncertainty_type,           // aleatoric | epistemic | distributional | intervention | identity
  
  // Lab 提交并由 Core 准入的证据
  admitted_lab_evidence: {
    admitted_hypotheses: list of {
      hypothesis_id,
      source: lab,
      evidence_status: candidate | under_review | accepted_for_diagnostic | rejected,
      admitted_at
    },
    admitted_negative_results: list of {
      negative_result_id,
      source: lab,
      evidence_status,
      admitted_at
    },
    admitted_scenarios: list of {
      scenario_id,
      source: lab,
      evidence_status,
      admitted_at
    },
    admitted_probe_proposals: list of {
      proposal_id,
      source: lab,
      status: pending_core_review | approved | rejected | executed,
      admitted_at
    }
  },

  // 已知未知域
  unknown_domains: list of {
    domain_description,
    identified_by: core | lab,
    identified_at,
    severity: blocking | high | medium | low
  },

  // 当前活跃假设（供Bridge行动选项生成）
  active_hypotheses_summary: list of {
    hypothesis_id,
    brief_description,
    status,
    implication_for_action
  },

  last_knowledge_update_at
}
关键约束：admitted_lab_evidence 由 Core 写入，不是 Lab 直接写入。Lab 提交证据包到 Core offline_sandbox，Core 经过检疫和 HardGate 后，将准入的证据写入此字段。Bridge 只能读取此字段中 evidence_status 为 accepted_for_diagnostic 或 under_review 的条目，不得直接读取 Lab 原始输出。

2.8 行动与安全状态
text
ActionState = {
  // 当前生效的安全回落策略
  active_safe_fallback_policy: {
    policy_id,
    domain_of_validity,               // 该策略的适用域
    verified_initial_set,             // 已验证可从此集合中的状态安全回落
    invariant_safe_set,               // 回落过程中保持不违反的安全不变量
    robustness_margin,                // 鲁棒裕度
    target_state,                     // 回落目标状态
    trajectory_constraints,           // 回落轨迹约束
    max_duration,                     // 最长回落时间
    unavailable_action: human_takeover | safe_shutdown | freeze,
    post_fallback_action: hold | handoff | shutdown,
    last_verified_at
  },

  // v0.3 新增：当前安全动作集状态（从身份不变量移至此处）
  current_safe_action_set: {
    nonempty: true | false | unknown,
    evaluated_at,
    evaluator,
    valid_until,
    fallback_available
  },

  // 当前行动空间
  current_action_space_id,            // 指向最近一次Bridge生成的行动空间
  last_bridge_output_id,
  last_bridge_output_at,

  // 人工接管状态
  human_takeover_state: not_requested | requested | in_progress | completed,
  human_takeover_requested_at,
  human_takeover_completed_at,

  // 安全回落历史
  last_safe_fallback_triggered_at,
  last_safe_fallback_trigger_reason,

  // 决策追溯
  last_decision_record_id
}
v0.3 修改：current_safe_action_set 从 IdentityInvariants 移至此处。它是运行时状态——取决于当前状态、控制约束、模型资格和安全回落策略是否可用——不是身份定义。

2.9 审计追溯
text
AuditTrail = {
  // Core 快照
  latest_core_snapshot_id,
  core_snapshot_history: list,       // 只追加

  // Bridge 决策记录
  latest_bridge_decision_record_id,
  bridge_decision_history: list,     // 只追加

  // Lab 证据批次
  latest_lab_evidence_batch_id,
  lab_evidence_batch_history: list,  // 只追加

  // 安全事件
  safety_events: list of {
    event_id,
    event_type,
    timestamp,
    description,
    related_snapshot_id
  },

  // 身份事件
  identity_events: list of {
    event_id,
    event_type: version_update | identity_branch | identity_rebuild | lifecycle_state_change,
    timestamp,
    description,
    related_lineage_id
  },

  // 人类决策事件
  human_decisions: list of {
    decision_id,
    timestamp,
    human_role,
    decision_type,
    decision_summary,
    risk_acknowledged
  },

  // 不可变审计日志引用
  immutable_audit_log_reference       // 指向外部防篡改日志系统
}
所有审计字段只追加，不可删除，不可修改。

三、写入权限矩阵
字段组	CoreRuntime	CoreCertification	Lab	Bridge	DomainPack	人工/认证
identity	读+写	只读	只读(公开)	只读	初始化	审批分叉/重建
state_semantics	只读	只读	只读(公开)	只读	初始化引用	版本升级审批
constraint_state.active	读+写(suspend/恢复)	读+写	只读(摘要)	只读	初始化引用	版本升级审批
constraint_state.suspended	写	读+写	不可见	只读	不可见	审批解除
constraint_state.failed	写	读	不可见	只读(摘要)	不可见	审批解决
identity_invariants.audit_benchmark	不可见	只读	不可见	不可见	初始化引用	不可修改
identity_invariants.current_validation_set	只读(公开集)	读+写	只读(公开集)	不可见	初始化引用	版本化更新
identity_invariants.safety_boundaries	读	读	只读(公开)	只读	初始化	修改审批
model_governance_state	读+写(资格更新)	读+写(链路升级、证书签发)	不可见完整内容	只读(摘要)	初始化注册	审批重大变更
knowledge_state.admitted_lab_evidence	读	写(准入)	不可直接写	只读	不适用	不适用
knowledge_state.unknown_domains	读+写	读	只读(公开)	只读	不适用	不适用
knowledge_state.active_hypotheses_summary	写(摘要)	读	不可直接写	只读	不适用	不适用
action_state.active_safe_fallback_policy	读	读	不可见	只读(摘要)	初始化引用	审批修改
action_state.current_safe_action_set	读+写	读	不可见	只读	不适用	不适用
action_state.human_takeover_state	读+写	读	不可见	只读	不适用	写(takeover操作)
audit	追加	追加	追加(Lab批次)	追加(Bridge记录)	不适用	追加(审批记录)
v0.3 关键修改：Core 的写入权限从单一 Core 拆分为 CoreRuntime 和 CoreCertification。运行时资格判定不可见隐藏验证基准。

四、多视图定义
4.1 CoreRuntimeView
Core 运行时模块可见：identity、state_semantics、constraint_state、identity_invariants 中的 safety_boundaries 和 error_evaluation_protocol、model_governance_state、knowledge_state、action_state。

不可见：audit_benchmark、hidden_challenge_set、production_acceptance_suite、完整审计历史。

4.2 CoreCertificationView
Core 认证模块可见：CoreRuntimeView 的全部内容，加上 audit_benchmark、hidden_challenge_set、production_acceptance_suite。用于链路升级验证、证书签发、隐藏验证集访问。

仅供认证流程使用，运行时资格判定不可调用此视图。

4.3 CoreAuditView
完整审计追溯。仅供离线审计使用，不参与运行时决策。

4.4 LabExplorationView
Lab 可见：

twin_id, twin_type

identity.identity_state, identity.lineage_type（不含 identity_confidence 和 parent_twin_id）

state_semantics 完整内容

constraint_state.active_constraints 中的公开摘要（约束ID、公开表达式摘要、适用域摘要——不含完整的 certifier 逻辑、隐藏阈值）

identity_invariants.current_validation_set 中标记为 public 的部分

identity_invariants.safety_boundaries 中标记为 public 的部分

model_governance_state.registered_models 的公开摘要（模型ID、模型类型、是否有 sandbox 以上权限的指示——不含具体 active_links、资格历史、证书详情、production_model_id）

knowledge_state.unknown_domains

knowledge_state.active_hypotheses_summary

其自身提交的证据包的历史状态

Lab 永远不可见：

audit_benchmark

hidden_challenge_set

production_acceptance_suite

约束的完整 certifier 逻辑和隐藏阈值

model_governance_state 的 active_links 详情、资格历史和证书详情

identity_confidence

action_state 中的安全回落策略和人工接管状态

4.5 BridgeDecisionView
Bridge 可见：

twin_id, twin_type, active_domain_pack_id

identity.identity_state, identity.identity_confidence, identity.lineage_type

state_semantics 完整内容

constraint_state 的摘要

identity_invariants.safety_boundaries

model_governance_state 的摘要（当前生产模型ID、退化模型ID、各链路模型数量及权限类型）

knowledge_state 完整内容

action_state 完整内容

Bridge 不可见：

约束的完整 certifier 逻辑

audit_benchmark、hidden_challenge_set、production_acceptance_suite

model_governance_state 的完整资格历史和证书详情

4.6 AuditView
完整审计追溯。仅供离线审计使用。

五、TwinLineage（身份谱系）
text
TwinLineage = {
  lineage_id,
  root_twin_id,                     // 谱系根孪生

  entries: list of {
    entry_id,
    entry_type: version_update | identity_branch | identity_rebuild | lifecycle_change,

    // 若为 version_update：
    update_description,
    previous_twin_object_id,
    new_twin_object_id,
    update_timestamp,
    updated_fields,

    // 若为 identity_branch：
    branch_event_description,
    parent_twin_id,
    child_twin_id,
    branch_timestamp,
    broken_invariants,              // 被破坏的不变量列表
    inherited_invariants,           // 继承的不变量列表
    new_identity_scope,             // 新身份的适用域描述

    // 若为 identity_rebuild：
    rebuild_reason,
    old_twin_retired_at,
    new_twin_id,
    rebuild_timestamp,

    // 若为 lifecycle_change：
    from_state,
    to_state,
    change_reason,
    change_timestamp,
    approved_by
  },

  // 当前活跃孪生
  current_active_twin_id,
  current_active_since
}
继承规则：

子孪生继承父孪生的 broken_invariants 之外的所有不变量。

子孪生不能放松父孪生的绝对约束。只能收紧或保持不变。

父孪生退役不影响子孪生。父孪生更新触发子孪生重新认证。

六、TwinObjectModel 与外部基础条件的关系
根据设计方确认：外部专业领域知识库和数据生产设施已存在。

TwinObjectModel 定位为逻辑定义层。外部条件为物理支撑层：

外部知识库：提供状态语义的本体定义、约束模板、安全策略模板

外部数据设施：提供时序数据存储、验证数据集、审计日志持久化

外部版本管理系统：TwinObject 自身的版本化存储和 TwinLineage 的持久化

TwinObjectModel 不重复建设这些外部能力。它引用它们。

七、TwinObjectModel 不做什么
不替代外部知识库的本体论设计

不存储任何模型的权重或训练数据

不定义 Core 怎么审判——那是 Core 的职责

不定义 Lab 怎么探索——那是 Lab 的职责

不定义 Bridge 怎么展示行动空间——那是 Bridge 的职责

不替代外部数据设施的时序存储或审计日志系统

不定义约束卡片的内部验证逻辑

八、与 Core v1.3 和 Lab v0.4 的关键对齐
Core/Lab 概念	TwinObjectModel 对应字段
状态语义（原理一）	state_semantics
约束体系（原理二）	constraint_state
身份不变量（原理四）	identity_invariants
链路权限矩阵（Core v1.3）	model_governance_state.active_links
安全回落策略	action_state.active_safe_fallback_policy
身份连续性	identity + TwinLineage
失败理论	identity.identity_state 生命周期迁移
Lab 证据准入	knowledge_state.admitted_lab_evidence
验证防火墙	LabExplorationView 的可见性限制
反馈隔离	BridgeDecisionView 的可见性限制
Core 认证与运行时分离	CoreRuntimeView / CoreCertificationView / CoreAuditView
九、定位声明
TwinObjectModel v0.3 是 Polymorphic-Twin 生态的统一孪生对象定义。它承载了“这个系统在孪生什么”的完整答案——身份与谱系、状态语义、约束状态、身份不变量、模型治理状态（含 Core v1.3 链路权限矩阵）、知识状态、行动与安全状态、审计追溯。Core、Lab、Bridge 围绕同一个 TwinObject 工作，但各自通过不同的视图访问——Core 的运行时与认证能力被显式分离，Lab 被防火墙保护不可见隐藏验证基准，Bridge 只获得决策所需的摘要视图。

它是逻辑定义层，不重复建设外部知识库和数据设施。它是三系统共通的“系统”概念的锚点。