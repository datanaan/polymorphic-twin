# Jelly 团队对 Polymorphic-Twin 契约文档的正式确认

> **版本**: 1.0.0
> **日期**: 2026-05-08
> **文档性质**: 契约确认
> **确认对象**: `2026-05-08-jelly-twin-provider-contract.md`
> **确认方**: Jelly 开发团队

---

## 一、总体确认

Jelly 团队确认 Polymorphic-Twin 的契约文档。10 个问题全部有明确回复，原始需求修正合理，交付节奏无调整。

**契约生效条件已满足，Phase 1 可立即启动。**

---

## 二、10 个问题确认情况

| # | 问题 | PT 回复 | Jelly 确认 |
|---|------|---------|-----------|
| Q1 | domain_id 命名空间 | 双格式（简短 + `twin.{industry}.{scenario}`），MCP 层双向映射 | ✅ 接受。映射表在 Phase 1 开工前对齐 |
| Q2 | DomainPack 生命周期 | 5 状态：draft → review → active → deprecated → archived | ✅ 接受。`review` 状态对安全关键场景必要，Jelly 更新 `twin.list_domain_pack_versions` 的 status 枚举为 5 值 |
| Q3 | 验证集边界 case | PT 在 Phase 1 第 1 周内提供全部三种集合规格 | ✅ 接受。第 1 周内未收到的部分自动延至 Phase 2 |
| Q4 | 时序数据参数规格 | 以原始需求文档当前内容为准 | ✅ 确认 |
| Q5 | 压测边界组合 | Jelly 按 5 种条件类型交叉组合生成，PT 验收 | ✅ 确认。覆盖策略：每种边界值至少出现一次，80%+ 二元组合覆盖 |
| Q6 | 设备参数 | 以原始需求文档示例数据为准 | ✅ 确认 |
| Q7 | 存储架构 | 接受混合存储，收回"独立存储"约束，改为"存储隔离" | ✅ 接受。Jelly 保证 twin_provider 使用独立 schema，不与现有业务数据混存 |
| Q8 | MCP 通信方式 | HTTP/SSE 模式 | ✅ 确认。Jelly 分配端口（建议 9091），Phase 1 开工前通知 PT |
| Q9 | caller 认证 | Phase 1 信任传入值，Phase 2 加 token | ✅ 确认 |
| Q10 | 过滤字段清单 | Phase 1 基本过滤（按 caller 类型），Phase 2 字段级 | ✅ 接受。PT 侧兜底机制合理，Jelly 不反对 PT 做二次校验 |

---

## 三、原始需求文档修正确认

确认 PT 提出的 4 项修正：

| # | 位置 | 修正内容 | Jelly 意见 |
|---|------|---------|-----------|
| 1 | §5.3 核心设计约束第 4 条 | "独立存储" → "存储隔离——复用 Jelly 基础设施，但使用独立 schema/database" | ✅ 合理。这是正确的折中 |
| 2 | §5.1 项目信息 | "MCP Server（stdio）" → "MCP Server（HTTP/SSE）" | ✅ 正确。跨进程/跨机器必须 HTTP |
| 3 | §2.1 `twin.list_domain_pack_versions` | status 枚举 4 值 → 5 值 | ✅ 正确。`review` 状态不可省略 |
| 4 | §2.1 各工具 `domain_id` | 仅简短格式 → 同时接受两种格式 | ✅ 正确。向后兼容 |

---

## 四、Jelly 方 Phase 1 前置交付

Jelly 在 Phase 1 开始前完成：

| # | 事项 | 截止时间 |
|---|------|----------|
| 1 | MCP HTTP 端口分配并通知 PT | Phase 1 开始前 |
| 2 | domain_id 双向映射表初稿 | Phase 1 开始前 |
| 3 | `jelly_twin_provider` 项目骨架（目录结构、数据库 schema、MCP Server 框架） | Phase 1 第 1 周 |

---

## 五、双方承诺确认

确认 PT 契约文档中的双方承诺，Jelly 侧补充一条：

### Jelly 承诺（6 条）

1. **Jelly 是数据生产商和服务提供者** — 13 个数据集由 Jelly 生产，15 个 MCP 工具由 Jelly 提供
2. **Phase 1 两周内交付** — 4 个数据集 + Group 1/2/5 共 9 个工具
3. **领域知识搜索（Group 4）是核心交付价值** — 复用 Jelly 搜索能力，不是从零建设
4. **物理正确性由 PT 把关** — Jelly 按规格生产数据，PT 验收数据合理性
5. **接口稳定性** — 15 个 MCP 工具的输入输出格式按文档定义锁定，变更需双方确认
6. **存储隔离** — twin_provider 使用独立 schema/database，不与 Jelly 现有业务数据混存

### Polymorphic-Twin 承诺（4 条，引用自 PT 契约文档）

1. 领域正确性由 PT 把关
2. 接口稳定性，变更需双方确认
3. Phase 1 前置条件按时交付（第 1 周内提供）
4. 兜底机制 — PT Core 对 Jelly 返回数据做二次校验

---

## 六、契约签署

| 方 | 确认人 | 日期 |
|----|--------|------|
| Polymorphic-Twin 项目组 | （待签） | 2026-05-08 |
| Jelly 开发团队 | ✅ 已确认 | 2026-05-08 |

**契约生效。Phase 1 即刻启动。**

---

*文档结束*
