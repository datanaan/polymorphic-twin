# Core 接口规范

> **版本**: 1.0.0
> **状态**: 🟡 规划中
> **创建日期**: 2026-05-06
> **对应理论文档**: `02-核心原理与约束治理.md`
> **对应组件**: Core v1.3

---

## 变更历史

| 日期 | 版本 | 变更类型 | 变更内容 | 作者 |
|------|------|----------|----------|------|
| 2026-05-06 | 1.0.0 | 初始 | 文档创建 | - |
| 2026-05-08 | 1.1.0 | 修订 | 新增 Jelly 验证集集成接口（load_validation_sets 从 Jelly MCP 获取） | - |

---

## 1. 接口概览

### 1.1 接口列表

| 接口 | 方法 | 用途 | 认证要求 |
|------|------|------|----------|
| `/v1/core/qualify` | POST | 资格验证 | mTLS |
| `/v1/core/constraints` | GET/POST/PUT/DELETE | 约束管理 | mTLS + RBAC |
| `/v1/core/fallback` | POST | 触发安全回落 | mTLS + RBAC |
| `/v1/core/permission` | POST | 权限计算 | mTLS |
| `/v1/core/evidence` | POST/GET | 证据管理 | mTLS |
| `/v1/core/audit` | GET | 审计查询 | mTLS + RBAC |
| `/v1/core/health` | GET | 健康检查 | - |

### 1.2 通信协议

- **协议**: gRPC (推荐) / REST (备选)
- **序列化**: Protocol Buffers / JSON
- **传输安全**: mTLS (双向 TLS)
- **超时设置**:
  - 资格验证: 100ms
  - 约束管理: 1s
  - 权限计算: 50ms
  - 审计查询: 500ms

---

## 2. 资格验证接口

### 2.1 `/v1/core/qualify`

**用途**: 判定对象或行为是否满足约束条件

**请求**:

```protobuf
message QualifyRequest {
  string request_id = 1;           // 请求 ID (UUID)
  string object_id = 2;            // TwinObject ID
  string action_id = 3;            // 行为 ID (可选)
  string context_id = 4;           // 场景 ID
  repeated ConstraintCheck constraints = 5;  // 要验证的约束列表
  QualificationMode mode = 6;      // 验证模式
  map<string, string> metadata = 7; // 元数据
}

message ConstraintCheck {
  string constraint_id = 1;
  string version = 2;              // 约束版本
  map<string, string> parameters = 3; // 约束参数
}

enum QualificationMode {
  MODE_UNSPECIFIED = 0;
  MODE_STRICT = 1;                 // 严格模式（所有约束必须满足）
  MODE_PERMISSIVE = 2;             // 宽松模式（允许部分约束不满足）
  MODE_AUDIT_ONLY = 3;             // 仅审计（不阻止执行）
}
```

**响应**:

```protobuf
message QualifyResponse {
  string request_id = 1;
  QualificationResult result = 2;
  repeated ConstraintEvaluation evaluations = 3;
  string explanation = 4;          // 自然语言解释
  FallbackRecommendation fallback = 5; // 回落建议
}

message QualificationResult {
  QualificationStatus status = 1;
  double score = 2;                // 综合得分 [0, 1]
  string decision_reason = 3;      // 决策原因
}

enum QualificationStatus {
  STATUS_UNSPECIFIED = 0;
  STATUS_APPROVED = 1;             // 完全通过
  STATUS_CONDITIONAL = 2;          // 有条件通过
  STATUS_REJECTED = 3;             // 拒绝
  STATUS_PENDING = 4;              // 需要更多信息
}

message ConstraintEvaluation {
  string constraint_id = 1;
  QualificationStatus status = 2;
  double score = 3;                // 该约束的得分 [0, 1]
  repeated CheckResult checks = 4; // 详细检查结果
  string message = 5;              // 评估消息
}

message CheckResult {
  string check_name = 1;
  bool passed = 2;
  string detail = 3;               // 详细信息
  string error = 4;                // 错误信息（如有）
}

message FallbackRecommendation {
  bool fallback_recommended = 1;
  repeated FallbackOption options = 2;
  string reason = 3;
}

message FallbackOption {
  string strategy = 1;             // 回落策略
  string description = 2;
  map<string, string> parameters = 3;
  double estimated_impact = 4;     // 估计影响 [0, 1]
}
```

**错误码**:

| Code | 含义 | HTTP Status |
|------|------|-------------|
| `INVALID_ARGUMENT` | 请求参数无效 | 400 |
| `OBJECT_NOT_FOUND` | 对象不存在 | 404 |
| `CONSTRAINT_NOT_FOUND` | 约束不存在 | 404 |
| `CONTEXT_NOT_ACTIVE` | 场景未激活 | 409 |
| `INTERNAL_ERROR` | 内部错误 | 500 |
| `TIMEOUT` | 验证超时 | 504 |

### 2.2 使用示例

**请求**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "object_id": "obj-123",
  "action_id": "action-delete",
  "context_id": "ctx-prod",
  "constraints": [
    {
      "constraint_id": "constraint-001",
      "version": "1.0"
    }
  ],
  "mode": "MODE_STRICT"
}
```

**响应**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "result": {
    "status": "STATUS_CONDITIONAL",
    "score": 0.75,
    "decision_reason": "部分约束未满足，建议采用回落策略"
  },
  "evaluations": [
    {
      "constraint_id": "constraint-001",
      "status": "STATUS_REJECTED",
      "score": 0.5,
      "checks": [
        {
          "check_name": "安全边界检查",
          "passed": false,
          "detail": "超出安全阈值 10%"
        }
      ]
    }
  ],
  "explanation": "对象 obj-123 在执行 action-delete 时违反了安全边界约束，当前值为 110%，阈值为 100%。",
  "fallback": {
    "fallback_recommended": true,
    "options": [
      {
        "strategy": "DEGRADED_EXECUTION",
        "description": "降级执行，只删除部分数据",
        "estimated_impact": 0.3
      }
    ],
    "reason": "主路径违反安全约束"
  }
}
```

---

## 3. 约束管理接口

### 3.1 创建约束 - `/v1/core/constraints`

**请求**:

```protobuf
message CreateConstraintRequest {
  ConstraintCard constraint = 1;
  bool dry_run = 2;                // 试运行，不实际创建
}

message ConstraintCard {
  string id = 1;
  string name = 2;
  string version = 3;
  ConstraintLevel level = 4;
  string scope = 5;                 // 适用范围（对象路径模式）
  TriggerConfig trigger = 6;
  ValidationConfig validation = 7;
  FallbackConfig fallback = 8;
  ConstraintMetadata metadata = 9;
}

enum ConstraintLevel {
  LEVEL_UNSPECIFIED = 0;
  LEVEL_HARD = 1;                  // 刚性约束
  LEVEL_CRITICAL = 2;              // 关键约束
  LEVEL_SOFT = 3;                  // 建议约束
  LEVEL_INFO = 4;                  // 参考约束
}

message TriggerConfig {
  TriggerType type = 1;
  string target = 2;               // 触发目标
  map<string, string> conditions = 3;
}

enum TriggerType {
  TRIGGER_ON_PRODUCE = 0;          // 产生时
  TRIGGER_ON_TRANSFORM = 1;        // 转换时
  TRIGGER_ON_ACCESS = 2;           // 访问时
  TRIGGER_SCHEDULED = 3;           // 定时
}

message ValidationConfig {
  string method = 1;               // 验证方法
  string tool = 2;                 // 验证工具
  map<string, string> config = 3;  // 验证配置
}

message FallbackConfig {
  string strategy = 1;
  repeated string alternatives = 2;
}

message ConstraintMetadata {
  string owner = 1;
  string created_at = 2;
  map<string, string> labels = 3;
}
```

**响应**:

```protobuf
message CreateConstraintResponse {
  ConstraintCard constraint = 1;
  bool created = 2;
  repeated ValidationWarning warnings = 3;
}

message ValidationWarning {
  string code = 1;
  string message = 2;
  string suggestion = 3;
}
```

### 3.2 获取约束 - `/v1/core/constraints/{constraint_id}`

**请求**:
```protobuf
message GetConstraintRequest {
  string constraint_id = 1;
  string version = 2;              // 可选，默认最新版本
  string view = 3;                 // 视图 (full | summary)
}
```

**响应**:
```protobuf
message GetConstraintResponse {
  ConstraintCard constraint = 1;
  ConstraintStats stats = 2;
}

message ConstraintStats {
  int64 total_evaluations = 1;
  int64 pass_count = 2;
  int64 fail_count = 3;
  double pass_rate = 4;
  timestamp last_evaluation = 5;
}
```

### 3.3 更新约束 - `/v1/core/constraints/{constraint_id}`

**请求**:
```protobuf
message UpdateConstraintRequest {
  string constraint_id = 1;
  string version = 2;              // 基于哪个版本更新
  ConstraintUpdate update = 3;
  string reason = 4;               // 更新原因
}

message ConstraintUpdate {
  optional string name = 1;
  optional ValidationConfig validation = 2;
  optional FallbackConfig fallback = 3;
  map<string, string> metadata_updates = 4;
}
```

**响应**:
```protobuf
message UpdateConstraintResponse {
  ConstraintCard constraint = 1;
  bool updated = 2;
  string new_version = 3;
}
```

### 3.4 删除约束 - `/v1/core/constraints/{constraint_id}`

**请求**:
```protobuf
message DeleteConstraintRequest {
  string constraint_id = 1;
  bool force = 2;                  // 强制删除（即使有引用）
}
```

**响应**:
```protobuf
message DeleteConstraintResponse {
  bool deleted = 1;
  repeated string dependents = 2;   // 依赖此约束的对象
}
```

---

## 4. 安全回落接口

### 4.1 触发回落 - `/v1/core/fallback`

**请求**:

```protobuf
message TriggerFallbackRequest {
  string request_id = 1;
  string object_id = 2;
  string trigger_reason = 3;
  FallbackTrigger trigger = 4;
  map<string, string> context = 5;
}

message FallbackTrigger {
  TriggerType type = 1;            // MANUAL | AUTOMATIC | EMERGENCY
  string source = 2;               // 触发源
  string triggered_by = 3;         // 触发者
  repeated string constraint_violations = 4;
}

enum TriggerType {
  TRIGGER_MANUAL = 0;              // 人工触发
  TRIGGER_AUTOMATIC = 1;           // 自动触发
  TRIGGER_EMERGENCY = 2;           // 紧急触发
}
```

**响应**:

```protobuf
message TriggerFallbackResponse {
  string fallback_id = 1;
  FallbackExecution execution = 2;
  FallbackStatus status = 3;
}

message FallbackExecution {
  string strategy = 1;
  string target_state = 2;
  repeated ActionStep steps = 3;
  timestamp estimated_completion = 4;
}

message ActionStep {
  string step_id = 1;
  string action = 2;
  map<string, string> parameters = 3;
  repeated string depends_on = 4;
}

enum FallbackStatus {
  STATUS_INITIATED = 0;
  STATUS_IN_PROGRESS = 1;
  STATUS_COMPLETED = 2;
  STATUS_FAILED = 3;
  STATUS_ABORTED = 4;
}
```

### 4.2 查询回落状态 - `/v1/core/fallback/{fallback_id}`

**请求**:
```protobuf
message GetFallbackStatusRequest {
  string fallback_id = 1;
}

message GetFallbackStatusResponse {
  FallbackStatus status = 1;
  FallbackExecution execution = 2;
  repeated StepResult step_results = 3;
  string error_message = 4;
}

message StepResult {
  string step_id = 1;
  StepStatus status = 2;
  string output = 3;
  string error = 4;
  timestamp started_at = 5;
  timestamp completed_at = 6;
}

enum StepStatus {
  STEP_PENDING = 0;
  STEP_RUNNING = 1;
  STEP_COMPLETED = 2;
  STEP_FAILED = 3;
  STEP_SKIPPED = 4;
}
```

---

## 5. 权限计算接口

### 5.1 `/v1/core/permission`

**用途**: 计算对象间的动态权限

**请求**:

```protobuf
message PermissionRequest {
  string subject_id = 1;           // 主体 ID
  string object_id = 2;            // 客体 ID
  string action = 3;               // 动作 (read | write | execute | delete | delegate)
  string context_id = 4;           // 场景 ID
  map<string, string> environment = 5; // 环境变量
}

message PermissionResponse {
  bool granted = 1;
  double confidence = 2;           // 置信度 [0, 1]
  string reason = 3;
  PermissionDetail detail = 4;
}

message PermissionDetail {
  repeated PermissionRule matched_rules = 1;
  TrustFactors trust = 2;
  EmergencyOverride emergency = 3;
}

message PermissionRule {
  string rule_id = 1;
  string source = 2;               // 规则来源
  string effect = 3;               // allow | deny
  string reason = 4;
}

message TrustFactors {
  double base_trust = 1;           // 基础信任度 [0, 1]
  double history_factor = 2;       // 历史因子 [0, 1]
  double lineage_factor = 3;       // 谱系因子 [0, 1]
  double scene_factor = 4;         // 场景因子 [0, 1]
}

message EmergencyOverride {
  bool active = 1;
  string emergency_level = 2;
  string reason = 3;
  timestamp expires_at = 4;
}
```

---

## 6. 证据管理接口

### 6.1 提交证据 - `/v1/core/evidence`

**请求**:

```protobuf
message SubmitEvidenceRequest {
  string evidence_id = 1;
  EvidenceType type = 2;
  string source = 3;               // 来源 (Lab | External | Manual)
  bytes payload = 4;               // 证据载荷
  map<string, string> metadata = 5;
}

enum EvidenceType {
  TYPE_UNSPECIFIED = 0;
  TYPE_CONSTRAINT_HYPOTHESIS = 1;  // 约束假设
  TYPE_MODEL_CANDIDATE = 2;        // 模型候选
  TYPE_NEGATIVE_RESULT = 3;        // 负面结果
  TYPE_UNCERTAINTY_EVIDENCE = 4;   // 不确定性证据
}
```

**响应**:

```protobuf
message SubmitEvidenceResponse {
  string evidence_id = 1;
  EvidenceStatus status = 2;
  string quarantine_id = 3;        // 隔离区 ID
  timestamp review_deadline = 4;
}

enum EvidenceStatus {
  STATUS_SUBMITTED = 0;
  STATUS_IN_QUARANTINE = 1;        // 隔离中
  STATUS_UNDER_REVIEW = 2;         // 审核中
  STATUS_ACCEPTED = 3;             // 已接受
  STATUS_REJECTED = 4;             // 已拒绝
}
```

### 6.2 查询证据 - `/v1/core/evidence/{evidence_id}`

**请求**:
```protobuf
message GetEvidenceRequest {
  string evidence_id = 1;
  bool include_payload = 2;        // 是否包含载荷
}

message GetEvidenceResponse {
  Evidence evidence = 1;
  EvidenceReview review = 2;
}

message Evidence {
  string evidence_id = 1;
  EvidenceType type = 2;
  string source = 3;
  bytes payload = 4;
  EvidenceStatus status = 5;
  map<string, string> metadata = 6;
  timestamp submitted_at = 7;
}

message EvidenceReview {
  string reviewer = 1;
  string decision = 2;             // accept | reject | pending
  string comment = 3;
  timestamp reviewed_at = 4;
}
```

---

## 7. 审计查询接口

### 7.1 `/v1/core/audit`

**请求**:

```protobuf
message AuditQueryRequest {
  AuditFilter filter = 1;
  Pagination pagination = 2;
  SortOrder sort = 3;
}

message AuditFilter {
  repeated string object_ids = 1;
  repeated string constraint_ids = 2;
  timestamp start_time = 3;
  timestamp end_time = 4;
  repeated QualificationStatus statuses = 5;
  repeated string user_ids = 6;
}

message Pagination {
  int32 page = 1;
  int32 page_size = 2;
}

message SortOrder {
  string field = 1;                // 排序字段
  bool descending = 2;
}
```

**响应**:

```protobuf
message AuditQueryResponse {
  repeated AuditEntry entries = 1;
  int64 total_count = 2;
  int32 page = 3;
  int32 page_size = 4;
}

message AuditEntry {
  string entry_id = 1;
  timestamp timestamp = 2;
  string event_type = 3;           // qualification | constraint_violation | fallback
  string object_id = 4;
  string actor = 5;
  map<string, string> details = 6;
  string request_id = 7;
}
```

---

## 8. 健康检查接口

### 8.1 `/v1/core/health`

**响应**:

```protobuf
message HealthResponse {
  HealthStatus status = 1;
  ComponentHealth components = 2;
  map<string, string> metadata = 3;
}

enum HealthStatus {
  HEALTH_UNKNOWN = 0;
  HEALTH_SERVING = 1;
  HEALTH_NOT_SERVING = 2;
}

message ComponentHealth {
  HealthStatus database = 1;
  HealthStatus cache = 2;
  HealthStatus message_queue = 3;
  HealthStatus audit_log = 4;
}
```

---

## 9. 事件流

### 9.1 Core 发布的事件

| 事件名称 | 触发条件 | 消费者 |
|---------|---------|--------|
| `constraint.qualified` | 资格验证完成 | Bridge, Audit |
| `constraint.violated` | 约束违反 | Bridge, Alerting |
| `fallback.triggered` | 安全回落触发 | Bridge, Alerting, Audit |
| `evidence.submitted` | 证据提交 | Lab, Audit |
| `evidence.accepted` | 证据接受 | Lab, TOM |
| `evidence.rejected` | 证据拒绝 | Lab |

### 9.2 事件格式

```protobuf
message CoreEvent {
  string event_id = 1;
  string event_type = 2;
  timestamp timestamp = 3;
  string source = 4;               // core_instance_id
  bytes payload = 5;
  map<string, string> headers = 6;
}
```

---

## 10. 性能指标

### 10.1 暴露的指标

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `core_qualify_duration_seconds` | Histogram | 资格验证耗时 |
| `core_qualify_total` | Counter | 资格验证总数 |
| `core_qualify_result` | Gauge | 当前结果分布 |
| `core_constraint_evaluations_total` | Counter | 约束评估总数 |
| `core_fallbacks_total` | Counter | 回落触发总数 |
| `core_evidence_queue_size` | Gauge | 证据队列大小 |
| `core_active_connections` | Gauge | 当前活跃连接 |

### 10.2 SLO

| 指标 | 目标 |
|------|------|
| 资格验证 P99 延迟 | < 10ms |
| 权限计算 P99 延迟 | < 50ms |
| 可用性 | > 99.9% |
| 错误率 | < 0.1% |

---

## 11. 安全要求

### 11.1 认证

- **内部调用**: mTLS (双向 TLS)
- **API 密钥**: 用于服务间轻量认证（开发环境）

### 11.2 授权

| 角色 | 可访问接口 |
|------|-----------|
| `core-admin` | 所有接口 |
| `core-operator` | 读取、资格验证、权限计算 |
| `core-auditor` | 审计查询、健康检查 |
| `bridge-service` | 资格验证、权限计算、回落 |
| `lab-service` | 证据提交、证据查询 |

### 11.3 加密

- 传输加密: TLS 1.3
- 存储加密: 透明数据加密 (TDE)

---

## 12. 限制

| 限制项 | 值 |
|-------|-----|
| 单次资格验证约束数 | 100 |
| 约束版本历史保留 | 10 |
| 审计日志保留期 | 90 天 |
| 最大并发资格验证 | 10,000 |

---

## 13. 待定事项

| ID | 事项 | 优先级 |
|----|------|--------|
| C001 | 是否支持约束版本回滚 | P1 |
| C002 | 证据隔离区的详细流程 | P0 |
| C003 | 分布式事务支持 | P2 |
| C004 | 批量资格验证接口 | P1 |

---

## 14. 参考文献

- 理论文档: `docs/framework/02-核心原理与约束治理.md`
- 系统架构: `docs/implementation/architecture/01-system-overview.md`

---

**文档维护者**: [待定]
**审核人**: [待定]
**最后审核日期**: [待定]
