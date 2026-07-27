DomainPack v0.3
场景实例化配置单元——核心定义（定稿版）

〇、版本说明
v0.3 是针对 v0.2 审核意见的修订版。具体修改：

修改项	内容
P0-1 修复	新增 rigidity_criticality_compatibility 规则，明确 safety_critical 必须为 absolute
P0-2 修复	父包退役按原因分流：safety_issue → 立即降级；superseded → 限期运行；obsolete → 禁止新实例化
P1 修复	verification_record 增加 verified_initial_set_reference、verified_domain_reference、verification_method
版本引用更新	文档中对 Core 的引用从 v1.2 更新为 v1.3
〇、定位说明
根据设计方确认：外部专业领域知识库和数据生产设施已存在。

DomainPack 不是一个需要从零构建的复杂知识工程产物。它是一个轻量级配置单元——从已有外部知识库中引用和组合现有资源，声明特定工业场景下 TwinObject 实例化所需的具体参数。

它的角色不是“创建领域知识”，而是“告诉三系统：在这个场景下，状态是什么、约束是什么、安全策略是什么、行动模板是什么、谁能做什么”。

DomainPack 是配置，不是模型。是声明，不是实现。

一、DomainPack 结构
text
DomainPack = {
  // ===== 标识 =====
  domain_id,
  domain_name,
  domain_version,
  parent_domain_id,                 // 继承自哪个DomainPack（可选）

  // ===== 继承策略 =====
  inheritance_policy: {
    can_relax_parent_absolute_constraints: false,
    can_lower_parent_criticality: false,
    conflict_resolution: stricter_wins | require_manual_review,
    parent_update_action: require_recertification,
    parent_retirement_action_by_reason: {
      // v0.3 修改：按退役原因分流
      safety_issue: immediate_degrade_and_require_recertification,
      superseded: mark_requires_upgrade_with_deadline,
      obsolete: warn_and_prohibit_new_instantiation,
      administrative: human_review_required
    }
  },

  // ===== 刚性-关键性兼容规则（v0.3 新增）=====
  rigidity_criticality_compatibility: {
    // safety_critical 约束必须是 absolute，不能是 soft 或 learnable
    safety_critical: must_be_absolute,
    // identity_critical 约束必须是 absolute，或经过严格审计的 learnable
    identity_critical: absolute_or_strictly_audited,
    // operational 约束可以是任意刚性
    operational: absolute | soft | learnable,
    // informational 约束可以是 soft 或 learnable
    informational: soft | learnable
  },

  // ===== 状态语义实例化 =====
  state_semantics_template: {
    ontology_reference,             // 外部知识库中的本体ID
    variables: list of {
      name,
      physical_meaning,
      unit,
      range_min,
      range_max,
      observability,
      controllability,
      measurement_source
    }
  },

  // ===== 约束卡片集合 =====
  constraint_cards: {
    knowledge_base_reference,       // 外部知识库中的约束模板ID

    absolute: list of {
      constraint_id,
      domain_override,
      tolerance_override,
      certifier_config,
      scenario_criticality: safety_critical | identity_critical | operational | informational
    },

    soft: list of {
      constraint_id,
      weight,
      domain_override,
      // v0.3 约束：soft 约束的 scenario_criticality 只能是 operational 或 informational
      scenario_criticality: operational | informational
    },

    learnable: list of {
      constraint_id,
      initial_value_source,
      learning_rate_limit,
      // v0.3 约束：learnable 约束的 scenario_criticality 只能是 operational 或 informational
      // 特例：若为 identity_critical，必须通过 strictly_audited 审查
      scenario_criticality: identity_critical | operational | informational
    }
  },

  // ===== 安全回落策略（对齐 Core v1.3）=====
  safe_fallback: {
    policy_id,
    template_reference,

    domain_of_validity,
    verified_initial_set,
    invariant_safe_set,
    robustness_margin,

    target_state,
    trajectory_constraints: {
      max_rate,
      forbidden_zones
    },
    max_duration,

    unavailable_action: human_takeover | safe_shutdown | freeze,
    post_fallback_action: hold | handoff | shutdown,

    // v0.3 扩展：验证记录绑定验证域
    verification_record: {
      verified_in_simulation,
      verified_scenarios,
      verified_initial_set_reference,   // v0.3 新增：绑定到哪个初始状态集
      verified_domain_reference,        // v0.3 新增：绑定到哪个适用域
      verification_method,              // v0.3 新增：验证方法
      verification_result_summary,      // v0.3 新增：验证结果摘要
      last_verification_date
    }
  },

  // ===== 行动空间模板 =====
  action_templates: {
    knowledge_base_reference,

    immediate_action_types: list of {
      action_type_id,
      description_template,
      applicable_when,
      monitoring_requirements,
      fallback_if_fails
    },

    conditional_action_types: list of {
      action_type_id,
      description_template,
      typical_prerequisites,
      risk_profile
    },

    forbidden_action_types: list of {
      action_type_id,
      description_template,
      typical_prohibition_reasons
    }
  },

  // ===== 人类角色定义 =====
  human_roles: list of {
    role_id,
    role_name,
    authorized_action_types,
    exception_request_authority: {
      can_request_review,
      can_request_recertification,
      can_request_constraint_revision,
      can_initiate_human_takeover,
      can_initiate_safe_shutdown
    },
    approval_required_for
  },

  // ===== 验证集引用 =====
  validation_sets: {
    public_eval_set_reference,
    // 以下两项在 LabExplorationView 中不可见
    audit_benchmark_reference,
    production_acceptance_reference
  },

  // ===== 元信息 =====
  created_at,
  last_modified_at,
  certified_by,
  certification_date,
  applicability_scope
}
二、刚性-关键性兼容规则
v0.3 新增此规则，防止配置错误导致安全关键约束被弱化。

关键性	允许的刚性	说明
safety_critical	仅 absolute	安全关键约束必须进入 Core 硬门槛，不能作为 soft 惩罚项或 learnable 自适应项
identity_critical	absolute 或 learnable（需 strictly_audited）	身份关键约束可以是从数据中学习的，但学习过程必须审计且每次修改须人工确认
operational	absolute、soft、learnable	运行层面的约束可以是任意刚性
informational	soft、learnable	信息层面的约束不进入硬门槛，可以是 soft 或 learnable
DomainPack 在加载时必须验证：所有 scenario_criticality: safety_critical 的约束，其 rigidity 必须为 absolute。违反此规则的 DomainPack 不得进入 certified 状态。

三、继承规则
当 parent_domain_id 不为空时：

约束继承：子包继承父包的所有约束。子包可以新增约束，可以收紧父包约束的适用域或容差，但不得放宽父包的绝对约束、不得降低父包的安全关键性。

安全回落继承：子包继承父包的安全回落策略。子包可以定义更严格的回落策略，但不得放松。

冲突解决：当父包与子包的约束或安全策略冲突时，若 conflict_resolution = stricter_wins，自动采用更严格者；若 conflict_resolution = require_manual_review，标记冲突并请求人工裁决。

父包更新触发：父包版本升级时，所有子包标记为 requires_recertification。

父包退役按原因分流（v0.3 修改）：

退役原因	子包动作
safety_issue	子包立即降级：禁止在 production 状态运行，标记为 requires_recertification，现有生产实例降级至 diagnostic 链路
superseded	子包标记为 requires_upgrade，可限期运行，需在截止日期前重新认证
obsolete	子包发出警告，禁止新实例化，已有实例可继续运行但标记为 deprecated
administrative	子包标记为 parent_retired，请求人工审查是否需自主升级
四、DomainPack 视图机制
DomainPack 不是所有系统共享的裸配置文件。不同系统获得不同投影：

视图	使用者	可见内容	不可见内容
CoreFullView	Core（运行时+认证）	全部字段	—
BridgeActionView	Bridge	标识、状态语义、约束摘要、安全回落（不含验证细节）、行动模板、人类角色	约束certifier完整逻辑、验证集隐藏引用、内部审计字段、父包退役原因详情
LabExplorationView	Lab	标识、状态语义、约束摘要（不含certifier和隐藏阈值）、刚性-关键性兼容规则摘要、公开评估集引用	约束certifier完整逻辑、audit_benchmark_reference、production_acceptance_reference、安全回落策略、人类角色、父包继承链
AuditView	审计系统	全部字段 + 完整变更历史	—
原则：Lab 永远不可见 audit_benchmark_reference 和 production_acceptance_reference。这些字段在 LabExplorationView 中被移除。

五、DomainPack 的生命周期
text
DomainPackLifecycle = 
  draft                // 草稿，尚未认证
  | certified          // 已认证，可用于测试环境
  | production         // 已部署到生产环境
  | deprecated         // 已过时，新场景不应使用
  | retired            // 已退役
draft → certified：需要约束审查（含刚性-关键性兼容验证）、安全回落策略验证、人类角色权限审查。

certified → production：需要生产环境验证。

production → deprecated：人工标记。

任意状态 → retired：人工退役。退役原因必须声明，以便继承链上的子包做出正确响应。

关键规则：

production 状态的 DomainPack 修改必须经过重新认证。

如果修改涉及 safety_critical 约束或 safe_fallback 策略，必须重新验证回落。

safety_critical 约束的 rigidity 不得从 absolute 修改为其他值。违反此规则的修改直接被拒绝。

六、DomainPack 的轻量化原则
引用优于创建：所有可引用的内容优先从外部知识库引用，不重复定义。

只声明差异：只声明该场景下与通用模板的差异，不完整重述。

验证集引用而非内嵌：只引用外部数据设施中的验证集ID。

行动模板是结构，不是实现：定义有哪些行动类型，不定义UI展示。

领域专家可以在较短时间内完成初稿，但进入 certified 或 production 前必须经过认证、约束审查（含刚性-关键性兼容验证）和回落策略验证。

七、DomainPack 不做什么
不创建新的领域知识（引用外部知识库）

不存储数据（引用外部数据设施）

不定义Core的审判逻辑（Core的HardGate/RiskGate是通用的）

不定义Lab的探索策略（Lab的进化算法是通用的）

不定义Bridge的UI（Bridge输出结构化行动选项，UI是外围系统）

不允许人类角色覆盖Core的安全硬拒绝（exception_request ≠ override）

不允许 safety_critical 约束以 soft 或 learnable 形式存在

八、定位声明
DomainPack v0.3 是 Polymorphic-Twin 生态的场景实例化配置单元。它从已有的专业领域知识库中引用和组合资源，声明特定场景下 TwinObject 所需的具体参数。它通过刚性-关键性兼容规则确保安全关键约束不被弱化，通过多视图机制保护隐藏验证集不被 Lab 可见，通过 exception_request_authority 确保人类不能直接覆盖 Core 的安全拒绝，通过按退役原因分流的继承规则防止父包安全问题污染子包。

它是配置，不是模型。是声明，不是实现。是让三系统——Core v1.3、Lab v0.4、Bridge v0.3——从“通用内核”变为“具体场景可用”的实例化单元。