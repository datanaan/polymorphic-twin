# Polymorphic-Twin 软件框架文档

> **定位**: 从理论到落地的桥梁
> **目标**: 为开发团队提供足够详细的实施规范，理论文档 → 可编码实现
> **原则**: 不写代码，只写规范；不指定具体技术栈，只定义接口

---

## 文档结构

### 1. 架构层
- [系统架构总览](./architecture/01-system-overview.md) - 技术架构全景图
- [部署架构](./architecture/02-deployment-architecture.md) - 组件部署拓扑
- [数据流架构](./architecture/03-data-flow.md) - 系统内数据流向
- [安全架构](./architecture/04-security-architecture.md) - 安全防护体系

### 2. 接口层
- [Core 接口规范](./interfaces/01-core-api.md) - Core 组件接口定义
- [Lab 接口规范](./interfaces/02-lab-api.md) - Lab 组件接口定义
- [Bridge 接口规范](./interfaces/03-bridge-api.md) - Bridge 组件接口定义
- [TOM 接口规范](./interfaces/04-tom-api.md) - TOM 组件接口定义
- [生态接口规范](./interfaces/05-ecosystem-api.md) - 对外集成接口

### 3. 数据层
- [TOM 数据模型](./data/01-tom-data-model.md) - TwinObject 完整 Schema
- [DomainPack 格式规范](./data/02-domainpack-format.md) - DomainPack YAML/JSON 规范
- [约束卡片格式](./data/03-constraint-card-format.md) - 约束卡片标准格式
- [审计日志格式](./data/04-audit-log-format.md) - 审计日志标准格式
- [视图投影规范](./data/05-view-projection-spec.md) - 视图投影定义规范

### 4. 协议层
- [Lab-Core 通信协议](./protocols/01-lab-core-protocol.md) - Lab 与 Core 交互协议
- [Bridge-Core 通信协议](./protocols/02-bridge-core-protocol.md) - Bridge 与 Core 交互协议
- [TOM 访问协议](./protocols/03-tom-access-protocol.md) - TOM 访问控制协议
- [组件注册协议](./protocols/04-component-registration.md) - 组件注册与发现

### 5. 实施层
- [Core 实施规范](./implementation/01-core-implementation.md) - Core 实施细节
- [Lab 实施规范](./implementation/02-lab-implementation.md) - Lab 实施细节
- [Bridge 实施规范](./implementation/03-bridge-implementation.md) - Bridge 实施细节
- [TOM 实施规范](./implementation/04-tom-implementation.md) - TOM 实施细节

### 6. 运维层
- [监控指标定义](./operations/01-metrics.md) - 系统监控指标
- [日志规范](./operations/02-logging.md) - 日志格式与等级
- [配置管理](./operations/03-configuration.md) - 配置文件规范
- [故障恢复](./operations/04-failure-recovery.md) - 故障处理策略

### 7. 测试层
- [测试策略总览](./testing/01-test-strategy.md) - 整体测试策略
- [单元测试规范](./testing/02-unit-tests.md) - 单元测试要求
- [集成测试规范](./testing/03-integration-tests.md) - 集成测试场景
- [性能测试规范](./testing/04-performance-tests.md) - 性能基准

---

## 文档约定

### 符号说明

| 符号 | 含义 |
|------|------|
| `<>` | 变量占位符，需替换为实际值 |
| `[]` | 可选字段 |
| `|` | 枚举值分隔符 |
| `...` | 省略内容 |
| `→` | 数据流向或依赖关系 |

### 版本号规则

文档版本采用 `主版本.次版本.修订` 格式：
- 主版本：架构重大变更
- 次版本：新增功能或接口
- 修订：文档修正或优化

### 变更追踪

每份文档头部包含变更历史：

```markdown
## 变更历史

| 日期 | 版本 | 变更类型 | 变更内容 | 作者 |
|------|------|----------|----------|------|
| 2026-05-06 | 1.0.0 | 初始 | 文档创建 | - |
```

---

## 阅读路径

### 架构师 / Tech Lead
1. 系统架构总览
2. 部署架构
3. 数据流架构
4. 所有接口规范

### 后端开发工程师
1. 系统架构总览
2. 对应组件的接口规范
3. 对应组件的实施规范
4. 数据层文档

### 前端 / 集成工程师
1. 生态接口规范
2. 数据层文档（DomainPack 格式）
3. 协议层文档

### 测试工程师
1. 系统架构总览
2. 所有测试规范
3. 接口规范（用于 Mock）

### DevOps / SRE
1. 部署架构
2. 配置管理
3. 监控指标定义
4. 日志规范

---

## 文档状态

| 文档 | 状态 | 负责人 |
|------|------|--------|
| 系统架构总览 | 🟡 规划中 | - |
| 部署架构 | ⚪ 未开始 | - |
| 数据流架构 | ⚪ 未开始 | - |
| 安全架构 | ⚪ 未开始 | - |
| Core 接口规范 | 🟡 规划中 | - |
| Lab 接口规范 | ⚪ 未开始 | - |
| Bridge 接口规范 | ⚪ 未开始 | - |
| TOM 接口规范 | ⚪ 未开始 | - |
| 生态接口规范 | ⚪ 未开始 | - |

**图例**:
- 🟢 已完成
- 🟡 进行中
- ⚪ 未开始
- 🔴 阻塞

---

## 贡献指南

### 文档创建流程

1. 在对应目录创建 Markdown 文件
2. 使用标准模板（见各目录的 `TEMPLATE.md`）
3. 填充内容，确保覆盖所有必需章节
4. 更新本文档的文档状态表
5. 提交 PR 进行评审

### 文档评审要点

- [ ] 与理论框架文档一致性
- [ ] 技术可行性
- [ ] 完整性（无缺失的必要信息）
- [ ] 清晰性（易于理解和实施）
- [ ] 可测试性（定义可验证的规范）

---

## 联系方式

- 项目负责人: [待定]
- 架构评审: [待定]
- 文档问题反馈: [待定]

---

**最后更新**: 2026-05-06
**文档版本**: 1.0.0
