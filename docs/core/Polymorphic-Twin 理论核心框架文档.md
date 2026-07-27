Polymorphic-Twin 理论核心框架文档
下面是一版可作为总纲的理论核心框架文档。

Polymorphic-Twin 理论核心框架 v1.0
1. 系统最终目标
Polymorphic-Twin 的目标不是构建一个更准的预测模型，也不是替代仿真器、控制器、机器学习平台或行业专家系统。

它的目标是构建一套：

面向不完全已知、持续变化、模型相互冲突的物理/生理/工业系统的可信数字孪生治理基础设施。

它要解决的问题是：

当我们不完全知道真实系统发生了什么，但又必须预测、诊断、控制、干预或决策时，系统如何判断当前什么可信、什么不可信、谁有资格发言、哪些行动可执行、哪些必须禁止，以及在不确定时如何安全退下。

因此，Polymorphic-Twin 的核心不是“预测”，而是：

text
可信性治理 + 证据进化 + 行动边界管理
2. 根本问题
传统数字孪生常默认：

text
有一个模型 → 预测未来 → 辅助控制
但真实工业场景的问题更复杂：

系统会退化；
传感器会漂；
模型会 OOD；
多模型会冲突；
物理约束会有适用域；
新工况下旧身份可能失效；
人类仍必须行动；
自动进化可能污染安全边界。
所以根本问题不是：

未来会怎样？

而是：

在当前观测、约束、证据和不确定性下，我能相信什么？我不能相信什么？如果我不知道，我该如何安全行动？

3. 总体定位
Polymorphic-Twin 是部署在以下断层上的基础设施：

text
真实物理世界
  ↕
传感器 / 控制器 / 仿真器 / 机器学习模型 / 领域知识
  ↕
不确定性、冲突、退化、身份变化
  ↕
人类决策与物理行动
它不是底层物理仿真器，也不是控制器，而是：

位于模型、证据、约束和行动之间的可信治理层。

4. 总体结构：三系统 + 两基础结构
最终结构为：

text
Polymorphic-Twin Ecosystem =
  Core
  + Lab
  + Bridge
  + TwinObjectModel
  + DomainPack
5. 三个系统
5.1 Core：约束治理核
Core 回答：

当前什么可信？什么不可信？什么可以释放？什么必须拒绝？

职责：

约束卡片治理；
模型资格审判；
链路权限管理；
不确定性证书检查；
身份连续性监控；
安全回落；
失败理论执行；
物理行动的唯一安全通道。
Core 不做：

不训练模型；
不自动探索新结构；
不替人决策；
不直接生成行动建议；
不绕过约束。
核心原则：

text
不释放未通过约束验证的安全相关输出。
不允许无证书模型进入安全相关生产链路。
不知道时安全退下。
5.2 Lab：隔离探索证据供应链
Lab 回答：

有什么新证据、新反例、新候选值得被审判？

职责：

生成候选模型；
生成约束假设；
生成不确定性证据包；
生成反事实场景；
生成负面结果；
发现未知域；
持续扩展系统的知识边界。
Lab 不做：

不接触物理世界；
不执行真实主动探测；
不颁发证书；
不制定绝对约束；
不访问隐藏验证集；
不直接进入生产链路；
不把自己的产物升级。
核心原则：

text
Lab 生成证据，不生成判决。
Lab 自由，因为它隔离。
Lab 有用，因为它接受 Core 审判。
5.3 Bridge：决策接口与行动治理层
Bridge 回答：

在当前知识边界下，人可以做什么、不能做什么、需要什么条件才能做？

职责：

读取 BridgeDecisionView；
读取 Core-admitted Lab Evidence View；
读取 DomainPack 行动模板；
生成结构化行动空间；
显示已知、未知、不确定；
标明行动前提、风险、证书、审批要求；
记录人类选择的审计记录。
Bridge 不做：

不输出单一建议；
不替人决策；
不推翻 Core；
不把 Lab 证据当事实；
不执行控制；
不学习偏好；
不维护业务状态。
核心原则：

text
Bridge 输出行动空间，不输出“你应该做什么”。
6. 两个基础结构
6.1 TwinObjectModel：统一孪生对象模型
TwinObjectModel 回答：

三系统到底围绕哪个“对象”工作？

它承载：

身份与谱系；
状态语义；
约束状态；
身份不变量；
模型治理状态；
知识状态；
行动与安全状态；
审计追溯。
核心原则：

text
Core、Lab、Bridge 都围绕同一个 TwinObject 工作。
但它们通过不同视图访问，不共享裸对象。
6.2 DomainPack：场景实例化配置单元
DomainPack 回答：

在这个具体工业场景里，状态是什么、约束是什么、安全策略是什么、行动模板是什么？

它声明：

状态语义实例化；
约束卡片引用与适用域；
刚性-关键性兼容规则；
安全回落策略；
行动空间模板；
人类角色权限；
验证集引用；
继承规则；
多视图。
核心原则：

text
通用性来自内核，场景可用性来自 DomainPack。
7. 五个核心闭环
7.1 可信性闭环
text
模型输出
→ Core 约束验证
→ HardGate / RiskGate
→ 链路权限
→ 输出释放或拒绝
目标：

防止失效模型在未知域继续发言。

7.2 证据进化闭环
text
Lab 生成候选证据
→ SubmissionQuarantine
→ Core offline_sandbox
→ Core 准入
→ shadow / diagnostic / production 逐级升级
目标：

允许系统持续进化，但不让进化污染生产安全。

7.3 身份连续性闭环
text
观测偏离
→ 可辨识性分析
→ identity_uncertain
→ version_update / identity_branch / identity_rebuild
→ TwinLineage 记录
目标：

系统变化时，知道自己是否还是同一个系统。

7.4 行动治理闭环
text
Core 状态 + Lab 证据 + DomainPack 行动模板
→ Bridge ActionSpace
→ 人类选择
→ 审计记录
→ Core 新鲜确认
→ 执行 / 拒绝 / 回落
目标：

帮助人在不确定中安全行动，而不是只输出“我不知道”。

7.5 安全退化闭环
text
约束失败 / 身份不确定 / 控制资格丧失
→ SafeFallbackPolicy
→ 安全保持 / 接管 / 停机
→ 审计记录
目标：

当系统无法可靠判断时，仍能安全退下。

8. 后续实际系统框架开发建议
阶段 0：冻结原则层
当前已经完成：

text
Core v1.3
Lab v0.4
Bridge v0.3
TwinObjectModel v0.3
DomainPack v0.3
接口规范 v1.0
建议不再继续大幅修改原则稿。

接下来应进入：

text
接口规范 v1.1
→ 抽象架构设计
→ MVP 场景实现
阶段 1：接口规范 v1.1 小修
优先修：

修正接口矩阵；
增加 RequestContext；
增加快照一致性机制；
约束验证结果增加 criticality / suspend_effect；
证据准入改为 item 级；
安全回落触发条件改为基于 safe_action_set；
HumanActionResponse 消除执行歧义。
通过标准：

text
所有跨系统调用都有调用方身份。
所有视图读取都有 view_type。
所有输出都有 snapshot/version。
所有 Lab 产物都有 item 级准入结果。
所有 Bridge 行动都有有效期和新鲜 Core 确认要求。
阶段 2：实现最小 TwinObject + 视图投影
先不做模型，不做控制。

先实现：

TwinObject 存储；
快照机制；
视图投影；
写入权限矩阵；
审计追加日志。
通过标准：

text
Lab 无法读取 hidden 字段。
Bridge 无法读取 Lab 原始证据。
CoreRuntime 无法读取 hidden challenge set。
AuditView 只离线可用。
所有写入生成新快照。
阶段 3：实现 Core 最小闭环
最小 Core 只需要：

加载 DomainPack；
初始化 TwinObject；
注册一个模型；
执行 HardGate；
执行约束验证；
生成链路权限；
在失败时触发 SafeFallbackPolicy。
通过标准：

text
违反 safety_critical 约束的输出被阻止。
无有效不确定性证书的控制模型不能进入 production_control。
suspended safety_critical 约束关闭相关 production。
所有资格变化写入 TwinObject。
阶段 4：实现 Lab 最小证据供应链
最小 Lab 不需要进化算法。
先实现证据包提交机制：

CandidateModelPackage;
ConstraintHypothesisPackage;
NegativeResultPackage;
ScenarioPackage;
SubmissionQuarantine;
EvidenceAdmissionResult.
通过标准：

text
Lab 只能提交到 SubmissionQuarantine。
Lab 不能直接写 TwinObject。
证据准入结果为 item 级。
Lab 只收到模糊反馈。
被拒证据不进入 Core 链路。
阶段 5：实现 Bridge 最小行动空间
先不做人机 UI，只输出结构化 JSON。

实现：

读取 BridgeDecisionView;
读取 BridgeActionView;
生成 BridgeOutput;
生成 BridgeDecisionRecord;
支持 HumanActionRecord.
通过标准：

text
Bridge 不输出单一建议。
Bridge 不生成自然语言主导结论。
BridgeOutput 有 valid_until。
所有 immediate_actions 需要 fresh_core_check。
禁止动作必须说明合法解锁条件或永久禁止。
阶段 6：选择第一个 MVP 场景
建议从低风险、可仿真、可验证场景开始。

推荐顺序：

机器人仿真 sim-to-real 守门场景；
工业设备健康管理离线场景；
化学工艺仿真场景；
材料外推安全评估场景。
不建议第一阶段做：

医疗真实建议；
真实闭环自主控制；
高风险化工在线控制；
自动模型上线。
9. MVP 验证标准
9.1 核心功能标准
系统必须证明：

能拒绝 OOD 模型输出；
能区分模型失效与约束冲突；
能进入身份不确定状态；
能触发安全回落；
能从 Lab 接收候选证据但不直接上线；
能通过 Bridge 输出行动空间；
能完整审计人类选择。
9.2 安全标准
必须通过以下测试：

text
Safety Gate 1:
  safety_critical 约束 fail → 输出阻止

Safety Gate 2:
  safety_critical 约束 suspended → production 关闭或降级

Safety Gate 3:
  production_control 模型资格撤销 → safe_fallback 触发

Safety Gate 4:
  BridgeOutput 过期 → 行动不可执行

Safety Gate 5:
  Lab 试图访问 hidden_challenge_set → 拒绝

Safety Gate 6:
  人类试图 override Core safety rejection → 只能进入 exception_request 流程
9.3 演进标准
系统必须证明：

Lab 可提交候选模型；
候选模型先进入 offline_sandbox;
通过验证后可进入 shadow;
不能直接进入 production;
负面结果能降低错误方向优先级；
数据撤回能让依赖证据失效。
9.4 可审计标准
每个关键事件必须可追溯：

模型为什么获得资格；
模型为什么被拒绝；
约束为什么挂起；
人类为什么选择某行动；
哪个证据影响了决策；
哪个 DomainPack 版本生效；
哪个 TwinObject 快照被使用。
10. 项目开发关键风险
风险 1：系统膨胀成万能平台
防范：

坚持 Core/Lab/Bridge/TwinObject/DomainPack 的职责边界。

风险 2：Bridge 变成 AI 助手
防范：

Bridge 输出结构化行动空间，不输出自由建议。

风险 3：Lab 过拟合 Core 审判机制
防范：

隐藏验证集、模糊反馈、检疫、EvaluationSetLifecycle。

风险 4：DomainPack 变成知识工程黑洞
防范：

DomainPack 只引用已有知识库，只声明差异。

风险 5：Core 被过度复杂化
防范：

Core 只做审判、约束、安全、回落，不做探索，不做 UI，不做人类建议。

11. 最终理论定位
Polymorphic-Twin 的理论核心可以压缩为一句话：

它是一套部署在知识边界上的可信数字孪生治理生态：用 Core 判断什么可信，用 Lab 持续产生可审判的新证据，用 Bridge 把当前知识状态转化为可审计的行动空间，并用 TwinObject 与 DomainPack 保证对象一致性和场景可实例化。

它最终交付的不是一个预测值，而是：

text
我知道什么；
我不知道什么；
谁有资格发言；
谁必须沉默；
哪些行动现在可执行；
哪些行动需要条件；
哪些行动被禁止；
如果我也不知道，如何安全退下。
这就是它区别于传统数字孪生、仿真器、机器学习平台和控制系统的根本价值。