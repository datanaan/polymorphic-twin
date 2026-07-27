# Polymorphic-Twin 对 Jelly 团队回复的正式确认

> **版本**: 1.0.0
> **日期**: 2026-05-08
> **文档性质**: 双方协作契约
> **回复对象**: `2026-05-08-jelly-team-reply.md`
> **原始需求**: `2026-05-08-jelly-twin-provider-design.md`
> **确认方**: Polymorphic-Twin 项目组

---

## 一、总体确认

Polymorphic-Twin 确认 Jelly 团队的回复。Jelly 对 15 个 MCP 工具全部接受，对 13 个数据集的交付能力评估合理，架构建议专业。

以下是对 10 个问题的逐条确认，附自检后的修正。

---

## 二、10 个问题的逐条确认

### Q1: domain_id 命名空间

**确认方案：Jelly 内部使用 `twin.{industry}.{scenario}` 管理，MCP 接口同时接受两种格式。**

理由：Polymorphic-Twin 现有代码已使用简短格式：

| 现有 domain_id | 用途 | 来源文档 |
|---------------|------|----------|
| `cstr.standard` | CSTR 演示 | plan-M11a, product-demo |
| `example.minimal_device_monitor` | M0 验证 | plan-M0 |
| `chemical-reactor-thermal` | M6 多场景 | plan-M6 |
| `wind-turbine-bearing` | M6 多场景 | plan-M6 |
| `knowledge-management` | M6 多场景 | plan-M6 |

如果强制改为 `twin.chemical.cstr_standard`，所有引用点需同步修改，且 SDK 用户的学习成本增加。

**执行方式**：
- Jelly 存储层使用 `twin.{industry}.{scenario}` 作为内部主键
- MCP 接口层做双向映射：`cstr.standard` ↔ `twin.chemical.cstr_standard`
- Polymorphic-Twin 代码继续使用简短格式，SDK 面向用户也使用简短格式
- 新增 domain_id 时，由 Jelly 分配内部名，Polymorphic-Twin 确认简短名
- `twin.search_domain_packs` 返回结果中同时包含两种格式

映射关系在 Phase 1 开工前由双方对齐。

### Q2: DomainPack 生命周期

**确认方案：版本化实体，5 状态生命周期。**

Jelly 回复中提到 4 个状态（active、deprecated + 新版本自动 deprecate 旧版本）。Polymorphic-Twin 的设计规范中 DomainPack 有 5 个状态：

```
draft → review → active → deprecated → archived
```

**补充 `review` 状态的理由**：DomainPack 包含 safety_critical 约束，从 `draft` 直接进入 `active` 缺乏审核环节。`review` 是领域专家确认约束阈值正确性的必要步骤，尤其对安全关键场景不可省略。

| 状态 | 含义 | 谁触发 |
|------|------|--------|
| `draft` | 编辑中，不可用于生产 | 创建者 |
| `review` | 待领域专家审核 | 创建者提交 |
| `active` | 当前生效版本 | 审核通过 |
| `deprecated` | 已有新版本替代，仍可查询 | 新版本激活时自动触发 |
| `archived` | 历史归档，只读 | 手动归档 |

**`twin.list_domain_pack_versions` 的 status 枚举需更新为 5 值**（原设计文档中为 4 值，此处修正）。

### Q3: 验证数据集的边界 case 规格

**确认方案：Polymorphic-Twin 在 Phase 1 第 1 周内提供全部三种集合的规格。**

| 集合类型 | 谁生产 | Polymorphic-Twin 提供什么 | 何时提供 |
|----------|--------|--------------------------|----------|
| public_eval (100 cases) | Jelly 程序化生成 | 约束定义 + 状态变量范围 + 工况枚举 | 已在原始需求文档中 |
| audit_benchmark (50 cases) | Jelly 格式化入库 | 边界 case 规格（含精确阈值和期望判定） | Phase 1 第 1 周 |
| production_acceptance (30 cases) | Jelly 格式化入库 | 极端工况规格（含多约束同时触发的组合） | Phase 1 第 1 周 |

**格式**：JSON，每个 case 包含 `input_state`、`expected_result`（约束 ID → passed/failed/not_applicable）、`tags`。与原始需求文档中数据集 5 的格式完全一致。

**Phase 1 交付承诺**：如果 Polymorphic-Twin 未在第 1 周内提供规格，Phase 1 仍交付 public_eval（由 Jelly 按约束定义程序化生成），其余两种延至 Phase 2。

### Q4: 时序数据生成参数规格

**确认方案：以原始需求文档当前内容为准，无调整。**

文档中数据集 3 的六种工况参数已明确定义：

| 工况 | 参数 | 条数 |
|------|------|------|
| 正常稳态 | 温度 175-185°C，高斯噪声 σ=2 | 100 |
| 启动升温 | 温度 25→180°C 线性 | 100 |
| 传感器漂移 | 温度读数偏移 +0.5°C/周期 | 100 |
| 冷却失效 | coolant 下降，温度升至 250-260°C | 100 |
| 安全回落 | 温度突破 280°C | 100 |
| 恢复 | 从回落逐步恢复 | 100 |

这些参数的物理合理性由 Polymorphic-Twin 负责。Jelly 按规格生成后，Polymorphic-Twin 在集成测试中验收。

### Q5: 压测数据 domain_of_validity 边界组合

**确认方案：Jelly 按 5 种条件类型交叉组合生成，Polymorphic-Twin 验收。**

DomainPack 中 `domain_of_validity` 的 5 种条件类型为：

| 条件类型 | 语义 | 边界值 |
|----------|------|--------|
| `state_range` | 数值变量在范围内 | min、max、min-ε、max+ε |
| `state_enum` | 枚举变量取特定值 | 允许值、不允许值 |
| `sensor_status` | 传感器在线/离线 | online、offline、degraded |
| `composite` | 多条件 AND/OR 组合 | 每个子条件的边界 |
| `identity_confidence` | 身份置信度阈值 | 阈值、阈值±ε |

**生成规则**：
- 数据集 9 的 5,000 条多变量组合数据，由 Jelly 按 5 种条件类型的交叉组合自动生成
- 覆盖策略：每个条件类型的每种边界值至少出现一次，交叉组合覆盖至少 80% 的二元组合
- 不需要 Polymorphic-Twin 提供枚举清单

### Q6: 特定设备参数

**确认方案：以原始需求文档中的示例数据为准。**

| 参数 | 值 | 来源 |
|------|-----|------|
| 反应器容积 | 1000 L | product-demo |
| 材质 | SS316L | product-demo |
| 最大工作压力 | 50 atm | jelly-twin-provider-design 数据集 6 |
| 热容 | 4186 J/(kg·K) | product-demo |

公开标准数据（ASTM A36 钢 350°C 极限、IEC 61511 SIL 2 要求、Arrhenius 方程等）由 Jelly 负责采集和结构化，Polymorphic-Twin 不另行提供。

### Q7: 存储架构

**确认方案：接受 Jelly 提议的混合存储方案。**

Polymorphic-Twin 收回原始需求中"独立存储——不依赖 Jelly 的 PG/Redis/Typesense/Qdrant"的约束。理由充分：领域知识搜索（Group 4 工具）的语义查询能力必须依赖 Typesense + Qdrant，否则 `twin.query_domain_knowledge` 只能做精确匹配，无法实现自然语言混合查询。

**最终存储方案**：

| 数据类型 | 存储方式 | 说明 |
|----------|----------|------|
| DomainPack YAML | PostgreSQL | 结构化，版本管理，继承链查询 |
| 时序数据 | PostgreSQL (TimescaleDB 扩展) | 时间范围查询，统计聚合 |
| 验证数据集 | PostgreSQL | 结构化 JSON 查询 |
| 失效日志 | PostgreSQL | 结构化查询 + 时间筛选 |
| 领域知识条目 | Typesense + Qdrant | 混合搜索能力（关键词 + 语义 + RRF 融合） |
| 缓存 | Redis | DomainPack 热数据缓存 |

**约束**：Jelly 需保证 jelly_twin_provider 的存储层有独立的 schema/database，不与 Jelly 现有业务数据混存。具体隔离方式由 Jelly 团队决定。

### Q8: MCP 通信方式

**确认方案：HTTP 模式。**

Polymorphic-Twin 和 Jelly 部署在不同进程，未来可能跨机器。HTTP 模式是必要选择。

| 配置 | 值 |
|------|-----|
| 传输协议 | HTTP (SSE) |
| 默认端口 | Jelly 分配（建议 9091 或其他未占用端口） |
| MCP Client | Polymorphic-Twin 内置 |
| MCP Server | jelly_twin_provider |

原始需求文档中建议的 stdio 模式仅适用于同进程调试，此处修正为 HTTP。

### Q9: caller 认证方式

**确认方案：Phase 1 信任传入值，Phase 2 加 token 认证。**

| 阶段 | 认证方式 | 说明 |
|------|----------|------|
| Phase 1 | 信任 `caller` 字符串参数 | 快速对接，Polymorphic-Twin 保证传入正确的 caller 值 |
| Phase 2 | caller + token 双重认证 | Jelly 签发 token，Polymorphic-Twin 每次调用携带 |

Phase 2 的 token 机制细节在 Phase 1 交付后由双方协商设计。

### Q10: 精确过滤字段清单

**确认方案：Phase 1 基本过滤 + Phase 2 完整字段级过滤。**

#### Phase 1 过滤规则（按 caller 类型）

**`lab` caller 可见字段：**

| 工具 | 可返回 | 禁止返回 |
|------|--------|----------|
| `twin.get_domain_pack` | id, semantics, constraint summary (无 certifier/thresholds), rigidity rules, public_eval set, state_variables (name/unit/range/description) | certifier 逻辑, certifier.threshold, certifier.expression, fallback_strategy (完整细节), human_roles, audit_benchmark_reference, production_acceptance_reference |
| `twin.get_validation_set` | 仅 set_type="public_eval" | set_type="audit_benchmark" 和 "production_acceptance" 全部拒绝，返回 `permission_denied` |
| `twin.get_exploration_data` | LabExplorationView 投影后的数据（状态变量值、工况标签、时间戳） | 安全回落策略细节、完整判定逻辑和阈值 |
| `twin.get_failure_logs` | 脱敏条目（resolution 只含类别不含细节） | root_cause_category 中的内部诊断细节 |
| `twin.query_operational_history` | 全部（raw/stats） | — |
| `twin.query_domain_knowledge` | 全部 | — |
| `twin.get_physical_limits` | 全部 | — |
| `twin.get_equipment_spec` | 全部 | — |
| `twin.get_safety_standards` | 全部 | — |
| `twin.get_state_variable_schema` | 全部 | — |
| `twin.validate_data_alignment` | 全部 | — |

**`core` caller：** 全部数据，无过滤。

**`bridge` caller 可见字段：**

| 工具 | 可返回 | 禁止返回 |
|------|--------|----------|
| `twin.get_domain_pack` | id, constraint summary (仅 description + criticality + rigidity, 不含 certifier 逻辑), fallback (仅 name + steps, 不含 target_state 和 timeout), action_templates, human_roles (仅 name + permissions, 不含 audit 相关) | certifier 逻辑和阈值, hidden validation sets, 完整 fallback 策略细节 |
| `twin.get_validation_set` | 禁止访问，返回 `permission_denied` | 全部 |
| `twin.get_exploration_data` | 禁止访问，返回 `permission_denied` | 全部 |
| `twin.get_failure_logs` | 仅 severity + count 聚合，不含具体条目 | 具体失效条目 |
| `twin.query_domain_knowledge` | 全部 | — |
| `twin.get_physical_limits` | 全部 | — |
| `twin.get_equipment_spec` | 全部 | — |
| `twin.get_safety_standards` | 全部 | — |
| `twin.get_state_variable_schema` | 全部 | — |
| `twin.validate_data_alignment` | 全部 | — |

**`audit` caller：** 全部数据 + 变更历史，无过滤。

#### Phase 2 过滤增强

| 增强项 | 说明 |
|--------|------|
| 精确字段级过滤 | DomainPack 中每个嵌套字段按 caller 白名单返回 |
| 变更历史 | audit caller 额外获取 change_log (变更时间、操作者、变更 diff) |
| 敏感信息注入检测 | 自动检测并移除含 "hidden_challenge_set" 等敏感标记的数据 |

Phase 1 中，如果过滤规则不够精确导致数据泄露风险，Polymorphic-Twin 侧有兜底机制：Core 在加载数据时做二次校验，丢弃不在当前 caller 视图内的字段。

---

## 三、原始需求文档修正汇总

基于以上确认，原始需求文档 `2026-05-08-jelly-twin-provider-design.md` 需做以下修正：

| 位置 | 原文 | 修正为 |
|------|------|--------|
| §5.3 核心设计约束第 4 条 | "独立存储 — 不依赖 Jelly 的 PG/Redis/Typesense/Qdrant" | "存储隔离 — 复用 Jelly 基础设施（PG/Typesense/Qdrant/Redis），但使用独立 schema/database" |
| §5.1 项目信息 | "MCP Server（stdio）" | "MCP Server（HTTP/SSE）" |
| §2.1 `twin.list_domain_pack_versions` | status 枚举 4 值 | status 枚举 5 值：`draft` \| `review` \| `active` \| `deprecated` \| `archived` |
| §2.1 各工具 `domain_id` | 仅简短格式 | 同时接受简短格式和 `twin.{industry}.{scenario}` 格式 |

---

## 四、Phase 1 前置条件

Phase 1 开工前，双方需完成：

| # | 事项 | 负责方 | 截止时间 |
|---|------|--------|----------|
| 1 | domain_id 双向映射表（简短 ↔ 内部格式） | 双方对齐 | Phase 1 开始前 |
| 2 | 最小设备监控 DP 的 4 个 absolute 约束阈值 | PT 提供 | Phase 1 第 1 周 |
| 3 | CSTR 标准 DP 的 8 个约束完整定义 + 身份不变量值 | PT 提供 | Phase 1 第 1 周 |
| 4 | audit_benchmark 50 cases 边界规格 | PT 提供 | Phase 1 第 1 周 |
| 5 | production_acceptance 30 cases 极端工况规格 | PT 提供 | Phase 1 第 1 周 |
| 6 | domain_of_validity 5 种条件类型的精确边界值 | PT 提供 | Phase 1 第 1 周 |
| 7 | MCP HTTP 端口分配 | Jelly 提供 | Phase 1 开始前 |

**第 2-6 项的交付格式**：JSON，与原始需求文档中对应数据集的格式一致。PT 将以独立文件形式提供。

---

## 五、交付节奏确认

确认 Jelly 提出的 4 阶段交付计划，无调整。

| 阶段 | 时间 | 核心交付 | 验收标准 |
|------|------|----------|----------|
| Phase 1 | 第 1-2 周 | 数据集 1/2/5/10 + Group 1/2/5 共 9 个工具 | PT M0-M2 可对接 |
| Phase 2 | 第 3-4 周 | 数据集 3/4/7/8/11 + Group 3 共 3 个工具 + 视图过滤 | PT Lab 探索闭环可运行 |
| Phase 3 | 第 5-6 周 | 数据集 6/9/12/13 + Group 4 共 4 个工具 + 性能达标 | PT M6-M7 多场景验证通过 |
| Phase 4 | 第 7-8 周 | 错误处理 + 数据新鲜度 + CSTR 演示全流程 + 文档 + 容错 | PT M10-M11 演示就绪 |

---

## 六、双方承诺

### Polymorphic-Twin 承诺

1. **领域正确性由 PT 把关** — 所有约束阈值、物理参数、工况规格的合理性由 PT 验收
2. **接口稳定性** — 15 个 MCP 工具的输入输出格式按原始需求文档定义锁定，变更需双方确认
3. **Phase 1 前置条件按时交付** — 上述前置条件清单中的 PT 负责项在第 1 周内提供
4. **兜底机制** — PT 在 Core 中对 Jelly 返回数据做二次校验，过滤规则不够精确时 PT 侧兜底

### Jelly 承诺（确认 Jelly 回复中的 5 条）

1. 13 个数据集由 Jelly 生产，15 个 MCP 工具由 Jelly 提供
2. Phase 1 两周内交付 4 个数据集 + 9 个工具
3. 领域知识搜索（Group 4）是核心交付价值，复用 Jelly 搜索能力
4. 物理正确性由 Polymorphic-Twin 把关
5. 接口稳定性，变更需双方确认

---

## 七、契约生效

本文档经双方确认后生效，作为 `2026-05-08-jelly-twin-provider-design.md` 的正式补充和修正。

双方确认后，以本文档和原始需求文档为准开始 Phase 1 开发。

| 方 | 确认人 | 日期 |
|----|--------|------|
| Polymorphic-Twin 项目组 | （待签） | 2026-05-08 |
| Jelly 开发团队 | （待签） | — |

---

*文档结束*
