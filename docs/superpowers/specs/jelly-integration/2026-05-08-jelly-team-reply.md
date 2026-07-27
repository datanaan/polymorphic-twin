# Jelly 团队对 Polymorphic-Twin 对接需求的正式回复

> **版本**: 1.0.0
> **日期**: 2026-05-08
> **回复对象**: Polymorphic-Twin 项目组
> **评审文档**: `2026-05-08-jelly-twin-provider-design.md` (993 行)
> **回复方**: Jelly 开发团队
> **状态**: 待 Polymorphic-Twin 确认

---

## 一、前提确认

### 1.1 Jelly 的定位

Jelly 是**数据生产商和内容提供者**。这不是附加能力，是核心身份。

| 当前能力 | 说明 |
|----------|------|
| 文本数据生产 | 网页爬取 → 清洗 → 分块 → 向量化 → 导入 Typesense/Qdrant → 注册为知识库 |
| 知识库服务 | 搜索（关键词+向量混合，RRF 融合）、知识库注册/健康检查/路由 |
| 数据管道 | Creator Agent（41 个 MCP 工具），完整 5 步管道 |
| MCP 服务暴露 | 通过 `jelly_local_kb_mcp`(:9090) 提供 6 个搜索工具 |

### 1.2 Polymorphic-Twin 需求的本质

Polymorphic-Twin 的请求是：**Jelly 从文本内容数据生产者，扩展为科学数据生产和服务提供者。**

这包括两种新数据类型：
- **结构化科学数据**：时序数据、失效日志、验证基准集（Jelly 目前不生产）
- **领域知识数据**：物理极限、设备规格、安全标准（Jelly 已有能力，需结构化改造）

**Jelly 接受这个扩展方向。** 以下是对具体需求的逐项回复。

---

## 二、15 个 MCP 工具：逐项确认

### Group 1: DomainPack 服务（4 工具）— ✅ 接受

| 工具 | Jelly 能力评估 | 说明 |
|------|---------------|------|
| `twin.get_domain_pack` | ✅ 可做 | 按 ID 检索结构化数据，Jelly 已有类似能力（知识库按 ID 查询） |
| `twin.search_domain_packs` | ✅ 可做 | 关键词搜索，Jelly 核心能力 |
| `twin.list_domain_pack_versions` | ✅ 可做 | 版本管理，需新建版本表 |
| `twin.get_domain_pack_lineage` | ✅ 可做 | 继承链查询，需新建谱系表 |

**关键问题需确认**：

> **Q1**: DomainPack 的 `domain_id` 命名空间由谁管理？建议 Jelly 统一分配，格式 `twin.{industry}.{scenario}`（如 `twin.chemical.cstr_standard`），与 Jelly 现有知识库 ID 命名规范对齐。

> **Q2**: 一个 DomainPack 是一个不可变文件，还是可版本化更新的实体？文档说"支持版本管理和继承链查询"，Jelly 倾向于后者——DomainPack 是版本化实体，新版本创建时旧版本自动标记为 `deprecated`。

### Group 2: 验证数据集服务（2 工具）— ✅ 接受

| 工具 | Jelly 能力评估 | 说明 |
|------|---------------|------|
| `twin.get_validation_set` | ✅ 可做 | 结构化 JSON 查询 + caller 权限过滤 |
| `twin.query_validation_data` | ✅ 可做 | 条件筛选 + 分页 |

**关键问题需确认**：

> **Q3**: 三种验证集（public_eval / audit_benchmark / production_acceptance）的数据由谁生产？

这里需要明确：

- **public_eval**（100 cases）：给定 DomainPack 约束定义 + 状态变量范围，Jelly **可以程序化生成**——遍历 normal/boundary/emergency 工况，自动生成 input_state → expected_result 映射
- **audit_benchmark**（50 cases）：需要**领域专家**定义边界 case，Jelly 不具备判断"CSTR 反应器温度 283.5°C 时哪些约束应该 failed"的物理正确性
- **production_acceptance**（30 cases）：同理，需领域专家定义极端工况

**Jelly 的立场**：Jelly 负责生产 `public_eval`（因为规则明确，程序化可行），`audit_benchmark` 和 `production_acceptance` 需要双方协作——Polymorphic-Twin 提供阈值和边界条件，Jelly 负责格式化和存储。

### Group 3: 探索数据服务（3 工具）— ✅ 接受，需扩展数据生产能力

| 工具 | Jelly 能力评估 | 说明 |
|------|---------------|------|
| `twin.get_exploration_data` | ✅ 可做 | 查询 + LabExplorationView 过滤 |
| `twin.get_failure_logs` | ✅ 可做 | 时间范围 + 严重级别筛选 |
| `twin.query_operational_history` | ✅ 可做 | raw/stats 两种聚合模式 |

**这是 Jelly 数据生产能力的最大扩展点。**

Jelly 目前的数据生产是**文档型**（爬取网页 → 分块 → 向量化）。时序数据需要新的生产方式：

| 数据类型 | Jelly 能生产吗？ | 怎么生产？ |
|----------|-----------------|-----------|
| CSTR 六工况时序（600+条） | ✅ 可以 | 给定工况参数，程序化生成（高斯噪声、线性升温、偏移漂移等算法明确） |
| 风机轴承退化时序（600+条） | ✅ 可以 | 同上，给定退化曲线参数 |
| 知识管理使用日志（300条） | ✅ 可以 | 模拟用户行为序列 |
| 压测数据（15,000+条） | ✅ 可以 | 组合生成 + 边界填充 |
| 失效日志（50+条） | ✅ 可以 | 给定失效类型分布，程序化生成 |
| 边界异常数据（350+条） | ✅ 可以 | domain_of_validity 边界值 + 异常模式 |

**关键问题需确认**：

> **Q4**: 时序数据的物理真实性由谁保证？

文档中每种工况的生成参数都很明确（如"温度 175-185°C，高斯噪声 σ=2"），Jelly 可以按参数程序化生成。但"这些参数本身是否合理"是 Polymorphic-Twin 的领域。**建议：Polymorphic-Twin 提供每种工况的生成参数规格（类似文档中已有的格式），Jelly 按规格生产。**

> **Q5**: 数据集 9（压测 15,000+ 条）的"domain_of_validity 各种边界组合"具体有哪些？需要 Polymorphic-Twin 给出组合枚举或生成规则。

### Group 4: 领域知识查询（4 工具）— ✅ 核心匹配，直接复用 Jelly 现有能力

| 工具 | Jelly 能力评估 | 说明 |
|------|---------------|------|
| `twin.query_domain_knowledge` | ✅ 直接复用 | 即 Jelly 搜索（关键词+向量混合），已实现 |
| `twin.get_physical_limits` | ✅ 可做 | 结构化知识条目查询 |
| `twin.get_equipment_spec` | ✅ 可做 | 结构化知识条目查询 |
| `twin.get_safety_standards` | ✅ 可做 | 结构化知识条目查询 |

**这是 Jelly 与 Polymorphic-Twin 对接的核心价值点。** Jelly 已有混合搜索能力，只需：
1. 将领域知识导入为结构化知识库（Typesense 全文 + Qdrant 向量）
2. 在 MCP 工具层做 schema 感知的查询适配

**关键问题需确认**：

> **Q6**: 领域知识条目（数据集 6，30+ 条）的内容来源？

- 物理极限（如 ASTM A36 钢 350°C）：这是公开标准数据，Jelly 可以从标准文档中提取
- 设备规格（如 CSTR 容积 1000L、材质 SS316L）：需要 Polymorphic-Twin 指定设备型号和参数
- 安全标准（如 IEC 61511 SIL 2 要求）：公开法规数据，Jelly 可提取
- 领域知识（如 Arrhenius 方程）：公开化学动力学知识

**Jelly 的立场**：公开标准/法规/物理常数由 Jelly 负责采集和结构化；特定设备参数和场景特定知识由 Polymorphic-Twin 提供，Jelly 负责入库和索引。

### Group 5: 数据对齐与元数据（2 工具）— ✅ 接受

| 工具 | Jelly 能力评估 | 说明 |
|------|---------------|------|
| `twin.get_state_variable_schema` | ✅ 可做 | 读取 DomainPack 的变量定义 |
| `twin.validate_data_alignment` | ✅ 可做 | Schema 校验逻辑明确 |

---

## 三、架构决策：需双方确认

### 3.1 "独立存储" vs "复用 Jelly 基础设施"

文档原文要求：

> 独立存储 — 不依赖 Jelly 的 PG/Redis/Typesense/Qdrant

**Jelly 的意见：这个约束需要调整。**

理由：

| 数据类型 | 适合的存储 | 为什么 |
|----------|-----------|--------|
| DomainPack YAML | PostgreSQL | 结构化，需要版本管理、继承链查询 |
| 时序数据 | PostgreSQL (TimescaleDB 扩展) 或独立时序存储 | 需要时间范围查询、统计聚合 |
| 验证数据集 | PostgreSQL | 结构化 JSON 查询 |
| 领域知识条目 | **Typesense + Qdrant** | 这是 Jelly 搜索能力的核心依赖 |
| 失效日志 | PostgreSQL | 结构化查询 + 时间筛选 |

**领域知识条目必须用 Typesense + Qdrant**，否则 `twin.query_domain_knowledge` 的"自然语言混合查询"能力无从实现。这不是"依赖"，是"能力来源"。

**建议方案**：

```
jelly_twin_provider/
├── 存储层
│   ├── PostgreSQL       ← DomainPack、时序、验证集、失效日志（结构化数据）
│   ├── Typesense+Qdrant ← 领域知识条目（搜索型数据，复用 Jelly 现有 KB）
│   └── Redis            ← 缓存层（DomainPack 热数据缓存）
│
├── MCP Server
│   ├── 15 个 twin.* 工具
│   ├── caller 权限过滤
│   └── 数据对齐校验
│
└── 数据生产
    ├── 种子数据导入脚本
    ├── 时序数据生成器（按工况参数规格）
    ├── 验证集生成器（按约束定义）
    └── 领域知识爬取/提取器
```

> **Q7**: Polymorphic-Twin 是否接受"领域知识复用 Typesense+Qdrant，其余用 PostgreSQL"？这是实现 Group 4 搜索能力的必要条件。

### 3.2 MCP 协议传输方式

文档建议 `stdio`。Jelly 的 MCP Server 有两种运行方式：

| 方式 | 当前使用 | 适合场景 |
|------|---------|---------|
| stdio | `jelly_local_kb_mcp` | 本地进程间通信 |
| HTTP | TrendRadar (:3333) | 网络通信、多进程 |

> **Q8**: Polymorphic-Twin 的 MCP Client 调用是本地进程间通信还是跨网络？如果 Polymorphic-Twin 和 Jelly 部署在不同机器上，需要 HTTP 模式。

### 3.3 视图过滤（caller 权限）

文档要求 Jelly 侧执行 caller 过滤。Jelly 接受这个职责，但需明确语义：

| caller | 定义 | 过滤规则 |
|--------|------|---------|
| `lab` | Lab 探索引擎 | 只返回 public_eval + 脱敏数据 |
| `core` | Core 运行时核 | 全部数据 |
| `bridge` | Bridge 决策接口 | 约束摘要 + 行动模板，不含判定逻辑 |
| `audit` | 审计模块 | 全部 + 变更历史 |

> **Q9**: `caller` 参数如何认证？是信任 Polymorphic-Twin 传入的 caller 字符串，还是 Jelly 需要独立的 caller 认证机制？建议 Phase 1 信任传入值，Phase 2 加 token 认证。

> **Q10**: "隐藏验证集"和"安全回落策略细节"的精确过滤字段清单是什么？Jelly 需要知道精确的过滤规则，不能模糊地理解"不该看的就不返回"。

---

## 四、13 个数据集：交付计划

Jelly 按文档要求的优先级顺序交付，每个数据集包含：**数据生产 + 入库 + MCP 工具可查询**。

### Phase 1（第 1-2 周）：基础可用

| # | 数据集 | Jelly 负责生产？ | 需要 Polymorphic-Twin 提供什么？ |
|---|--------|-----------------|-------------------------------|
| 1 | 最小设备监控 DP | ✅ 是 | **约束阈值**（4 个 absolute 约束的具体值） |
| 2 | CSTR 标准 DP | ✅ 是 | **约束阈值**（8 个约束的完整定义）、**身份不变量值** |
| 5 | 验证基准集 | ✅ 部分 | public_eval Jelly 生成；audit_benchmark + production_acceptance 的**边界 case 规格由 Polymorphic-Twin 提供** |
| 10 | 边界异常数据 | ✅ 是 | **domain_of_validity 5 种条件类型的精确边界值** |

**Phase 1 前置条件**：Polymorphic-Twin 需在开始前提供上述"需要提供"列的内容。格式不限（YAML/JSON/Markdown），Jelly 负责转换。

### Phase 2（第 3-4 周）：探索支持

| # | 数据集 | Jelly 负责生产？ | 需要 Polymorphic-Twin 提供什么？ |
|---|--------|-----------------|-------------------------------|
| 3 | CSTR 时序 600+ 条 | ✅ 是 | **6 种工况的生成参数规格**（文档中已有，确认即可） |
| 4 | 失效日志 50+ 条 | ✅ 是 | **4 种失效类型的分布和严重级别映射** |
| 7 | 风机轴承完整场景 | ✅ 是 | **风机 DomainPack 的约束定义和阈值** |
| 8 | 知识管理场景 | ✅ 是 | **知识管理 DomainPack 的约束定义** |
| 11 | DP 继承测试 | ✅ 是 | **5 个关联 DP 的继承关系规格** |

### Phase 3（第 5-6 周）：知识与压测

| # | 数据集 | Jelly 负责生产？ | 需要 Polymorphic-Twin 提供什么？ |
|---|--------|-----------------|-------------------------------|
| 6 | 领域知识 30+ 条 | ✅ 部分 | 公开标准数据 Jelly 采集；**特定设备参数由 Polymorphic-Twin 提供** |
| 9 | 压测 15,000+ 条 | ✅ 是 | **组合生成规则**（domain_of_validity 边界组合枚举） |
| 12 | SDK Fixture | ✅ 是 | 无（基于已有数据集裁剪） |
| 13 | 多实例数据 | ✅ 是 | 无（3 用户 × 2 Twin 的配置规格文档中已有） |

### Phase 4（第 7-8 周）：生产加固

与原需求文档一致。错误处理完善、数据新鲜度校验、CSTR 演示全流程跑通、文档交付、容错验证。

---

## 五、需要 Polymorphic-Twin 回复的 10 个问题

以下是推进对接的必要确认项，请逐条回复：

| # | 问题 | 影响范围 | 默认方案（如不回复） |
|---|------|---------|-------------------|
| Q1 | DomainPack 的 `domain_id` 命名空间规范？ | Group 1 | Jelly 按 `twin.{industry}.{scenario}` 分配 |
| Q2 | DomainPack 是不可变文件还是版本化实体？ | Group 1 | 版本化实体，新版本自动 deprecate 旧版本 |
| Q3 | audit_benchmark 和 production_acceptance 的边界 case 规格 Polymorphic-Twin 何时提供？ | 数据集 5 | Phase 1 结束前提供，否则 Phase 1 只交付 public_eval |
| Q4 | 时序数据生成参数规格以文档当前内容为准，还是有调整？ | 数据集 3、7 | 以文档当前内容为准 |
| Q5 | 压测数据 domain_of_validity 边界组合的具体枚举？ | 数据集 9 | Jelly 自行按 5 种条件类型交叉组合生成 |
| Q6 | 特定设备参数（如 CSTR 容积、材质）Polymorphic-Twin 何时提供？ | 数据集 6 | 以文档中示例数据（1000L, SS316L）为准 |
| Q7 | 是否接受领域知识复用 Typesense+Qdrant？ | 架构 | 接受（否则 Group 4 只能做精确匹配，无法语义搜索） |
| Q8 | MCP 通信方式：stdio 还是 HTTP？ | 架构 | HTTP（Jelly 在独立进程/机器运行） |
| Q9 | caller 认证方式：信任传入值还是 token 认证？ | 安全 | Phase 1 信任传入值，Phase 2 加 token |
| Q10 | "隐藏验证集"和"安全回落策略细节"的精确过滤字段清单？ | Group 3 | Phase 1 不过滤，Phase 2 按字段清单过滤 |

---

## 六、Jelly 承诺

1. **Jelly 是数据生产商和服务提供者**——13 个数据集由 Jelly 生产，15 个 MCP 工具由 Jelly 提供
2. **Phase 1 两周内交付**——4 个数据集 + Group 1/2/5 共 9 个工具
3. **领域知识搜索（Group 4）是核心交付价值**——复用 Jelly 搜索能力，不是从零建设
4. **物理正确性由 Polymorphic-Twin 把关**——Jelly 按规格生产数据，Polymorphic-Twin 验收数据合理性
5. **接口稳定性**——15 个 MCP 工具的输入输出格式按文档定义锁定，变更需双方确认

---

## 附录：Jelly 现有基础设施与对接点

| Jelly 组件 | 端口 | 对接点 |
|-----------|------|--------|
| jelly_search_v3（后端 API） | 8000 | 知识库注册、搜索路由、配额管理 |
| jelly_local_kb_mcp（KB MCP Server） | 9090 | MCP 搜索工具暴露 |
| jelly_data_creation（Creator Agent） | 8090 | 数据生产管道（41 个 MCP 工具） |
| jelly_memory_service（Memory 服务） | 8091 | Agent 长期记忆 |
| Typesense | 8108 | 全文搜索索引 |
| Qdrant | 6333 | 向量搜索索引 |
| PostgreSQL | 5432 | 结构化数据存储 |
| Redis | 6380 | 缓存 + 分布式锁 |

**Jelly 数据生产架构**：

```
Creator Agent (41 MCP 工具)
    │
    ├─ 爬取 (WebCrawler: BFS, 限速, URL过滤, 缓存续爬)
    ├─ 清洗 (去标签/导航/广告, Markdown转换)
    ├─ 分块 (语义分块: 512 tokens, 50 overlap)
    ├─ 向量化 (Ollama bge-m3, 本地嵌入)
    ├─ 导入 (Typesense + Qdrant 双写)
    └─ 注册 (Jelly Search KB 元数据)
```

**扩展到科学数据生产后，新增**：

```
Science Data Producer (新增)
    │
    ├─ 时序数据生成器 (按工况参数规格程序化生成)
    ├─ 验证集生成器 (按约束定义生成 input_state → expected_result)
    ├─ 失效日志生成器 (按失效类型分布生成)
    ├─ 领域知识提取器 (从公开标准/法规中结构化提取)
    └─ DomainPack 存储 (版本管理 + 继承链)
```
