Polymorphic-Twin 生态接口规范 v1.1

前置说明
本规范定义 Polymorphic-Twin 生态中五个组件之间的接口，基于以下核心原则定稿：

组件	定稿版本	性质
Core	v1.3	运行时系统：约束治理、资格审判、安全退化
Lab	v0.4	离线系统：隔离探索、证据供应
Bridge	v0.3	无状态接口层：行动空间映射、决策审计
TwinObjectModel	v0.3	统一数据对象定义
DomainPack	v0.3	场景实例化配置单元
本规范不重复各组件的内部原理，仅定义调用关系、数据格式、前置条件和必须满足的契约。

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
调用关系矩阵（v1.1 修正）：

调用方 ↓ / 被调用方 →	Core	Lab	Bridge	TwinObject	DomainPack Mgr
Core	—	不调用（Lab 主动提交）	不调用（Bridge 由人类触发）	读写	读取配置
Lab	提交证据包	—	不调用	只读(Lab视图)	只读(Lab视图)
Bridge	不调用	不直接调用	—	只读(Bridge视图)	只读(Bridge视图)
人类/运维	调用审批接口	调用管理接口	调用行动空间与记录	查询审计	管理配置
关键约束：

Core 不主动调用 Lab。Lab 通过 SubmitEvidence 接口向 Core 提交证据包。

Core 不主动调用 Bridge。Bridge 由人类或外部系统查询触发，基于 Core 写入 TwinObject 的状态快照生成行动空间。

Lab 不可直接读取 TwinObject 的 CoreRuntimeView 或 CoreCertificationView。

Bridge 不可直接读取 Lab 原始输出，只可通过 Core-admitted Lab Evidence View 获取已准入证据。

所有对物理世界的控制指令必须经过 Core 的安全回路。

二、通用约定
2.1 请求上下文（v1.1 新增）
所有接口调用必须携带统一的请求上下文：

text
RequestContext = {
  request_id,                 // 全局唯一请求ID
  caller_id,                  // 调用方标识（core_instance / lab_id / bridge_instance / human_user_id）
  caller_type,                // core_runtime / core_certification / lab / bridge / human / admin
  timestamp,
  trace_parent_id,            // 分布式追踪父Span ID
  auth_token_hash             // 认证凭证的不可逆哈希
}
每个响应中回显 request_id。

2.2 视图投影
对 TwinObject 和 DomainPack 的读取必须通过视图投影。调用方声明视图类型，投影层返回该视图允许的字段子集。

text
投影请求（在请求上下文中指定）：
  target: twin/{twin_id} or domain/{domain_id}
  view_type: CoreRuntimeView | CoreCertificationView | LabExplorationView | BridgeDecisionView | AuditView
            （DomainPack 对应 CoreFullView | BridgeActionView | LabExplorationView | AuditView）
2.3 快照与版本
Core 在每次重大状态变更后生成不可变快照。所有跨系统引用必须携带快照标识或对象版本。

text
SnapshotId = {twin_id}_{timestamp}_{hash}
TwinObjectVersion = {major}.{minor}.{patch}
DomainPackVersion = {domain_id}:{major}.{minor}
Bridge 输出必须绑定生成时所基于的 TwinObjectVersion 和 DomainPackVersion（见 5.1 节）。

2.4 链路命名
对齐 Core v1.3 权限矩阵：

链路	标识符	说明
生产预测	production_prediction	模型输出用于生产预测
生产诊断	production_diagnostic	模型输出用于生产诊断
生产控制	production_control	模型输出驱动物理执行器
仅诊断	diagnostic_only	仅诊断，不参与控制
影子	shadow	后台评估，输出不对外
离线沙盒	offline_sandbox	Lab 产物提交入口，安全隔离
物理探测	physical_probe	经批准的主动探测执行
拒绝	rejected	全链路禁止
2.5 错误处理统一格式
text
ErrorResponse = {
  request_id,                 // 回显
  error_code,
  error_type,
  detail,
  trace_id
}
三、Core 运行时接口
3.1 资格审判
触发方：Core 内部（模型注册、约束变更、状态域变化、链路升级请求）

输入：

text
QualificationRequest = {
  context: RequestContext,                // v1.1：统一请求上下文
  twin_id,
  model_id,
  target_links: list of LinkType,
  current_snapshot_id,
  task_context: prediction | diagnostic | control | exploration
}
处理流程（不变，略）

输出：

text
QualificationResult = {
  request_id,
  twin_id,
  model_id,
  snapshot_id,
  results: list of {
    link_type,
    verdict: granted | degraded | denied,
    hardgate_details,
    riskgate_details,
    intervention_validity,               // 仅 control 类
    granted_permissions,
    expiry,
    conditions
  },
  audit: {
    judged_at,
    judged_by_qualification_id
  }
}
3.2 约束验证（v1.1 增加 criticality 处理）
触发方：Core 在模型输出释放前调用

输入：

text
ConstraintVerificationRequest = {
  context: RequestContext,
  twin_id,
  model_id,
  proposed_output,
  current_state_snapshot_id,
  constraint_ids: list              // 空=所有激活约束
}
处理流程：

对每个约束执行 certifier

标记每个约束的关键性 (scenario_criticality) 和适用域状态

若 safety_critical 约束 fail，立即终止并阻止输出

not_applicable 的约束按挂起流程处理

输出：

text
ConstraintVerificationResult = {
  request_id,
  twin_id,
  verification_id,
  overall_verdict,
  per_constraint: list of {
    constraint_id,
    scenario_criticality,                 // v1.1 新增
    verdict: pass | uncertain | fail | not_applicable,
    details,
    suspend_effect_if_not_applicable,     // v1.1 新增：若 not_applicable，此约束挂起后的影响范围
    suspension_record_id                  // 若已挂起，关联挂起记录
  },
  failure_diagnosis
}
3.3 安全回落触发（v1.1 调整触发条件）
触发条件（从 Bridge 输出失效改为 safe_action_set 不可用）：

production_control 模型全部资格丧失

身份不确定状态超时

约束冲突不可解决

主动探测失败

人类接管超时应答

当前 safe_action_set.nonempty = false 且无可用退化路径

输出：SafeFallbackTrigger 结构不变。

3.4 证据准入（改为 item 级结果）
触发方：Core 在收到 Lab 提交后触发

输入：

text
EvidenceAdmissionRequest = {
  context: RequestContext,
  submission_id,
  quarantine_result,
  items: list of {                         // v1.1：每个证据项独立评估
    item_id,
    evidence_type,
    quarantine_item_result
  }
}
输出（v1.1 改为 item 级）：

text
EvidenceAdmissionResult = {
  request_id,
  submission_id,
  items: list of {
    item_id,
    admitted: true | false,
    admission_id,
    evidence_status,
    rejection_reason,
    target_link: offline_sandbox
  },
  summary: {
    total_items,
    admitted_count,
    rejected_count
  }
}
规则：每个 item 独立准入。一个模型被拒绝不影响同批次约束假设的准入。

四、Lab 接口
4.1 证据提交
调用方：Lab → Core

输入：LabSubmission 结构增加 context: RequestContext，其余不变。

输出：LabSubmissionResponse 增加 request_id，其余不变。

4.2 探索上下文拉取
调用方：Lab → TwinObject（LabExplorationView）

请求和响应增加 context: RequestContext。

4.3 数据包请求
调用方：Lab → 外部数据治理

请求增加 context: RequestContext。

五、Bridge 接口
5.1 行动空间生成（绑定一致性版本）
调用方：人类/外部系统 → Bridge

输入：ActionSpaceRequest 增加 context: RequestContext。

输出：BridgeOutput 增加以下字段：

text
BridgeOutput = {
  ...原有字段,
  audit: {
    core_snapshot_id,
    twin_object_version,                  // v1.1 新增：生成时 TwinObject 版本号
    domain_pack_version,                  // v1.1 新增：生成时 DomainPack 版本号
    lab_evidence_batch_id,
    bridge_version,
    action_template_version
  },
  // v1.1 新增：一致性声明
  consistency_binding: {
    twin_object_version,
    domain_pack_id,
    domain_pack_version,
    snapshot_id,
    // 若此后 TwinObject 或 DomainPack 版本变化，此 BridgeOutput 应立即标记为过期
    invalidated_by_version_mismatch: false
  }
}
原则：一旦 TwinObject 的主版本号或 DomainPack 的版本号与 consistency_binding 中记录的不一致，该 BridgeOutput 必须标记为失效，即使未到 valid_until。

5.2 人类行动记录
请求和响应增加 context: RequestContext。

HumanActionResponse 中 action_executed 改名为 action_accepted_for_execution（v1.1 P1 建议），避免误解为“已真实执行”。真实执行由 Core 执行通道返回执行结果。

六、TwinObject 管理接口
所有操作增加 context: RequestContext。其余不变。

七、DomainPack 管理接口
所有操作增加 context: RequestContext。

DomainPack CoreFullView 目前定义为全部字段可见。后续可根据 Core 运行时与认证的职责拆分进一步视图化，当前版本保留此设计，标记为“待后续拆分”（对应 P1 建议）。

八、审批与人工接口
所有请求增加 context: RequestContext。

九、外部系统接口
不变（审计日志查询等外部系统也需满足 RequestContext 约定）。

十、接口实现的前置条件与约束（v1.1 微调）
10.1 必须已实现的基础设施（补充）
分布式追踪基础设施（支持 RequestContext 中的 trace 传递）

版本化快照存储（支持 TwinObject 主版本与 DomainPack 版本绑定）

10.2 接口实现的约束（修正）
Lab 与 Core 的网络隔离：Lab 仅通过 SubmitEvidence 单向提交。Core 不主动访问 Lab 的任何接口。

Bridge 的独立性：Bridge 不直接依赖 Core 的运行时状态，只读取 TwinObject 的 BridgeDecisionView。人类触发 Bridge 生成行动空间，Core 不调用 Bridge。

Core 对物理世界的独占通道：不变。

视图投影的强制执行：不变，且投影逻辑需包含版本一致性检查。

版本绑定强制检查：Bridge 生成输出时记录 TwinObject/DomainPack 版本，后续任何一致性校验失败将触发输出失效。

十一、定位声明
本接口规范 v1.1 在 v1.0 基础上闭合了关键契约缺口：统一了请求上下文，明确了 Core 不调用 Lab/Bridge 的隔离边界，将 Bridge 行动空间绑定到具体的 TwinObject 与 DomainPack 版本，约束验证结果纳入了关键性和挂起影响，证据准入细化为项目级判决。以此为实施契约，Polymorphic-Twin 生态可进入架构实现阶段。