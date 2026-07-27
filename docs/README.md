# Polymorphic-Twin 文档导航

> 最后更新：2026-05-10

## 目录结构

```
Polymorphic-Twin/
├── CLAUDE.md                  ← Agent 指引
├── docs/
│   ├── README.md              ← 你在这里
│   ├── core/                  ← 核心架构与路线图
│   ├── component/             ← 组件设计文档
│   ├── framework/             ← 理论框架（8章+导读）
│   ├── about/                 ← 产品介绍与商业论述
│   ├── implementation/        ← 工程实现细节
│   ├── superpowers/           ← 开发规划（specs + plans）
│   └── archive/               ← 历史版本归档
└── jelly-llm-wiki/            ← LLM 知识库 Wiki
```

---

## 一、核心架构 (`core/`)

| 文档 | 说明 |
|------|------|
| [核心原理架构 v1.3](core/Polymorphic-Twin%20核心原理架构%20v1.3.md) | 架构全貌、核心原理、分层模型 |
| [理论核心框架文档](core/Polymorphic-Twin%20理论核心框架文档.md) | 理论基础、约束治理、可证伪性 |
| [开发里程碑与关键检查点](core/Polymorphic-Twin%20开发里程碑与关键检查点.md) | M0~M11 里程碑、验收标准、依赖关系 |
| [系统架构简要说明](core/Polymorphic-Twin%20系统架构简要说明.md) | 系统架构速览 |

## 二、组件设计 (`component/`)

| 文档 | 组件 | 版本 |
|------|------|------|
| [DomainPack](component/DomainPack%20v0.3.md) | 场景配置包 | v0.3 |
| [DomainPack 轻量化](component/DomainPack%20轻量化：从文档型知识库到可执行配置.md) | 从知识库到可执行配置的演进 | — |
| [Polymorphic-Lab](component/Polymorphic-Lab%20v0.4.md) | 隔离探索引擎 | v0.4 |
| [Polymorphic-Bridge](component/Polymorphic-Bridge%20v0.3.md) | 生态桥接层 | v0.3 |
| [TwinObjectModel](component/TwinObjectModel%20v0.3.md) | 统一孪生对象模型 | v0.3 |
| [生态接口规范](component/Polymorphic-Twin%20生态接口规范%20v1.1.md) | 外部接口标准 | v1.1 |

## 三、理论框架 (`framework/`)

8 章体系，从理论到实践的完整推导：

| 章节 | 文档 | 主题 |
|------|------|------|
| — | [README](framework/README.md) | 框架导读 |
| 01 | [理论总纲与架构总览](framework/01-理论总纲与架构总览.md) | 设计哲学、架构分层 |
| 02 | [核心原理与约束治理](framework/02-核心原理与约束治理.md) | 约束卡片、资格函数 Q |
| 03 | [统一孪生对象模型](framework/03-统一孪生对象模型.md) | TOM、视图投影、身份谱系 |
| 04 | [场景配置与 DomainPack](framework/04-场景配置与DomainPack.md) | DomainPack 格式与约束 |
| 05 | [探索引擎与决策接口](framework/05-探索引擎与决策接口.md) | Lab 探索、Bridge 决策 |
| 06 | [生态接口规范](framework/06-生态接口规范.md) | 外部集成协议 |
| 07 | [场景验证与价值论证](framework/07-场景验证与价值论证.md) | 六大应用场景 |
| 08 | [开发路线与知识产权保护](framework/08-开发路线与知识产权保护.md) | 路线图、知识产权策略 |
| — | [Lab Explain](framework/Polymorphic-Lab-隔离探索引擎-explain.md) | Lab 隔离探索引擎详解 |

## 四、产品与商业 (`about/`)

| 文档 | 说明 |
|------|------|
| [系统介绍](about/系统介绍.md) | 产品概述 |
| [商业价值与用户价值](about/Polymorphic-Twin%20商业价值与用户价值.md) | 双边价值分析 |
| [实际意义和价值讨论](about/实际意义和价值讨论.md) | 深度价值论述 |
| [分层保护](about/分层保护.md) | 安全与可信分层 |
| [场景演绎](about/场景演绎.md) | 场景推演与案例 |
| [专利](about/专利.md) | 专利相关文档 |
| [论文](about/论文.md) | 学术论文素材 |

## 五、工程实现 (`implementation/`)

| 目录 | 文档 | 说明 |
|------|------|------|
| — | [README](implementation/README.md) | 实现总览 |
| architecture/ | [System Overview](implementation/architecture/01-system-overview.md) | 系统架构实现 |
| data/ | [TOM Data Model](implementation/data/01-tom-data-model.md) | 数据模型实现 |
| data/ | [DomainPack Format](implementation/data/02-domainpack-format.md) | 配置包格式 |
| data/ | [Constraint Card Format](implementation/data/03-constraint-card-format.md) | 约束卡片格式 |
| interfaces/ | [Core API](implementation/interfaces/01-core-api.md) | 核心 API 实现 |

---

## 六、开发规划 (`superpowers/`)

### 设计规范 (`specs/`)

#### 核心设计

| 文档 | 说明 |
|------|------|
| [Python Monolith Design](specs/design/2026-05-06-python-monolith-design.md) | Python 单体架构设计 |

#### 产品设计

| 文档 | 说明 |
|------|------|
| [Product Overview SDK](specs/product/2026-05-07-product-overview-sdk.md) | SDK 产品总览 |
| [Product API Service](specs/product/2026-05-07-product-api-service.md) | API 服务设计 |
| [Product Demo](specs/product/2026-05-07-product-demo.md) | Demo 系统设计 |
| [Product Workbench](specs/product/2026-05-07-product-workbench.md) | Workbench 设计 |

#### Jelly 集成

| 文档 | 说明 |
|------|------|
| [MCP Client Integration](specs/jelly-integration/2026-05-08-jelly-mcp-client-integration.md) | Jelly MCP 客户端集成 |
| [Twin Provider Design](specs/jelly-integration/2026-05-08-jelly-twin-provider-design.md) | Twin Provider 架构设计 |
| [Twin Provider Contract](specs/jelly-integration/2026-05-08-jelly-twin-provider-contract.md) | Twin Provider 契约定义 |
| [Team Confirmation](specs/jelly-integration/2026-05-08-jelly-team-confirmation.md) | 团队确认记录 |
| [Team Reply](specs/jelly-integration/2026-05-08-jelly-team-reply.md) | 团队回复记录 |

### 开发计划 (`plans/`)

#### 基础阶段 (M0~M2)

| 里程碑 | 计划文档 | 说明 |
|--------|----------|------|
| M0 | [DomainPack Design](plans/foundation/plan-M0-domainpack-design.md) | 场景配置包设计 |
| M1 | [TOM Views](plans/foundation/plan-M1-tom-views.md) | 孪生对象视图层 |
| M2 | [Core Engine](plans/foundation/plan-M2-core-engine.md) | 核心引擎实现 |

#### 组件阶段 (M3~M6)

| 里程碑 | 计划文档 | 说明 |
|--------|----------|------|
| M3 | [Lab Engine](plans/components/plan-M3-lab-engine.md) | 探索引擎 |
| M4 | [Bridge](plans/components/plan-M4-bridge.md) | 桥接层 |
| M5 | [Integration](plans/components/plan-M5-integration.md) | 集成层 |
| M6 | [Multi-Scene](plans/components/plan-M6-multiscene.md) | 多场景支持 |

#### 生产阶段 (M7~M8)

| 里程碑 | 计划文档 | 说明 |
|--------|----------|------|
| M7 | [Production](plans/production/plan-M7-production.md) | 生产就绪 |
| M8 | [SDK Packaging](plans/production/plan-M8-sdk-packaging.md) | SDK 打包发布 |

#### Workbench 阶段 (M9~M11)

| 里程碑 | 计划文档 | 说明 |
|--------|----------|------|
| M9a | [Workbench CLI](plans/workbench/plan-M9a-workbench-cli.md) | 命令行工具 |
| M9b | [Workbench Simulate](plans/workbench/plan-M9b-workbench-simulate.md) | 模拟器 |
| M10a | [API Auth](plans/workbench/plan-M10a-api-auth.md) | API 认证 |
| M10b | [API Endpoints](plans/workbench/plan-M10b-api-endpoints.md) | API 端点 |
| M10c | [API Deploy](plans/workbench/plan-M10c-api-deploy.md) | API 部署 |
| M11a | [Demo Data](plans/workbench/plan-M11a-demo-data.md) | 演示数据 |
| M11b | [Demo Dashboard](plans/workbench/plan-M11b-demo-dashboard.md) | 演示仪表盘 |

### 报告

| 文档 | 说明 |
|------|------|
| [Current Status](report/now_status.md) | 当前开发状态 |

---

## 七、LLM 知识库 Wiki (`jelly-llm-wiki/`)

独立的 LLM 可读知识库，供 AI 代理快速理解项目。

| 目录 | 说明 |
|------|------|
| `wiki/index.md` | 知识库索引 |
| `wiki/entities/` | 33 个实体页（Core、Lab、Bridge、TOM、DomainPack 等） |
| `wiki/topics/` | 4 个主题页（架构全景、数据流、设计哲学、视图隔离） |
| `raw/` | 原始资料（空，待填充） |

---

## 八、归档 (`archive/`)

| 文档 | 说明 |
|------|------|
| [生态接口规范 v1.0](archive/Polymorphic-Twin%20生态接口规范%20v1.0.md) | 已被 v1.1 取代 |

---

## 九、文档统计

| 类别 | 数量 |
|------|------|
| 核心架构 | 4 |
| 组件设计 | 6 |
| 理论框架 | 10 |
| 产品与商业 | 7 |
| 工程实现 | 6 |
| 设计规范 (specs) | 10 |
| 开发计划 (plans) | 16 |
| 报告 | 1 |
| Wiki 实体 | 33 |
| Wiki 主题 | 4 |
| 归档 | 1 |
| **总计** | **98** |
