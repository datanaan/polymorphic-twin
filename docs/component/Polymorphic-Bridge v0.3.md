Polymorphic-Bridge v0.3

决策接口层——核心原则（定稿版）

〇、版本说明
v0.3 是针对 v0.2 审核意见的修订版。具体修改：

修改项	内容
P0-1 修复	BridgeOutput 增加 validity，含快照标识、有效期和失效触发器
P0-2 修复	immediate_actions 增加 requires_fresh_core_check 和 execution_mode，明确行动执行授权
P1 修复	风险字段增加 risk_basis 和 residual_uncertainty
对齐 Core v1.3	production_model_link 改为 production_permissions_summary，对齐链路权限矩阵
〇、定位声明
Polymorphic-Bridge 不是一个独立的运行时系统。它是一个决策接口层——部署在 Core + Lab 双系统生态与人类决策者之间，不执行自己的计算循环，不维护自己的业务状态。

Bridge 是无状态的：每次调用，它接收 TwinObject 中 BridgeDecisionView 的当前快照，输出结构化的行动选项空间。它不记忆之前的决策，不学习用户偏好，不维护独立世界模型。

但 Bridge 生成审计事件：每次输出，Bridge 生成 BridgeDecisionRecord，提交至外部审计设施追加保存。Bridge 自身不持久化这些记录。

Bridge 输出的行动选项具有时效性：它们基于某一时刻的 Core 快照生成，在快照失效后不可继续作为行动依据。

它的职责是：

接收 Core-admitted Lab Evidence View（而非 Lab 原始输出）

接收 TwinObject 的 BridgeDecisionView（而非 Core 内部状态）

将两者映射为带有效期的结构化行动选项空间

一、Bridge 的宪法（不可违反的四条硬约束）
原则1：Bridge 输出行动空间，不输出单一建议
Bridge 不输出“建议执行A”。它输出：

可立即执行的行动（需在执行前经过 Core 新鲜确认）

有条件执行的行动（需额外证据/证书/审查）

禁止执行的行动（Core 拒绝，或安全边界不足）

当前不可判定的行动（知识状态不足以形成选项）

原则2：Bridge 不推翻 Core
Core 禁止的动作，Bridge 只能说明：

为什么被禁止

解锁需要什么条件（合法流程）

需要什么证据/审查/证书

Bridge 不得建议“虽然 Core 不允许，但可以低风险执行”。Bridge 不得输出“修改约束卡片Y即可绕过”的路径。

原则3：Bridge 不把 Lab 证据当事实
Bridge 只读取 Core-admitted Lab Evidence View——已通过检疫和 HardGate 准入的证据。不直接读取 Lab 原始输出。所有证据保留“候选”“未验证”“已准入但待审查”的限定词。

原则4：Bridge 必须审计人类选择
人类基于 Bridge 呈现的行动空间做出的选择，必须记录完整的 BridgeDecisionRecord。

二、Bridge 的输入和输出
2.1 输入
text
BridgeInput = {
  // 来自 TwinObject BridgeDecisionView
  twin_id,
  identity: {
    identity_state,
    identity_confidence,
    lineage_type
  },
  
  // Core 判决的当前状态（v0.3 对齐 Core v1.3 链路权限术语）
  core_status: {
    lifecycle_state,
    primary_uncertainty_type,
    model_governance_summary: {
      production_model_id,          // 仅作摘要展示，不参与权限判定
      production_permissions_summary: {
        has_prediction_model,
        has_diagnostic_model,
        has_control_model            // 必须存在 production_control 权限才为 true
      },
      fallback_model_id,
      models_in_diagnostic_count,
      models_in_shadow_count
    },
    active_constraint_violations_summary,
    active_suspended_constraints_summary,
    last_safe_fallback_triggered_at
  },
  
  // v0.3 不变：只读取 Core-admitted Lab Evidence View
  lab_evidence_admitted: {
    admitted_hypotheses: list of {
      hypothesis_id,
      evidence_status: candidate | under_review | accepted_for_diagnostic,
      brief_description,
      implication_for_action,
      admitted_at
    },
    admitted_negative_results: list of {
      negative_result_id,
      evidence_status,
      brief_description,
      implication_for_action
    },
    admitted_scenarios: list of {
      scenario_id,
      evidence_status,
      domain_gap_estimate
    },
    admitted_probe_proposals: list of {
      proposal_id,
      status: pending_core_review | approved | rejected | executed,
      brief_description,
      estimated_information_gain
    }
  },
  
  // 当前知识边界
  knowledge_boundary: {
    unknown_domains,
    horizon_of_reliable_prediction
  },
  
  // 来自 DomainPack BridgeActionView
  action_templates,
  human_roles,
  safe_fallback_summary
}
2.2 输出
text
BridgeOutput = {
  timestamp,
  twin_id,
  
  // v0.3 新增：时效性声明
  validity: {
    generated_from_snapshot_id,       // 生成此输出所基于的 Core 快照
    valid_until,                      // 建议的有效期截止时间
    invalidation_triggers: list of {
      constraint_state_changed,
      identity_state_changed,
      model_link_changed,
      safety_boundary_changed,
      safe_fallback_unavailable,
      new_core_failure_event
    }
  },
  
  situation_summary: {
    identity_state,
    identity_confidence,
    primary_uncertainty_type,
    knowledge_boundary_statement
  },
  
  action_space: {
    // === 可立即执行 ===
    immediate_actions: list of {
      action_id,
      action_type,
      action_description,
      prerequisites_met,
      risk_level: low | medium | high,
      // v0.3 新增：风险基础与残余不确定性
      risk_basis,                     // 该风险评估的依据
      residual_uncertainty,           // 评估后仍然存在的不确定性
      monitoring_requirements,
      fallback_if_fails,
      // v0.3 新增：执行授权信息
      execution_mode: core_execute | human_execute | request_core_execution | informational_only,
      requires_fresh_core_check: true // 执行前必须经过一次新鲜的 Core 状态确认
    },
    
    // === 有条件执行 ===
    conditional_actions: list of {
      action_id,
      action_type,
      action_description,
      unmet_prerequisites: list of {
        prerequisite_type,
        description,
        lawful_unlock_path: {
          required_review,
          required_evidence,
          required_certificate,
          required_role,
          required_wait_state,
          forbidden_shortcuts
        }
      },
      risk_level,
      risk_basis,
      residual_uncertainty,
      estimated_risk_if_executed_without_prerequisites,
      approval_required
    },
    
    // === 禁止执行 ===
    forbidden_actions: list of {
      action_id,
      action_type,
      prohibition_reason,
      lawful_unlock_conditions: {
        required_constraint_change,
        required_evidence,
        required_certificate,
        required_review,
        permanently_forbidden: true | false
      },
      risk_if_violated
    },
    
    // === 当前不可判定 ===
    undetermined_actions: list of {
      action_id,
      action_type,
      why_undetermined,
      what_information_would_help
    }
  },
  
  // 知识边界声明
  knowledge_boundary: {
    what_is_known,
    what_is_uncertain,
    what_is_unknown,
    horizon_of_reliable_prediction
  },
  
  // 审计元数据
  audit: {
    core_snapshot_id,
    lab_evidence_batch_id,
    bridge_version,
    action_template_version
  }
}
三、行动执行授权
Bridge 不执行任何行动。 它只输出行动选项。行动的实际执行由以下路径之一完成：

execution_mode	含义	执行路径
core_execute	该行动由 Core 直接执行（如安全回落）	Core 在运行时自动触发，人类不可干预
human_execute	该行动由授权人类操作员执行	人类在外部控制系统中手动执行，Bridge 仅记录审计
request_core_execution	该行动需要人类发起请求，Core 审核后执行	人类通过 Bridge 记录发起请求 → Core 验证当前状态 → 执行或拒绝
informational_only	该行动仅供信息参考，不涉及物理执行	不触发任何执行流程，仅记录人类已阅
关键原则：所有标记为 human_execute 或 request_core_execution 的行动，在执行前必须经过一次新鲜的 Core 状态确认。不能仅凭过期的 BridgeOutput 直接执行。

core_execute 行动不需要人类批准。它们是 Core 的安全回落策略的一部分，在触发条件满足时自动执行。

四、决策审计记录
text
BridgeDecisionRecord = {
  record_id,
  twin_id,
  timestamp,
  
  // 情境快照
  situation_summary_at_decision,
  identity_confidence_at_decision,
  
  // 基于的快照
  core_snapshot_id,
  bridge_output_validity_at_decision,   // 决策时 BridgeOutput 是否仍在有效期内
  
  // 呈现的选项
  options_presented: {
    immediate_count,
    conditional_count,
    forbidden_count,
    undetermined_count
  },
  
  // 风险披露
  risks_disclosed: list,
  
  // 人类选择
  human_role,
  human_selection: {
    selected_action_id,
    action_type,
    execution_mode,
    selection_timestamp,
    fresh_core_check_performed,         // v0.3 新增：是否执行了新鲜 Core 状态确认
    fresh_core_check_result,            // v0.3 新增：新鲜确认的结果
    exception_request_applied,
    exception_request_type,
    exception_request_authorization
  },
  
  // 确认记录
  risk_acknowledgement,
  prerequisites_acknowledgement,
  
  // 未选但可选的路径
  options_declined: list,
  
  // 审计锚
  lab_evidence_batch_id,
  bridge_input_hash
}
这些记录不可删除，只追加。由外部审计设施持久化。 Bridge 自身不存储它们。

五、人类不能做的事
Bridge 必须明确以下行为不在任何人类角色的权限范围内，即使 DomainPack 中定义了 exception_request_authority：

不能直接覆盖 Core 的安全硬拒绝。Core 以 safety_critical 约束为由拒绝的动作，人类只能发起例外审查流程，不能直接下令执行。

不能绕过约束卡片修订流程直接修改约束。约束修订必须经过人工审查、版本升级、重新认证。

不能在身份不确定状态下执行不可逆操作。身份不确定时，可逆的安全保持和观测增加是允许的，不可逆的修改被禁止。

不能在无安全回落策略绑定的情况下执行边界操作。

不能基于过期的 BridgeOutput 执行行动。所有行动执行前必须确认输出仍在有效期内，或重新请求 Bridge 生成新的行动空间。

exception_request 的含义：人类可以发起一个流程，请求审查当前约束、请求重新认证、请求人工接管或安全停机。这不是“覆盖 Core”，而是“启动一个受治理的例外流程”。这个流程的每一步都有审计记录。

六、Bridge 不做什么
不生成单一建议

不推翻 Core

不把 Lab 证据当事实

不执行控制：不向物理设备发送任何信号

不学习：没有自己的模型，不进化，不记忆偏好

不生成自然语言：输出是结构化数据。自然语言呈现是外围人机交互层的职责

不替代人工判断

不维护业务状态：每次调用是无状态的，不记忆之前的决策

不直接读取 Lab 原始输出：只通过 Core-admitted Lab Evidence View 获取证据

不保证输出长期有效：BridgeOutput 带有明确的 valid_until 和失效触发器

七、定位声明
Polymorphic-Bridge v0.3 是部署在 Core+Lab 双系统生态与人类决策者之间的决策接口层。它是一个无业务状态的转换层——每次调用接收 TwinObject 的 BridgeDecisionView 快照和 Core-admitted Lab Evidence View，输出带有时效性的结构化行动选项空间：可立即执行、有条件执行、禁止执行、当前不可判定。它不生成单一建议、不推翻 Core 判决、不把 Lab 证据当事实、不记忆、不学习、不直接读取 Lab 原始输出。每次输出都声明有效期和失效条件。所有行动在执行前必须经过新鲜 Core 状态确认。人类做出的每个选择都有不可删除的审计记录。