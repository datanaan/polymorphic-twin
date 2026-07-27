Polymorphic-Twin 生态接口规范 v1.0

前置说明
本规范定义 Polymorphic-Twin 生态中五个组件之间的接口。各组件核心原则已在前序文档中定稿：

组件	定稿版本	性质
Core	v1.3	运行时系统：约束治理、资格审判、安全退化
Lab	v0.4	离线系统：隔离探索、证据供应
Bridge	v0.3	无状态接口层：行动空间映射、决策审计
TwinObjectModel	v0.3	统一数据对象定义
DomainPack	v0.3	场景实例化配置单元
本规范不重复论述各组件的内部原理，仅定义它们之间的调用关系、数据格式、状态机和约束。

一、架构总览与接口矩阵
text
                    DomainPack Manager
                         │
                   加载/视图投影
                         │
                         ▼
              ┌──────────────────┐
              │  TwinObject      │
              │  (唯一数据锚点)   │
              └────────┬─────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
      ┌──────┐    ┌──────┐    ┌────────┐
      │ Core │    │ Lab  │    │ Bridge │
      └──┬───┘    └──┬───┘    └───┬────┘
         │           │            │
         ▼           ▼            ▼
   物理世界      隔离计算环境    人类决策者
调用关系矩阵：

调用方 ↓ / 被调用方 →	Core	Lab	Bridge	TwinObject	DomainPack Mgr
Core	—	调用：拉取证据包	调用：推送状态快照	读写	读取配置
Lab	提交证据包	—	不调用	只读(Lab视图)	只读(Lab视图)
Bridge	调用：拉取快照	不直接调用	—	只读(Bridge视图)	只读(Bridge视图)
人工/运维	调用：审批接口	调用：管理接口	调用：请求决策	查询审计	管理配置
关键约束：

Lab 不直接调用 Bridge，不直接读取 TwinObject 的 CoreRuntimeView

Bridge 不直接调用 Lab，不读取 Lab 原始输出

Core 是唯一有权写入 TwinObject 运行时状态的系统

所有对物理世界的控制指令必须经过 Core 的安全回路

二、通用约定
2.1 视图投影
所有对 TwinObject 和 DomainPack 的读取，必须通过视图投影层。调用方声明自己的视图类型，投影层返回该视图允许的字段子集。

text
投影请求：
  GET /twin/{twin_id}/view/{view_type}
  view_type ∈ {CoreRuntimeView, CoreCertificationView, LabExplorationView, BridgeDecisionView, AuditView}

投影响应：
  TwinObject 的对应视图子集
DomainPack 同理：

text
  GET /domain/{domain_id}/view/{view_type}
  view_type ∈ {CoreFullView, BridgeActionView, LabExplorationView, AuditView}
2.2 快照与版本
Core 在每次重大状态变更后生成不可变快照。Bridge 基于快照生成行动空间。Lab 提交的证据包关联到快照版本。

text
SnapshotId = {twin_id}_{timestamp}_{hash}
所有跨系统引用必须携带 SnapshotId 或 TwinObjectVersion，用于审计追溯。

2.3 链路命名
对齐 Core v1.3 的链路权限矩阵：

链路	标识符	说明
生产预测	production_prediction	模型输出用于生产预测
生产诊断	production_diagnostic	模型输出用于生产诊断
生产控制	production_control	模型输出驱动物理执行器
仅诊断	diagnostic_only	模型输出仅用于诊断，不参与控制
影子	shadow	后台评估，输出不对外
离线沙盒	offline_sandbox	Lab 产物提交入口，安全隔离
物理探测	physical_probe	经批准的主动探测执行
拒绝	rejected	禁止在任何链路运行
2.4 错误处理统一格式
text
ErrorResponse = {
  error_code,
  error_type: constraint_violation | qualification_failed | view_denied | invalid_snapshot | timeout | internal,
  detail,
  trace_id
}
三、Core 运行时接口
3.1 资格审判
调用方：Core 内部定时触发 / 外部事件触发（模型注册、约束变更、状态域变化）

输入：

text
QualificationRequest = {
  twin_id,
  model_id,
  target_links: list of LinkType,    // 申请的链路权限
  current_snapshot_id,
  task_context: prediction | diagnostic | control | exploration
}
处理流程：

从 TwinObject 读取 CoreRuntimeView

遍历 target_links 中的每个 link_type，执行 HardGate

对通过 HardGate 的 link_type，执行 RiskGate

对 control 类 link_type（production_control、physical_probe），额外执行干预有效性审查

生成资格判决

输出：

text
QualificationResult = {
  twin_id,
  model_id,
  snapshot_id,
  results: list of {
    link_type,
    verdict: granted | degraded | denied,
    hardgate_details,
    riskgate_details,
    intervention_validity,          // 仅 control 类
    granted_permissions,            // 实际授予的链路权限
    expiry,
    conditions                       // 降权条件
  },
  audit: {
    judged_at,
    judged_by,
    qualification_id
  }
}
后续动作：

Core 将结果写入 TwinObject 的 model_governance_state

若 production_control 资格被撤销且无替代模型，触发安全回落

3.2 约束验证
调用方：Core 在每次模型输出释放前调用

输入：

text
ConstraintVerificationRequest = {
  twin_id,
  model_id,
  proposed_output,                  // 模型输出的预测/控制
  current_state_snapshot_id,
  constraint_ids: list              // 需验证的约束卡片ID，空=全部激活约束
}
处理流程：

读取当前约束状态和约束卡片

对每个约束卡片执行 certifier

区分 pass / uncertain / fail / not_applicable

对 not_applicable 的约束执行挂起逻辑

输出：

text
ConstraintVerificationResult = {
  twin_id,
  verification_id,
  overall_verdict: pass | uncertain | fail,
  per_constraint: list of {
    constraint_id,
    verdict: pass | uncertain | fail | not_applicable,
    details,
    suspended_if_not_applicable
  },
  // 若 overall_verdict = fail，附失败诊断
  failure_diagnosis: {
    suspected_cause,
    recommended_action
  }
}
关键规则：

safety_critical 约束若返回 fail，模型输出立即阻止

not_applicable 的约束进入 suspended，记录挂起原因

3.3 安全回落触发
调用方：Core 运行时监控

触发条件（任一满足即触发）：

production_control 链路模型全部资格丧失

身份不确定状态超时

约束冲突不可解决

主动探测失败

人类接管请求超时应答

Bridge 行动选项全部失效且无新快照

输出：

text
SafeFallbackTrigger = {
  twin_id,
  trigger_reason,
  snapshot_id,
  fallback_policy_id,
  target_state,
  trajectory_constraints,
  max_duration,
  unavailable_action,
  post_fallback_action,
  triggered_at
}
执行：Core 直接执行，不等待人类批准。同时写入 TwinObject 的 action_state 和 audit.safety_events。

3.4 证据准入
调用方：Core 在收到 Lab 提交后触发

输入：

text
EvidenceAdmissionRequest = {
  submission_id,                    // 来自 SubmissionQuarantine 的输出
  evidence_type: model | constraint_hypothesis | uncertainty_evidence | scenario | negative_result | probe_proposal,
  quarantine_result,                // 检疫扫描结果
  target_sandbox: offline_sandbox
}
处理流程：

验证 quarantine 状态为 cleared

对模型类证据执行 sandbox 级别的 HardGate

对约束假设类证据标记为 candidate，不自动提升

写入 TwinObject 的 knowledge_state.admitted_lab_evidence

输出：

text
EvidenceAdmissionResult = {
  submission_id,
  admitted: true | false,
  admission_id,
  admitted_at,
  evidence_status: admitted | rejected_with_reason,
  rejection_reason,                 // 若拒绝
  target_link: offline_sandbox,
  next_step: await_qualification | await_review | rejected
}
关键约束：

此接口不执行链路升级。从 offline_sandbox 到更高链路的升级由资格审判接口（3.1）独立执行。

Core 只写入 knowledge_state.admitted_lab_evidence，不修改 Lab 原始提交。

四、Lab 接口
4.1 证据提交
调用方：Lab → Core

输入：

text
LabSubmission = {
  lab_id,
  lab_instance_id,
  submission_id,
  twin_id,
  snapshot_id_reference,            // Lab 基于哪个版本的 ExplorationContext
  payload: {
    candidate_models: list of CandidateModelPackage,
    constraint_hypotheses: list of ConstraintHypothesisPackage,
    uncertainty_evidence: list of UncertaintyEvidencePackage,
    active_probe_proposals: list of ActiveProbeProposal,
    negative_results: list of NegativeResultPackage,
    candidate_scenarios: list of ScenarioPackage
  },
  exploration_summary: {
    budget_consumed_per_category,
    structures_searched,
    hypotheses_generated,
    hypotheses_falsified,
    failure_modes_discovered,
    negative_results_produced,
    unknown_domains_identified,
    data_packages_used
  }
}
处理流程：

进入 SubmissionQuarantine

检疫扫描（恶意代码、敏感信息泄露、资源异常）

通过检疫后，Core 调用证据准入接口（3.4）

Core 将准入结果写入 TwinObject

Core 向 Lab 返回模糊反馈

输出：

text
LabSubmissionResponse = {
  submission_id,
  status: received | quarantined | admitted | rejected,
  admission_id,                     // 若准入
  feedback: {
    // 不包含隐藏验证集的 membership 信息
    // 不包含具体拒绝原因的完整细节（若涉及安全敏感信息）
    admitted_items_count,
    rejected_items_count,
    feedback_summary                // 聚合、脱敏后的反馈摘要
  }
}
4.2 探索上下文拉取
调用方：Lab → TwinObject（通过 LabExplorationView）

输入：

text
ExplorationContextRequest = {
  lab_id,
  twin_id,
  last_known_snapshot_id            // 可选：增量更新
}
输出：LabExplorationView 的当前快照，包含：

状态语义

约束公开摘要

公开评估集引用

已准入证据的历史状态

活跃假设摘要

已知未知域

可用 DataReleasePackage 列表

关键约束：此接口不返回 audit_benchmark、hidden_challenge_set、production_acceptance_suite、model_governance_state 完整内容。

4.3 数据包请求
调用方：Lab → 外部数据治理系统（非 Core）

输入：

text
DataPackageRequest = {
  lab_id,
  requested_packages: list of DataReleasePackageId,
  intended_use,
  expected_derivatives
}
输出：授权的 DataReleasePackage 列表（含派生许可和保留策略）

约束：此接口由外部数据治理系统独立管理，Core 不参与。Lab 不得绕过此接口直接访问原始数据。

五、Bridge 接口
5.1 行动空间生成
调用方：人类/外部系统 → Bridge

输入：

text
ActionSpaceRequest = {
  twin_id,
  request_reason,                   // 为何请求行动空间（定期审查/异常响应/人工查询）
  preferred_snapshot_id             // 可选：指定快照
}
处理流程：

Bridge 从 TwinObject 拉取 BridgeDecisionView（基于最新快照或指定快照）

Bridge 从 DomainPack 拉取 BridgeActionView

Bridge 将两者映射为结构化行动选项

Bridge 生成 BridgeOutput，含有效期和失效触发器

Bridge 生成 BridgeDecisionRecord，提交至外部审计设施

输出：BridgeOutput（完整结构见 Bridge v0.3 第 2.2 节）

5.2 人类行动记录
调用方：人类/外部执行系统 → Bridge

输入：

text
HumanActionRecord = {
  bridge_output_id,                 // 基于哪个 BridgeOutput
  selected_action_id,
  execution_mode,
  fresh_core_check_performed,       // 是否执行了新鲜 Core 确认
  fresh_core_check_result,          // 新鲜确认结果
  human_role,
  exception_request_applied,
  exception_request_type,
  risk_acknowledged,
  prerequisites_acknowledged
}
处理流程：

验证 BridgeOutput 是否仍在有效期内

验证所选行动的 execution_mode 与人类角色是否匹配

若行动需要 fresh_core_check，验证 fresh_core_check_performed = true

生成或补全 BridgeDecisionRecord

若行动为 request_core_execution，向 Core 发起执行请求

输出：

text
HumanActionResponse = {
  recorded: true | false,
  decision_record_id,
  next_step: {
    action_executed,                // 行动已被授权执行
    action_rejected_due_to_expiry,  // BridgeOutput 已过期，需重新请求
    action_rejected_due_to_unauthorized,  // 人类角色无权执行该行动
    action_forwarded_to_core,       // 已转发至 Core 审核
    requires_fresh_action_space     // 需重新生成
  }
}
5.3 决策历史查询
调用方：审计系统/人类 → 外部审计设施

Bridge 不直接提供历史查询。所有 BridgeDecisionRecord 由外部审计设施持久化，查询通过审计接口完成。

六、TwinObject 管理接口
6.1 生命周期管理
调用方：Core / 人工

text
操作：
  InitializeTwin(domain_pack_id, initial_config) → twin_id
  UpdateTwinVersion(twin_id, update_spec) → new_snapshot_id
  BranchTwin(twin_id, branch_event) → child_twin_id
  RebuildTwin(twin_id, rebuild_reason) → new_twin_id
  RetireTwin(twin_id, retirement_reason) → retired_snapshot_id
  TransitionLifecycleState(twin_id, from_state, to_state, reason) → new_snapshot_id
每个操作生成不可变快照，写入 TwinLineage。

6.2 视图查询
text
GET /twin/{twin_id}/view/CoreRuntimeView
GET /twin/{twin_id}/view/CoreCertificationView
GET /twin/{twin_id}/view/LabExplorationView
GET /twin/{twin_id}/view/BridgeDecisionView
GET /twin/{twin_id}/view/AuditView
返回对应视图的当前快照。

6.3 写入操作
所有写入必须声明写入方身份。Core 写入通过 Core 运行时接口完成。人工写入通过审批工作流接口完成。Lab 不直接写入。

七、DomainPack 管理接口
7.1 配置加载
调用方：Core / Lab / Bridge 启动时

text
操作：
  LoadDomainPack(domain_id, view_type) → DomainPackView
  ResolveInheritance(domain_id, max_depth) → resolved_domain_pack
  ValidateDomainPack(domain_id) → validation_result
ValidateDomainPack 必须检查刚性-关键性兼容规则（DomainPack v0.3 第二章）。

7.2 视图查询
text
GET /domain/{domain_id}/view/CoreFullView
GET /domain/{domain_id}/view/BridgeActionView
GET /domain/{domain_id}/view/LabExplorationView
GET /domain/{domain_id}/view/AuditView
7.3 生命周期管理
text
操作：
  CertifyDomainPack(domain_id) → certified
  PromoteToProduction(domain_id) → production
  DeprecateDomainPack(domain_id, reason) → deprecated
  RetireDomainPack(domain_id, retirement_reason) → retired
父包退役后，系统遍历所有子包，按 parent_retirement_action_by_reason 执行相应动作。

八、审批与人工接口
8.1 例外审批
调用方：人类（通过外部审批系统）

text
操作：
  RequestConstraintReview(twin_id, constraint_id, reason)
  RequestRecertification(twin_id, model_id, reason)
  RequestConstraintRevision(twin_id, constraint_id, proposed_change)
  RequestHumanTakeover(twin_id, reason)
  RequestSafeShutdown(twin_id, reason)
每个请求生成审计事件，写入 TwinObject 的 audit.human_decisions。Core 在收到请求后，根据 DomainPack 中定义的角色权限判断是否批准。

8.2 身份决策
text
操作：
  ConfirmIdentityContinuity(twin_id) → 从 identity_uncertain 迁移至 active + version_update
  ConfirmIdentityBranch(twin_id, branch_spec) → 创建 child twin, 当前 twin 继续
  ConfirmIdentityRebuild(twin_id, rebuild_spec) → 当前 twin retired, 创建 new twin
所有身份决策必须人工确认。Core 可以提供建议，但不能自动执行 branch 或 rebuild。

九、外部系统接口
9.1 审计日志查询
调用方：审计系统

text
GET /audit/twin/{twin_id}/events?from={timestamp}&to={timestamp}&type={event_type}
GET /audit/twin/{twin_id}/snapshot/{snapshot_id}
GET /audit/twin/{twin_id}/lineage
9.2 数据治理接口
调用方：外部数据治理系统

text
操作：
  IssueDataReleasePackage(package_spec) → DataReleasePackage
  RevokeDataReleasePackage(package_id, reason) → 触发撤回传播
  AuditDataAccess(lab_id, package_id, timeframe) → access_log
撤回传播：被撤回的 DataReleasePackage 导致所有派生物和依赖产物标记为 invalidated 或 requires_revalidation。

9.3 物理世界接口
不在本规范范围内。 Core 对物理世界的控制通过 CoreExecute 通道完成，具体实现取决于工业场景的控制器接口。唯一进入本规范的物理相关接口是 Core 的安全回落触发——它确保物理系统在安全退化时收到正确的目标状态和轨迹约束。

十、接口调用时序示例
10.1 Lab 提交 → Core 准入 → 链路升级
text
Lab                    SubmissionQuarantine        Core                    TwinObject
 │                              │                   │                         │
 │──提交证据包────────────────►│                   │                         │
 │                              │──检疫扫描────────►│                         │
 │                              │                   │──HardGate(sandbox)─────►│
 │                              │                   │◄──结果─────────────────│
 │                              │                   │──写入admitted_evidence─►│
 │◄──反馈(admitted)────────────│◄──────────────────│                         │
 │                              │                   │                         │
 │                              │    [后续：链路升级] │                         │
 │                              │                   │──QualificationRequest──►│
 │                              │                   │◄──QualificationResult───│
 │                              │                   │──更新model_governance──►│
10.2 Bridge 生成行动空间 → 人类选择 → Core 执行
text
Human              Bridge                  TwinObject              Core
 │                   │                         │                     │
 │──请求行动空间────►│                         │                     │
 │                   │──拉取BridgeDecisionView─►│                     │
 │                   │◄──视图快照──────────────│                     │
 │                   │──拉取BridgeActionView───│(DomainPack)          │
 │                   │──生成BridgeOutput       │                     │
 │                   │──提交DecisionRecord─────│(审计设施)            │
 │◄──行动空间────────│                         │                     │
 │                   │                         │                     │
 │──人类选择────────►│                         │                     │
 │                   │──验证有效期/权限        │                     │
 │                   │──若request_core_exec───│────────────────────►│
 │                   │                         │──新鲜Core确认──────►│
 │                   │                         │◄──确认结果─────────│
 │◄──执行确认────────│◄────────────────────────│                     │
10.3 安全回落
text
Core                    TwinObject              物理世界
 │                         │                       │
 │──检测触发条件           │                       │
 │──判定不可恢复           │                       │
 │──读取SafeFallbackPolicy─►                       │
 │◄──策略详情─────────────│                       │
 │──写入action_state──────►                       │
 │──写入safety_event──────►                       │
 │──发出回落指令─────────────────────────────────►│
 │                         │                       │──执行安全轨迹
 │                         │                       │──到达目标状态
 │──更新lifecycle_state───►                       │
十一、接口实现的前置条件与约束
11.1 必须已实现的基础设施
基础设施	用途
不可变快照存储	TwinObject 版本化、审计追溯
视图投影引擎	根据调用方身份返回对应视图
检疫扫描服务	Lab 提交的产物安全扫描
约束验证器注册表	约束卡片的 certifier 调用分发
外部审计日志系统	BridgeDecisionRecord 和审计事件的防篡改存储
DataReleasePackage 管理服务	数据包的签发、授权、撤回传播
审批工作流引擎	例外审批、身份决策的人工流程
11.2 接口实现的约束
Lab 与 Core 之间的网络隔离：Lab 只能通过 SubmissionQuarantine 向 Core 提交数据。Lab 不可直接调用 Core 的任何其他接口。

Bridge 与 Core 之间无直接写入：Bridge 读取 Core 状态快照，但不写入 TwinObject。Bridge 的审计记录写入外部审计设施，不写入 Core。

Core 对物理世界的独占通道：所有对物理执行器的指令必须经过 Core 的安全回路。Bridge 和 Lab 没有物理世界通道。

视图投影的强制执行：任何对 TwinObject 和 DomainPack 的读取必须经过视图投影层。调用方不可绕过视图直接访问底层存储。

十二、本规范不覆盖的内容
具体传输协议（gRPC/REST/消息队列）——实现选择

服务发现与负载均衡——运维架构

加密与认证机制——安全架构

日志存储具体方案——基础设施选择

物理控制器的具体接口——场景特定实现

外部知识库的本体论设计——领域工程

人机交互的UI/UX——外围系统

十三、定位声明
本接口规范定义了 Polymorphic-Twin 生态中五个组件之间的调用关系、数据格式、状态机和约束。它基于 Core v1.3、Lab v0.4、Bridge v0.3、TwinObjectModel v0.3、DomainPack v0.3 的核心原则，将“什么可信、有什么新证据、人能做什么、系统在孪生什么、这个场景是什么”这五个问题的答案，编织成一个可实施的系统间契约。

它不是实现指南，而是实现必须遵守的边界。任何实现，只要满足本规范定义的接口契约、视图隔离规则和写入权限矩阵，就是一个合法的 Polymorphic-Twin 生态实例。