# TOM 数据模型规范

> **版本**: 1.0.0
> **状态**: 🟡 规划中
> **创建日期**: 2026-05-06
> **对应理论文档**: `03-统一孪生对象模型.md`
> **对应组件**: TOM v0.3

---

## 变更历史

| 日期 | 版本 | 变更类型 | 变更内容 | 作者 |
|------|------|----------|----------|------|
| 2026-05-06 | 1.0.0 | 初始 | 文档创建 | - |
| 2026-05-08 | 1.1.0 | 修订 | TwinObject 数据来源新增 Jelly MCP 可选路径（审计追踪记录 jelly_mcp_call 事件） | - |

---

## 1. 数据模型概览

### 1.1 TwinObject 核心结构

```
TwinObject
├── Identity (身份层)
│   ├── id: string (UUID v4)
│   ├── type: ObjectType
│   └── version: string (semver)
│
├── Lineage (谱系层)
│   ├── creator_id: string
│   ├── created_at: timestamp
│   ├── provenance: ProvenanceEntry[]
│   ├── parent_id: string (optional)
│   ├── fork_from: string (optional)
│   └── merge_from: string[] (optional)
│
├── Structure (结构层)
│   ├── schema_ref: string (URI)
│   ├── attributes: Map<string, any>
│   ├── content: ContentPayload
│   └── relationships: Relationship[]
│
├── State (状态层)
│   ├── lifecycle: LifecycleState
│   ├── health: HealthState
│   ├── last_modified: timestamp
│   └── access_stats: AccessStats
│
├── Constraints (约束层)
│   ├── attached: string[] (constraint_id)
│   ├── inherited: string[] (constraint_id)
│   └── overrides: Map<string, OverrideConfig>
│
├── Intent (意图层)
│   ├── current_goal: string (optional)
│   ├── pending_tasks: Task[]
│   └── preferences: Map<string, any>
│
└── Views (视图层)
    ├── default: string (view_id)
    ├── available: ViewDefinition[]
    └── active_view: string (view_id)
```

### 1.2 枚举定义

```typescript
// 对象类型
enum ObjectType {
  USER = "user",
  AGENT = "agent",
  TOOL = "tool",
  DOC = "doc",
  CODE = "code",
  KNOWLEDGE = "knowledge",
  DEVICE = "device",
  SCENE = "scene",
  DOMAIN_PACK = "domain_pack",
  CUSTOM = "custom"
}

// 生命周期状态
enum LifecycleState {
  CREATING = "creating",
  ACTIVE = "active",
  DEPRECATED = "deprecated",
  ARCHIVED = "archived",
  DELETED = "deleted"
}

// 健康状态
enum HealthState {
  HEALTHY = "healthy",
  DEGRADED = "degraded",
  FAILING = "failing",
  UNKNOWN = "unknown"
}
```

---

## 2. 完整 Schema 定义

### 2.1 Identity (身份层)

```typescript
interface Identity {
  // 全局唯一标识符
  id: string;  // UUID v4 格式: "550e8400-e29b-41d4-a716-446655440000"

  // 对象类型
  type: ObjectType;

  // Schema 版本
  version: string;  // semver: "0.3.0"

  // 可选：对象名称
  name?: string;

  // 可选：对象描述
  description?: string;

  // 可选：标签
  tags?: string[];
}
```

**约束**:
- `id`: 必须是有效的 UUID v4
- `version`: 必须遵循 semver 规范
- `type`: 必须是预定义的 ObjectType 或以 "custom:" 开头的自定义类型

### 2.2 Lineage (谱系层)

```typescript
interface Lineage {
  // 直接创建者
  creator_id: string;

  // 创建时间戳 (RFC 3339)
  created_at: string;  // "2026-05-06T12:00:00Z"

  // 来源链（从最近到最远）
  provenance: ProvenanceEntry[];

  // 父对象（结构继承）
  parent_id?: string;

  // 派生来源（内容复制）
  fork_from?: string;

  // 合并来源
  merge_from?: string[];

  // 修改历史
  modification_history?: ModificationEntry[];
}

interface ProvenanceEntry {
  source: string;           // 来源标识
  method: string;           // 创建方法
  timestamp: string;        // RFC 3339
  parent_of?: string;       // 指向上一条记录
  metadata?: Record<string, any>;
}

interface ModificationEntry {
  modified_at: string;      // RFC 3339
  modified_by: string;      // 修改者
  changes: Change[];
}

interface Change {
  field: string;            // 修改的字段
  old_value?: any;          // 旧值
  new_value?: any;          // 新值
  change_type: "add" | "update" | "delete";
}
```

**约束**:
- `provenance`: 最多保留 100 条记录
- `modification_history`: 最多保留 50 条记录

### 2.3 Structure (结构层)

```typescript
interface Structure {
  // 结构定义引用
  schema_ref: string;       // URI: "https://schema.polymorphic-twin.io/v1/code"

  // 属性字典
  attributes: Record<string, any>;

  // 内容载荷（类型特定）
  content: ContentPayload;

  // 关系列表
  relationships: Relationship[];
}

interface ContentPayload {
  // 通用字段
  format?: string;
  raw_data?: any;

  // 类型特定内容（根据 type 动态选择）
  user?: UserContent;
  agent?: AgentContent;
  doc?: DocumentContent;
  code?: CodeContent;
  knowledge?: KnowledgeContent;
  device?: DeviceContent;
  custom?: Record<string, any>;
}

// 用户内容
interface UserContent {
  profile: {
    name: string;
    email?: string;
    avatar?: string;
  };
  credentials?: Record<string, any>;  // 加密存储
  settings?: Record<string, any>;
}

// AI 代理内容
interface AgentContent {
  model_config: {
    provider: string;
    model: string;
    parameters: Record<string, any>;
  };
  capability_set: string[];
  memory_snapshot?: {
    db_id: string;
    snapshot_id: string;
  };
  execution_log?: ExecutionLogEntry[];
}

interface ExecutionLogEntry {
  timestamp: string;
  action: string;
  result: "success" | "failure" | "partial";
  details?: Record<string, any>;
}

// 文档内容
interface DocumentContent {
  format: string;           // "markdown", "html", "pdf", "plain"
  body: string;
  metadata: {
    title: string;
    tags?: string[];
    category?: string;
    author?: string;
  };
  embeddings?: {
    model: string;
    vector: number[];
  };
}

// 代码内容
interface CodeContent {
  language: string;         // "python", "javascript", "go", etc.
  source: string;
  ast_ref?: string;         // AST 表示引用
  dependencies: Dependency[];
  test_refs: string[];      // 关联测试对象 ID
  metrics?: CodeMetrics;
}

interface Dependency {
  name: string;
  version?: string;
  source: string;           // "pypi", "npm", "go_modules", etc.
}

interface CodeMetrics {
  lines_of_code: number;
  cyclomatic_complexity: number;
  test_coverage?: number;
}

// 知识节点内容
interface KnowledgeContent {
  concept: string;
  definition: string;
  relations: KnowledgeRelation[];
  evidence: EvidenceReference[];
  confidence: number;       // [0, 1]
}

interface KnowledgeRelation {
  target_concept: string;   // 概念名称或对象 ID
  relation_type: "is_a" | "part_of" | "related_to" | "causes" | "precedes";
  strength: number;         // [0, 1]
}

interface EvidenceReference {
  source: string;
  type: "document" | "observation" | "experiment" | "derivation";
  confidence: number;
  timestamp: string;
}

// 设备内容
interface DeviceContent {
  device_type: string;
  model: string;
  manufacturer?: string;
  serial_number?: string;
  capabilities: string[];
  state: Record<string, any>;
  connection_info?: {
    protocol: string;
    endpoint: string;
    credentials?: Record<string, any>;
  };
}

// 关系定义
interface Relationship {
  target_id: string;        // 目标对象 ID
  type: RelationshipType;
  strength: number;         // [0, 1]
  bidirectional: boolean;
  metadata?: Record<string, any>;
}

enum RelationshipType {
  OWNS = "owns",
  CREATED = "created",
  DEPENDS_ON = "depends_on",
  REFERENCES = "references",
  PART_OF = "part_of",
  VERSION_OF = "version_of",
  CONTRADICTS = "contradicts",
  SUPPORTS = "supports",
  SIMILAR_TO = "similar_to",
  TRIGGERS = "triggers",
  CONTAINS = "contains",
  CONNECTED_TO = "connected_to",
  CUSTOM = "custom"
}
```

**约束**:
- `relationships`: 最多 1000 个关系
- `strength`: 必须在 [0, 1] 范围内
- `codeContent.dependencies`: 最多 500 个依赖

### 2.4 State (状态层)

```typescript
interface State {
  // 生命周期状态
  lifecycle: LifecycleState;

  // 健康状态
  health: HealthState;

  // 最后修改时间
  last_modified: string;     // RFC 3339

  // 访问统计
  access_stats: AccessStats;

  // 锁定状态
  lock?: LockState;
}

interface AccessStats {
  read_count: number;        // 读取次数
  write_count: number;       // 写入次数
  last_access: string;       // RFC 3339
  last_access_by: string;    // 访问者 ID
  access_history?: AccessHistoryEntry[];
}

interface AccessHistoryEntry {
  timestamp: string;
  actor: string;
  action: "read" | "write" | "delete" | "execute";
  result: "success" | "failure";
}

interface LockState {
  locked_by: string;         // 锁定者
  locked_at: string;         // RFC 3339
  expires_at: string;        // RFC 3339
  lock_type: "exclusive" | "shared";
}
```

**约束**:
- `access_history`: 最多保留 100 条记录

### 2.5 Constraints (约束层)

```typescript
interface Constraints {
  // 附加的约束卡片 ID 列表
  attached: string[];

  // 继承的约束卡片 ID 列表
  inherited: string[];

  // 约束覆盖设置
  overrides: Record<string, OverrideConfig>;

  // 当前激活的约束
  active_constraints: string[];
}

interface OverrideConfig {
  constraint_id: string;
  parameter_overrides: Record<string, any>;
  level_override?: "hard" | "critical" | "soft" | "info";
  reason?: string;
  override_time: string;     // RFC 3339
  override_by: string;
  expires_at?: string;       // RFC 3339
}
```

### 2.6 Intent (意图层)

```typescript
interface Intent {
  // 当前目标
  current_goal?: string;

  // 待处理任务
  pending_tasks: Task[];

  // 偏好设置
  preferences: Record<string, any>;

  // 目标历史
  goal_history?: GoalHistoryEntry[];
}

interface Task {
  task_id: string;
  description: string;
  priority: number;         // [0, 100]
  status: "pending" | "in_progress" | "completed" | "failed";
  created_at: string;
  deadline?: string;
  dependencies: string[];   // 依赖的其他 task_id
  metadata?: Record<string, any>;
}

interface GoalHistoryEntry {
  goal: string;
  started_at: string;
  completed_at?: string;
  status: "completed" | "abandoned" | "failed";
  result_summary?: string;
}
```

### 2.7 Views (视图层)

```typescript
interface Views {
  // 默认视图 ID
  default: string;

  // 可用视图列表
  available: ViewDefinition[];

  // 当前激活视图
  active_view: string;
}

interface ViewDefinition {
  id: string;
  name: string;
  scope: string;             // 所属场景 ID

  // 投影配置
  projection: Projection;

  // 变换配置
  transform: Transform;

  // 权限配置
  permissions: ViewPermissions;
}

interface Projection {
  // 包含的属性名列表（空表示全部）
  include_attributes: string[];

  // 排除的属性名列表
  exclude_attributes: string[];

  // 包含的关系类型
  include_relations: RelationshipType[];

  // 关系遍历最大深度
  max_depth: number;
}

interface Transform {
  // 输出格式
  format: OutputFormat;

  // 脱敏字段
  redact: string[];

  // 本地化
  localize: string;          // "zh-CN", "en-US", etc.

  // 自定义转换
  custom_transforms?: Record<string, TransformFunction>;
}

enum OutputFormat {
  JSON = "json",
  YAML = "yaml",
  XML = "xml",
  PROTOBUF = "protobuf",
  CUSTOM = "custom"
}

interface TransformFunction {
  type: string;
  config: Record<string, any>;
}

interface ViewPermissions {
  readable_by: string[];     // 角色 ID 列表
  writable_by: string[];
  executable_by: string[];
}
```

---

## 3. 完整 TwinObject 示例

### 3.1 代码对象示例

```json
{
  "identity": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "type": "code",
    "version": "0.3.0",
    "name": "user-service-auth",
    "description": "用户认证服务代码模块",
    "tags": ["auth", "security", "python"]
  },
  "lineage": {
    "creator_id": "user-123",
    "created_at": "2026-05-06T12:00:00Z",
    "provenance": [
      {
        "source": "user-123",
        "method": "manual_create",
        "timestamp": "2026-05-06T12:00:00Z"
      },
      {
        "source": "agent-456",
        "method": "ai_assist",
        "timestamp": "2026-05-06T12:00:01Z",
        "parent_of": "0"
      }
    ]
  },
  "structure": {
    "schema_ref": "https://schema.polymorphic-twin.io/v1/code",
    "attributes": {
      "module": "auth",
      "package": "com.example.services",
      "language": "python"
    },
    "content": {
      "code": {
        "language": "python",
        "source": "def authenticate_user(username, password):\n    # Implementation\n    pass",
        "dependencies": [
          {
            "name": "pyjwt",
            "version": "2.8.0",
            "source": "pypi"
          },
          {
            "name": "bcrypt",
            "version": "4.1.2",
            "source": "pypi"
          }
        ],
        "test_refs": ["test-001", "test-002"],
        "metrics": {
          "lines_of_code": 150,
          "cyclomatic_complexity": 5,
          "test_coverage": 0.95
        }
      }
    },
    "relationships": [
      {
        "target_id": "dep-pyjwt",
        "type": "depends_on",
        "strength": 1.0,
        "bidirectional": false
      },
      {
        "target_id": "test-001",
        "type": "references",
        "strength": 0.8,
        "bidirectional": false
      }
    ]
  },
  "state": {
    "lifecycle": "active",
    "health": "healthy",
    "last_modified": "2026-05-06T14:30:00Z",
    "access_stats": {
      "read_count": 42,
      "write_count": 5,
      "last_access": "2026-05-06T14:30:00Z",
      "last_access_by": "user-123"
    }
  },
  "constraints": {
    "attached": ["sec-001", "qual-002", "perf-003"],
    "inherited": ["qual-001"],
    "active_constraints": ["sec-001", "qual-001", "qual-002", "perf-003"]
  },
  "intent": {
    "current_goal": "通过安全审计",
    "pending_tasks": [
      {
        "task_id": "task-001",
        "description": "完成单元测试",
        "priority": 80,
        "status": "completed",
        "created_at": "2026-05-06T10:00:00Z"
      },
      {
        "task_id": "task-002",
        "description": "通过安全扫描",
        "priority": 100,
        "status": "in_progress",
        "created_at": "2026-05-06T11:00:00Z"
      }
    ]
  },
  "views": {
    "default": "dev-view",
    "available": [
      {
        "id": "dev-view",
        "name": "开发者视图",
        "scope": "scene-development",
        "projection": {
          "include_attributes": ["content.code.source", "content.code.language", "content.code.dependencies"],
          "include_relations": ["depends_on", "references"],
          "max_depth": 3
        },
        "transform": {
          "format": "json",
          "redact": [],
          "localize": "zh-CN"
        },
        "permissions": {
          "readable_by": ["developer", "admin"],
          "writable_by": ["developer", "admin"],
          "executable_by": []
        }
      }
    ],
    "active_view": "dev-view"
  }
}
```

---

## 4. 数据库 Schema

### 4.1 PostgreSQL 表结构

```sql
-- TwinObject 主表
CREATE TABLE twin_objects (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '0.3.0',
    name VARCHAR(255),
    description TEXT,
    tags TEXT[],

    -- 谱系信息
    creator_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    parent_id UUID,
    fork_from UUID,

    -- 结构
    schema_ref TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}',
    content JSONB NOT NULL,

    -- 状态
    lifecycle VARCHAR(20) NOT NULL DEFAULT 'creating',
    health VARCHAR(20) NOT NULL DEFAULT 'unknown',
    last_modified TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- 意图
    current_goal TEXT,
    pending_tasks JSONB NOT NULL DEFAULT '[]',
    preferences JSONB NOT NULL DEFAULT '{}',

    -- 视图
    default_view VARCHAR(100),
    active_view VARCHAR(100),

    -- 元数据
    metadata JSONB NOT NULL DEFAULT '{}',

    -- 索引
    created_at_idx TIMESTAMP WITH TIME ZONE GENERATED ALWAYS AS (created_at) STORED,

    CONSTRAINT valid_type CHECK (type IN ('user', 'agent', 'tool', 'doc', 'code', 'knowledge', 'device', 'scene', 'domain_pack') OR type LIKE 'custom:%'),
    CONSTRAINT valid_lifecycle CHECK (lifecycle IN ('creating', 'active', 'deprecated', 'archived', 'deleted')),
    CONSTRAINT valid_health CHECK (health IN ('healthy', 'degraded', 'failing', 'unknown'))
);

-- 索引
CREATE INDEX idx_twin_objects_type ON twin_objects(type);
CREATE INDEX idx_twin_objects_lifecycle ON twin_objects(lifecycle);
CREATE INDEX idx_twin_objects_creator ON twin_objects(creator_id);
CREATE INDEX idx_twin_objects_parent ON twin_objects(parent_id);
CREATE INDEX idx_twin_objects_tags ON twin_objects USING GIN(tags);
CREATE INDEX idx_twin_objects_attributes ON twin_objects USING GIN(attributes);
CREATE INDEX idx_twin_objects_content ON twin_objects USING GIN(content);

-- 来源链表
CREATE TABLE provenance_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id UUID NOT NULL REFERENCES twin_objects(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    method VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    parent_of UUID REFERENCES provenance_entries(id),
    metadata JSONB DEFAULT '{}',

    position INTEGER NOT NULL,
    CONSTRAINT valid_position CHECK (position >= 0)
);

CREATE INDEX idx_provenance_object ON provenance_entries(object_id, position);

-- 关系表
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES twin_objects(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES twin_objects(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    strength DECIMAL(3,2) NOT NULL CHECK (strength BETWEEN 0 AND 1),
    bidirectional BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT no_self_relationship CHECK (source_id != target_id),
    CONSTRAINT unique_relationship UNIQUE (source_id, target_id, type)
);

CREATE INDEX idx_relationships_source ON relationships(source_id);
CREATE INDEX idx_relationships_target ON relationships(target_id);
CREATE INDEX idx_relationships_type ON relationships(type);

-- 约束关联表
CREATE TABLE object_constraints (
    object_id UUID NOT NULL REFERENCES twin_objects(id) ON DELETE CASCADE,
    constraint_id VARCHAR(100) NOT NULL,
    constraint_type VARCHAR(20) NOT NULL CHECK (constraint_type IN ('attached', 'inherited')),
    override_config JSONB,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    attached_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    PRIMARY KEY (object_id, constraint_id, constraint_type)
);

CREATE INDEX idx_constraints_object ON object_constraints(object_id);
CREATE INDEX idx_constraints_active ON object_constraints(active) WHERE active = TRUE;

-- 访问历史表
CREATE TABLE access_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id UUID NOT NULL REFERENCES twin_objects(id) ON DELETE CASCADE,
    actor VARCHAR(255) NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('read', 'write', 'delete', 'execute')),
    result VARCHAR(20) NOT NULL CHECK (result IN ('success', 'failure')),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_access_history_object ON access_history(object_id);
CREATE INDEX idx_access_history_timestamp ON access_history(timestamp DESC);

-- 视图定义表
CREATE TABLE view_definitions (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    scope VARCHAR(100) NOT NULL,
    projection JSONB NOT NULL,
    transform JSONB NOT NULL,
    permissions JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);

-- 对象视图映射表
CREATE TABLE object_views (
    object_id UUID NOT NULL REFERENCES twin_objects(id) ON DELETE CASCADE,
    view_id VARCHAR(100) NOT NULL REFERENCES view_definitions(id),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (object_id, view_id)
);

CREATE INDEX idx_object_views_object ON object_views(object_id);
CREATE INDEX idx_object_views_active ON object_views(is_active) WHERE is_active = TRUE;
```

---

## 5. API 响应格式

### 5.1 创建对象响应

```typescript
interface CreateObjectResponse {
  object_id: string;
  version: string;
  created_at: string;
  status: "success" | "partial" | "failed";
  warnings?: string[];
}
```

### 5.2 获取对象响应

```typescript
interface GetObjectResponse {
  object: TwinObject;
  view_applied?: string;
  permissions: ObjectPermissions;
  metadata: ResponseMetadata;
}

interface ObjectPermissions {
  can_read: boolean;
  can_write: boolean;
  can_delete: boolean;
  can_execute: boolean;
  can_delegate: boolean;
}

interface ResponseMetadata {
  retrieved_at: string;
  version: string;
  etag: string;
}
```

### 5.3 更新对象响应

```typescript
interface UpdateObjectResponse {
  object_id: string;
  version: string;
  updated_fields: string[];
  old_version: string;
  new_version: string;
}
```

### 5.4 删除对象响应

```typescript
interface DeleteObjectResponse {
  object_id: string;
  deleted: boolean;
  deleted_at: string;
  affected_count: number;  // 级联删除的对象数量
}
```

---

## 6. 验证规则

### 6.1 对象创建验证

| 字段 | 验证规则 | 错误码 |
|------|---------|--------|
| `id` | 必须是有效 UUID v4 | `INVALID_ID` |
| `type` | 必须是预定义类型或 custom: | `INVALID_TYPE` |
| `version` | 必须遵循 semver | `INVALID_VERSION` |
| `creator_id` | 必须存在 | `CREATOR_NOT_FOUND` |
| `parent_id` | 必须存在且处于 active 状态 | `PARENT_INVALID` |
| `fork_from` | 必须存在 | `SOURCE_NOT_FOUND` |

### 6.2 对象更新验证

| 操作 | 验证规则 |
|------|---------|
| 修改状态 | 必须遵循状态转换规则 |
| 删除 | 必须 active/archived 状态，无引用 |
| 修改内容 | 必须通过 schema 验证 |
| 修改视图 | 视图必须存在且用户有权限 |

---

## 7. 性能考虑

### 7.1 查询优化

- **按 ID 查询**: 使用主键索引，O(1)
- **按类型查询**: 使用 `idx_twin_objects_type` 索引
- **按标签查询**: 使用 GIN 索引
- **关系查询**: 使用 `idx_relationships_source` 和 `idx_relationships_target`
- **全文搜索**: 使用 PostgreSQL 全文搜索或外部搜索引擎

### 7.2 缓存策略

| 数据类型 | 缓存位置 | TTL |
|---------|---------|-----|
| 热点对象 | Redis | 5分钟 |
| 视图投影 | Redis | 10分钟 |
| 关系图谱 | Redis | 30分钟 |
| Schema 定义 | 内存缓存 | 1小时 |

---

## 8. 待定事项

| ID | 事项 | 优先级 |
|----|------|--------|
| T001 | 是否支持对象版本历史 | P1 |
| T002 | 大文件内容存储策略 | P0 |
| T003 | 分布式对象存储方案 | P2 |
| T004 | 对象迁移和备份策略 | P1 |

---

## 9. 参考文献

- 理论文档: `docs/framework/03-统一孪生对象模型.md`
- 系统架构: `docs/implementation/architecture/01-system-overview.md`

---

**文档维护者**: [待定]
**审核人**: [待定]
**最后审核日期**: [待定]
