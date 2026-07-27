# 04-场景配置与 DomainPack

> **定位**: 场景层配置系统  
> **组件**: DP (DomainPack)  
> **版本**: v0.3 + 轻量化扩展  
> **整合来源**: `DomainPack v0.3.md` + `DomainPack 轻量化：从文档型知识库到可执行配置.md`

---

## 1. 设计目标

DomainPack 解决的核心问题：**如何让同一套底层系统（Core/Lab/Bridge/TOM）在不同场景下表现出完全不同的行为模式？**

场景示例：
- 编程助手场景 vs 科研分析场景 vs 创意写作场景
- 三者需要的工具集、约束规则、视图模板、工作流完全不同
- 但底层组件（Core/Lab/Bridge/TOM）是同一套

DP 的设计目标：
1. **场景封装**: 将场景的所有配置封装为独立单元
2. **可继承复用**: 新场景可以继承现有场景，只做差异化修改
3. **运行时切换**: 系统可以在不同场景间动态切换
4. **版本管理**: 场景配置可以版本化，支持回滚
5. **可验证性**: 场景配置本身可以被验证（语法正确、约束一致）

---

## 2. DomainPack 结构

### 2.1 核心结构

```yaml
DomainPack:
  # === 元数据 ===
  id: "dp_unique_id"
  name: "场景名称"
  version: "1.0.0"
  description: "场景描述"
  
  # === 继承 ===
  extends:                # 父场景列表（多重继承）
    - "base_programming"
    - "security_strict"
  
  # === 场景边界 ===
  scope:
    domains: ["编程", "软件开发"]
    exclude_domains: ["硬件设计"]
    context_window: "session"   # session | task | persistent
  
  # === 角色定义 ===
  roles:
    - id: "developer"
      name: "开发者"
      permissions: ["read", "write", "execute"]
      default_view: "dev_view"
    - id: "reviewer"
      name: "代码审查者"
      permissions: ["read", "comment"]
      default_view: "review_view"
    - id: "system"
      name: "系统代理"
      permissions: ["read", "write", "execute", "admin"]
      default_view: "system_view"
  
  # === 约束集 ===
  constraints:
    inherit: true           # 是否继承父场景的约束
    override:               # 覆盖父场景的约束
      - constraint_id: "perf_001"
        new_threshold: 50   # 将性能阈值从 100ms 改为 50ms
    append:                 # 新增约束
      - id: "custom_001"
        name: "必须使用类型注解"
        level: "soft"
        validation:
          method: "ast_check"
          rule: "all_functions_have_type_hints"
  
  # === 工具集 ===
  tools:
    registry: "tool_registry_uri"
    allowed:                # 允许使用的工具白名单
      - "code_executor"
      - "linter"
      - "test_runner"
      - "git_client"
    forbidden:              # 明确禁止的工具
      - "file_deleter"
    configurations:         # 工具特定配置
      code_executor:
        timeout: 30
        sandbox: "docker"
      linter:
        ruleset: "pep8_strict"
  
  # === 视图模板 ===
  views:
    - id: "dev_view"
      name: "开发者视图"
      projection:
        include: ["code.source", "code.ast", "test.results"]
      format: "ide_panel"
    - id: "review_view"
      name: "审查视图"
      projection:
        include: ["code.diff", "quality.metrics", "security.scan"]
      format: "report"
  
  # === 工作流模板 ===
  workflows:
    - id: "code_review_flow"
      name: "代码审查工作流"
      steps:
        - action: "lint"
          tool: "linter"
          on_fail: "abort"
        - action: "test"
          tool: "test_runner"
          on_fail: "report"
        - action: "security_scan"
          tool: "security_scanner"
          on_fail: "block"
        - action: "human_review"
          role: "reviewer"
          on_timeout: "auto_approve"
  
  # === 知识库映射 ===
  knowledge:
    sources:
      - type: "vector_db"
        uri: "qdrant://localhost:6333/collections/code_knowledge"
      - type: "graph_db"
        uri: "neo4j://localhost:7687/code_graph"
    embedding_model: "bge-m3"
    retrieval_strategy: "hybrid"   # keyword | vector | hybrid
  
  # === 生命周期 ===
  lifecycle:
    status: "active"        # draft | active | deprecated | archived
    created_at: "2026-01-01"
    updated_at: "2026-01-15"
    deprecated_by: null
```

### 2.2 轻量化结构

对于简单场景，DP 支持轻量化配置（单文件 YAML）：

```yaml
# lightweight_dp.yaml
id: "quick_python"
extends: ["base_python"]

roles:
  developer:
    permissions: ["read", "write", "execute"]

tools:
  allowed: ["python_executor", "pytest"]
  configurations:
    python_executor:
      timeout: 10

constraints:
  append:
    - id: "no_exec"
      level: "hard"
      validation:
        method: "pattern_match"
        pattern: "exec\("
        inverse: true
```

轻量化的核心原则：**只写差异，不写默认**。未指定的字段从父场景或系统默认继承。

---

## 3. 刚性-关键性规则 (Hard-Critical Rules)

### 3.1 规则定义

DomainPack 中的约束遵循 Core 的 L0-L3 层级，但在场景层有特殊语义：

| 层级 | 场景语义 | 违反后果 |
|------|----------|----------|
| **Hard** | 场景准入门槛 | 对象/行为无法进入该场景 |
| **Critical** | 场景运行红线 | 触发强制回落或场景切换 |
| **Soft** | 场景质量期望 | 记录偏离，用于场景评分 |
| **Info** | 场景统计参考 | 仅用于分析和优化 |

### 3.2 场景准入 (Hard)

Hard 约束在场景层充当"门卫"——不满足的对象无法进入该场景：

```yaml
# 示例：安全编程场景的准入约束
constraints:
  - id: "admission_security"
    level: "hard"
    scope: "scene.admission"
    validation:
      method: "check_origin"
      rules:
        - "代码必须来自可信来源"
        - "无已知的 CVE 漏洞"
```

### 3.3 运行红线 (Critical)

Critical 约束在场景运行中充当"保险丝"：

```yaml
# 示例：性能红线
constraints:
  - id: "runtime_perf"
    level: "critical"
    scope: "scene.runtime"
    validation:
      method: "benchmark"
      threshold: 1000        # 1秒
      unit: "ms"
    fallback:
      strategy: "scene_switch"
      target_scene: "optimized_mode"  # 切换到优化模式场景
```

---

## 4. 继承机制

### 4.1 继承链

DomainPack 支持多重继承，形成继承链：

```
[base_system]        # 最基础场景，定义通用角色和默认约束
    │
    ├── [base_programming]   # 编程场景基类
    │       │
    │       ├── [python_dev]      # Python 开发
    │       │       │
    │       │       └── [django_project]   # Django 项目特定
    │       │
    │       └── [web_frontend]    # 前端开发
    │
    ├── [base_research]      # 科研场景基类
    │       │
    │       └── [bioinformatics]  # 生物信息学
    │
    └── [base_creative]      # 创意场景基类
            │
            └── [novel_writing]   # 小说写作
```

### 4.2 继承解析规则

当子场景继承多个父场景时，按以下规则解析冲突：

1. **字段覆盖**: 子场景显式定义的字段覆盖父场景
2. **约束合并**: 约束列表按 ID 合并，同 ID 以子场景为准
3. **工具集交集**: 若父场景 A 允许工具 {T1, T2}，父场景 B 允许 {T2, T3}，则子场景默认允许 {T2}（取交集，确保安全）
4. **权限最小化**: 角色权限取所有父场景中的最小集合
5. **视图追加**: 视图列表合并，同 ID 以子场景为准

### 4.3 继承示例

```yaml
# 父场景: base_python
id: "base_python"
roles:
  developer:
    permissions: ["read", "write", "execute"]
tools:
  allowed: ["python_executor", "pytest", "mypy"]
constraints:
  - id: "type_hint"
    level: "soft"

# 子场景: secure_python
id: "secure_python"
extends: ["base_python"]
# 角色继承 developer，权限不变
# 工具集继承，但追加配置
tools:
  configurations:
    python_executor:
      sandbox: "strict"    # 更严格的沙箱
# 约束升级
constraints:
  override:
    - constraint_id: "type_hint"
      new_level: "critical"   # 从 soft 升级为 critical
  append:
    - id: "no_eval"
      level: "hard"
      validation:
        method: "pattern_match"
        pattern: "eval\("
        inverse: true
```

---

## 5. 生命周期管理

### 5.1 状态机

```
         ┌──────────┐
         │  draft   │
         └────┬─────┘
              │ validate()
              ▼
         ┌──────────┐
    ┌───►│ active   │◄────┐
    │    └────┬─────┘     │
    │         │            │
    │         ▼            │
    │    ┌──────────┐      │
    │    │deprecated│      │
    │    └────┬─────┘      │
    │         │            │
    │         ▼            │
    │    ┌──────────┐      │
    └────┤ archived ├──────┘
         └──────────┘
```

### 5.2 状态说明

| 状态 | 说明 | 可执行操作 |
|------|------|------------|
| **draft** | 草稿状态，正在编辑 | 编辑、验证、发布 |
| **active** | 激活状态，可被使用 | 使用、更新、弃用 |
| **deprecated** | 已弃用，建议使用新版本 | 查看、回滚到 active |
| **archived** | 已归档，历史保留 | 查看、恢复 |

### 5.3 版本管理

DomainPack 支持语义化版本管理：

```yaml
version: "1.2.3"
# 主版本.次版本.修订号
# - 主版本：不兼容的 API 变更
# - 次版本：向下兼容的功能新增
# - 修订号：向下兼容的问题修复
```

版本切换策略：
- **自动升级**: 允许自动使用最新的修订号版本
- **手动升级**: 次版本和主版本需要显式确认
- **回滚**: 支持回滚到任意历史版本

---

## 6. 场景切换机制

### 6.1 切换触发条件

场景切换可能由以下事件触发：

1. **用户显式切换**: 用户主动选择新场景
2. **任务类型识别**: 系统根据输入内容自动识别场景
3. **约束触发**: 当前场景的 Critical 约束被违反，触发场景切换
4. **工作流步骤**: 工作流模板中定义了场景切换步骤
5. **对象类型匹配**: 新进入系统的对象类型与当前场景不匹配

### 6.2 切换流程

```
触发场景切换
    ↓
1. 保存当前场景状态（对象视图、进行中的任务）
    ↓
2. 加载目标场景配置
    ↓
3. 验证当前对象是否满足目标场景的 Hard 约束
   └─ 不满足 → 拒绝切换或触发对象转换
    ↓
4. 重新计算所有相关对象的视图投影
    ↓
5. 通知所有订阅者场景变更
    ↓
6. 恢复被挂起的任务（如果兼容）
```

### 6.3 切换代价

场景切换有一定代价，系统应尽量减少不必要的切换：

- **视图重计算**: 所有可见对象需要重新投影
- **工具热加载**: 新场景的工具集可能需要初始化
- **知识库重连**: 知识库连接可能需要切换
- **上下文丢失**: 部分场景特定的上下文可能无法保留

---

## 7. 知识库映射

### 7.1 映射架构

DomainPack 不直接存储知识，而是定义与知识库的映射关系：

```
DomainPack
    │
    ├── 知识源配置
    │       ├── 向量数据库 (Qdrant/Pinecone)
    │       ├── 图数据库 (Neo4j)
    │       └── 文档存储 (MongoDB/S3)
    │
    ├── 检索策略
    │       ├── 关键词检索
    │       ├── 向量相似度
    │       └── 混合检索 (RRF)
    │
    └── 嵌入模型配置
            ├── 模型名称
            ├── 维度
            └── 预处理管道
```

### 7.2 场景专属知识

不同场景可以映射到不同的知识库集合：

| 场景 | 知识源 | 检索策略 |
|------|--------|----------|
| Python 开发 | Python 官方文档、PyPI 包信息、Stack Overflow 精选 | 混合检索 |
| 生物信息学 | NCBI、UniProt、KEGG | 关键词为主 |
| 小说写作 | 文学作品库、写作技巧文档 | 向量相似度 |

### 7.3 知识库轻量化

对于小型场景，支持嵌入式知识库（无需外部服务）：

```yaml
knowledge:
  sources:
    - type: "embedded"
      format: "jsonl"
      path: "./knowledge_base.jsonl"
      embedding_model: "local_bge_small"
```

---

## 8. 与相邻组件的交互

### 8.1 DP ↔ TOM

- DP 定义场景中对象的 schema 和默认视图
- TOM 根据当前激活的 DP 调整对象的呈现方式
- 场景切换时，TOM 重新计算所有相关对象的视图投影

### 8.2 DP ↔ Core

- DP 中的约束集被转换为 Core 的约束卡片
- Core 的场景准入验证使用 DP 的 Hard 约束
- Core 的运行时验证使用 DP 的 Critical 约束

### 8.3 DP ↔ Lab

- Lab 的探索空间受 DP 的 scope 限制
- Lab 可用的知识源由 DP 的 knowledge 配置决定
- Lab 生成的假设需要满足 DP 的场景边界

### 8.4 DP ↔ Bridge

- Bridge 的行动空间由 DP 的 tools 配置定义
- Bridge 的工作流模板来自 DP 的 workflows
- Bridge 的角色权限基于 DP 的 roles 定义

---

## 9. 附录

### 9.1 预定义场景模板

系统预定义以下基础场景模板：

| 模板 ID | 名称 | 说明 |
|---------|------|------|
| `base_system` | 系统基础 | 最基础的默认场景 |
| `base_programming` | 编程基础 | 通用编程场景 |
| `base_research` | 科研基础 | 通用科研分析场景 |
| `base_creative` | 创意基础 | 通用创意写作场景 |
| `base_data` | 数据基础 | 通用数据分析场景 |

### 9.2 版本演进

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v0.1 | — | 基础场景配置结构 |
| v0.2 | — | 引入继承机制和生命周期管理 |
| v0.3 | — | 增加知识库映射、轻量化配置、工作流模板 |
