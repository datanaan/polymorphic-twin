# Polymorphic-Twin 产品化设计规范：API 服务

> **版本**: 1.0.0
> **日期**: 2026-05-07
> **状态**: 待审核
> **前置条件**: M8 SDK 完成打包
> **覆盖里程碑**: M10 (API 服务)
> **关联 Spec**: `2026-05-07-product-overview-sdk.md` §3 (公共 API)

---

## 1. 设计决策

| 决策项 | 结论 | 理由 |
|--------|------|------|
| 架构 | FastAPI 单体应用，引擎作为 library 嵌入 | 与引擎单体架构一致，不引入微服务复杂度 |
| 认证 | API Key + RBAC | 最简方案，满足多用户场景，未来可扩展 OAuth2 |
| 多实例 | 单进程管理多个 TwinObject 实例 | 引擎已在内存中支持多实例，API 层只需加生命周期管理 |
| 部署 | Docker + docker-compose | 单节点部署足够演示和小规模使用 |
| 存储 | PostgreSQL（生产）+ SQLite（开发） | 复用引擎 Spec 的存储抽象 |

---

## 2. API 设计

### 2.1 URL 结构

```
/api/v1/
├── health/                        # 健康检查
├── auth/
│   └── api-keys/                  # API Key 管理（管理员）
├── twins/                         # TwinObject 实例管理
│   ├── POST /                     # 创建 TwinObject
│   ├── GET /                      # 列出 TwinObject
│   ├── {twin_id}/
│   │   ├── GET                    # 获取详情
│   │   ├── DELETE                 # 删除
│   │   ├── state/                 # 状态管理
│   │   │   ├── GET                # 当前状态
│   │   │   └── PUT                # 更新状态（感知闭环入口）
│   │   ├── views/                 # 视图投影
│   │   │   └── {view_type}/GET
│   │   ├── constraints/           # 约束验证
│   │   │   ├── GET                # 当前约束状态
│   │   │   └── POST /validate     # 触发验证
│   │   ├── actions/               # Bridge 行动空间
│   │   │   ├── GET                # 当前行动空间
│   │   │   └── POST /generate     # 生成行动空间
│   │   │   └── {action_id}/
│   │   │       └── POST /respond  # 人类响应
│   │   ├── lab/                   # Lab 探索
│   │   │   ├── POST /explore      # 启动探索
│   │   │   ├── GET /results       # 查看结果
│   │   │   └── POST /submit       # 提交到 Core
│   │   └── snapshots/             # 快照管理
│   │       ├── GET                # 列出快照
│   │       └── POST               # 创建快照
├── domain-packs/                  # DomainPack 管理
│   ├── POST /                     # 上传 DomainPack
│   ├── GET /                      # 列出 DomainPack
│   ├── {pack_id}/
│   │   ├── GET                    # 获取详情
│   │   ├── DELETE                 # 删除
│   │   ├── validate/POST          # 校验
│   │   ├── activate/POST          # 激活（绑定到 TwinObject）
│   │   └── deactivate/POST        # 停用
│   └── templates/GET              # 可用模板列表
└── audit/                         # 审计日志
    ├── GET /                      # 查询审计日志
    └── GET /export                # 导出审计日志
```

### 2.2 核心端点规格

#### 创建 TwinObject

```http
POST /api/v1/twins/
Content-Type: application/json
Authorization: Bearer <api-key>

{
  "name": "CSTR-001",
  "description": "1号连续搅拌釜反应器",
  "domain_pack_id": "cstr.standard",
  "initial_state": {
    "temperature": 25.0,
    "pressure": 1.0,
    "concentration_A": 3.0,
    "concentration_B": 0.0,
    "flow_rate_in": 50.0,
    "coolant_flow": 100.0,
    "agitator_speed": 300.0,
    "reaction_rate": 0.0
  }
}
```

**响应** `201 Created`：
```json
{
  "twin_id": "twin_abc123",
  "name": "CSTR-001",
  "domain_pack_id": "cstr.standard",
  "status": "active",
  "created_at": "2026-05-07T10:00:00Z"
}
```

**验收**：
- 有效请求返回 201，twin_id 非空
- 缺少必填字段返回 422 + 详细错误
- 无效 domain_pack_id 返回 404
- 无权限返回 403

---

#### 更新状态（感知闭环入口）

```http
PUT /api/v1/twins/{twin_id}/state/
Authorization: Bearer <api-key>

{
  "temperature": 185.3,
  "pressure": 15.2,
  "concentration_A": 1.8,
  "concentration_B": 1.2
}
```

**响应** `200 OK`：
```json
{
  "twin_id": "twin_abc123",
  "updated_variables": ["temperature", "pressure", "concentration_A", "concentration_B"],
  "constraint_evaluation": {
    "max_temperature": "passed",
    "max_pressure": "passed",
    "min_coolant_flow": "passed",
    "mass_balance": "passed",
    "thermal_runaway_warning": "not_applicable",
    "reaction_efficiency": "passed",
    "yield_optimization": "passed",
    "agitator_integrity": "passed"
  },
  "safety_status": "normal",
  "evaluated_at": "2026-05-07T10:01:30Z"
}
```

**safety_critical 触发时** `200 OK` + 额外字段：
```json
{
  "safety_status": "fallback_triggered",
  "fallback_action": "emergency_shutdown",
  "fallback_reason": "max_temperature violated: 285.0 > 280.0",
  "fallback_triggered_at": "2026-05-07T10:02:15.187Z",
  "fallback_duration_ms": 187
}
```

**验收**：
- 正常状态更新返回约束评估结果
- safety_critical 违规触发安全回落，响应中包含回落信息
- 不存在的 twin_id 返回 404
- 状态值超范围返回 422 + InvalidStateError

---

#### 生成行动空间（决策闭环）

```http
POST /api/v1/twins/{twin_id}/actions/generate
Authorization: Bearer <api-key>
```

**响应** `200 OK`：
```json
{
  "bridge_output_id": "bo_xyz789",
  "twin_id": "twin_abc123",
  "generated_at": "2026-05-07T10:03:00Z",
  "valid_until": "2026-05-07T10:33:00Z",
  "immediate_actions": [
    {
      "action_id": "act_001",
      "action_template": "adjust_coolant",
      "parameters": {"coolant_flow": {"min": 80, "max": 200}},
      "execution_mode": "human_approval",
      "risk_level": "low"
    }
  ],
  "conditional_actions": [
    {
      "action_id": "act_002",
      "action_template": "adjust_feed_rate",
      "parameters": {"flow_rate_in": {"min": 30, "max": 70}},
      "unmet_prerequisites": ["确认冷却水系统正常"],
      "lawful_unlock_path": "提交冷却水检查报告"
    }
  ],
  "forbidden_actions": [
    {
      "action_id": "act_003",
      "action_template": "adjust_feed_rate",
      "prohibition_reason": "当前温度接近安全上限，增加进料可能导致失控",
      "lawful_unlock_conditions": "温度降至 200°C 以下",
      "permanently_forbidden": false
    }
  ],
  "undetermined_actions": []
}
```

**验收**：
- 行动空间四分类结构完整
- forbidden_actions 包含 prohibition_reason
- 有效期 valid_until 正确计算
- TwinObject 版本变化后旧输出标记为失效

---

#### 启动 Lab 探索

```http
POST /api/v1/twins/{twin_id}/lab/explore
Authorization: Bearer <api-key>

{
  "task_type": "constraint_hypothesis",
  "budget": {
    "max_iterations": 100,
    "max_time_seconds": 300,
    "max_memory_mb": 512
  }
}
```

**响应** `202 Accepted`（异步任务）：
```json
{
  "exploration_id": "exp_abc456",
  "twin_id": "twin_abc123",
  "status": "running",
  "started_at": "2026-05-07T10:05:00Z",
  "estimated_completion": "2026-05-07T10:10:00Z"
}
```

**查询结果** `GET /api/v1/twins/{twin_id}/lab/results?exploration_id=exp_abc456`：
- status = running → 202 + 进度百分比
- status = completed → 200 + ExplorationResult
- status = failed → 200 + 错误信息

**验收**：
- 探索异步启动，不阻塞 API
- 完成后可查询结果
- Lab 隔离性：探索结果不直接影响 TwinObject 状态

---

### 2.3 WebSocket 端点（实时推送）

```http
WS /api/v1/twins/{twin_id}/ws
Authorization: Bearer <api-key>
```

**推送事件类型**：

| 事件类型 | 触发时机 | 数据 |
|----------|----------|------|
| `state_updated` | 状态更新后 | 新状态值 |
| `constraint_evaluated` | 约束评估完成 | 评估结果 |
| `fallback_triggered` | 安全回落触发 | 回落动作和原因 |
| `action_space_updated` | 行动空间变更 | 新的 BridgeOutput |
| `exploration_progress` | Lab 探索进度 | 进度百分比 |
| `exploration_completed` | Lab 探索完成 | ExplorationResult 摘要 |
| `identity_status_changed` | 身份状态变化 | 新的身份状态 |
| `domain_pack_updated` | DomainPack 版本更新 | 新版本号 |

**验收**：
- WebSocket 连接建立后能接收实时事件
- 事件顺序与引擎内部一致
- 断线后重连不丢失中间状态（可查询 REST API 补齐）

---

## 3. 认证与授权

### 3.1 API Key 认证

**方案**：每个用户持有一个或多个 API Key，请求时通过 `Authorization: Bearer <key>` 传递。

```python
class APIKey(BaseModel):
    key_id: str
    key_hash: str                  # 只存哈希，不存明文
    name: str                      # 用户可读名称
    user_id: str
    roles: list[Role]
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
```

**Key 生成**：`ptw_` 前缀 + 32 字节随机数，base64 编码。

**验收**：
- 有效 Key 正确认证
- 过期 Key 返回 401
- 无效 Key 返回 401
- Key 明文只在创建时显示一次

### 3.2 RBAC 角色定义

| 角色 | 权限范围 |
|------|----------|
| `admin` | 全部操作：管理 API Key、创建/删除 TwinObject、上传 DomainPack、查看审计日志 |
| `operator` | 操作指定 TwinObject：更新状态、触发验证、响应行动、启动探索 |
| `viewer` | 只读：查看 TwinObject 状态、约束结果、行动空间、探索结果 |
| `domain_expert` | DomainPack 管理：上传、校验、激活 DomainPack，不能操作 TwinObject |
| `auditor` | 审计专用：查看和导出审计日志，不能修改任何数据 |

### 3.3 权限矩阵

| 操作 | admin | operator | viewer | domain_expert | auditor |
|------|:-----:|:--------:|:------:|:-------------:|:-------:|
| 管理 API Key | ✓ | ✗ | ✗ | ✗ | ✗ |
| 创建 TwinObject | ✓ | ✗ | ✗ | ✗ | ✗ |
| 删除 TwinObject | ✓ | ✗ | ✗ | ✗ | ✗ |
| 更新状态 | ✓ | ✓ | ✗ | ✗ | ✗ |
| 触发约束验证 | ✓ | ✓ | ✗ | ✗ | ✗ |
| 生成行动空间 | ✓ | ✓ | ✗ | ✗ | ✗ |
| 响应行动 | ✓ | ✓ | ✗ | ✗ | ✗ |
| 启动 Lab 探索 | ✓ | ✓ | ✗ | ✗ | ✗ |
| 查看 TwinObject | ✓ | ✓ | ✓ | ✗ | ✓ |
| 上传 DomainPack | ✓ | ✗ | ✗ | ✓ | ✗ |
| 校验 DomainPack | ✓ | ✗ | ✗ | ✓ | ✗ |
| 激活/停用 | ✓ | ✗ | ✗ | ✓ | ✗ |
| 查看审计日志 | ✓ | ✗ | ✗ | ✗ | ✓ |
| 导出审计日志 | ✓ | ✗ | ✗ | ✗ | ✓ |

### 3.4 验收点

| 编号 | 类别 | 验收项 | 通过标准 |
|------|------|--------|----------|
| AUTH-01 | 功能 | API Key 创建 | 生成格式为 `ptw_xxxx` 的 Key |
| AUTH-02 | 功能 | 认证正确性 | 有效 Key 200，无效 Key 401 |
| AUTH-03 | 功能 | RBAC 生效 | 每种角色的权限与矩阵一致 |
| AUTH-04 | 测试 | 越权测试 | 每个角色尝试越权操作全部返回 403 |
| AUTH-05 | 测试 | Key 过期测试 | 过期 Key 返回 401 |

---

## 4. 多实例管理

### 4.1 实例生命周期

```
              ┌─────────┐
              │ created  │
              └────┬─────┘
                   │ activate (绑定 DomainPack)
              ┌────▼─────┐
         ┌────│  active   │────┐
         │    └────┬─────┘    │
         │ suspend│          │ deactivate
    ┌────▼─────┐  │    ┌─────▼─────┐
    │suspended │  │    │inactive   │
    └────┬─────┘  │    └─────┬─────┘
         │resume  │          │delete
         └────────┤     ┌────▼─────┐
                  └────►│ deleted  │
                        └──────────┘
```

### 4.2 实例管理规格

| 操作 | 端点 | 行为 |
|------|------|------|
| 创建 | `POST /twins/` | 创建 TwinObject，绑定 DomainPack |
| 激活 | 自动 | 创建时自动激活，开始约束监控 |
| 暂停 | `POST /twins/{id}/suspend` | 停止约束监控和身份检查，保留快照 |
| 恢复 | `POST /twins/{id}/resume` | 从暂停恢复，执行全量约束验证 |
| 停用 | `POST /twins/{id}/deactivate` | 释放资源，保留审计日志 |
| 删除 | `DELETE /twins/{id}` | 删除所有数据（需确认，保留审计摘要） |

### 4.3 资源隔离

| 维度 | 隔离方式 |
|------|----------|
| TwinObject 数据 | 每个 TwinObject 独立的内存对象 + 数据库行 |
| DomainPack 配置 | 共享只读引用（多个 TwinObject 可用同一 DomainPack） |
| Lab 沙箱 | 每个 TwinObject 的探索在独立沙箱中运行 |
| 审计日志 | 每个 TwinObject 独立审计流，支持按 twin_id 查询 |
| 资源限制 | 单个 TwinObject 的 Lab 探索受 budget 约束 |

### 4.4 并发能力

| 指标 | 目标值 |
|------|--------|
| 最大并行 TwinObject 数 | 100（可配置） |
| 状态更新吞吐 | ≥ 1000 req/s（per instance） |
| 约束验证延迟 | p99 < 10ms |
| WebSocket 并发连接 | ≥ 50 per instance |

### 4.5 验收点

| 编号 | 类别 | 验收项 | 通过标准 |
|------|------|--------|----------|
| INST-01 | 功能 | 多实例并行 | 同时运行 3 个 TwinObject（不同 DomainPack），各自独立 |
| INST-02 | 功能 | 实例隔离 | TwinObject A 的操作不影响 TwinObject B 的状态和约束 |
| INST-03 | 功能 | 生命周期 | created→active→suspended→active→deactivated→deleted 全流程 |
| INST-04 | 测试 | 并发测试 | 10 个 TwinObject 同时更新状态，约束验证结果正确 |
| INST-05 | 测试 | 资源泄漏 | 创建+删除 100 个 TwinObject 后，内存无持续增长 |

---

## 5. 外部集成接口

### 5.1 数据接入（传感器 → TwinObject）

```http
POST /api/v1/twins/{twin_id}/state/
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "source": "sensor_gateway",
  "timestamp": "2026-05-07T10:01:30.000Z",
  "values": {
    "temperature": 185.3,
    "pressure": 15.2
  }
}
```

**批量接入**：

```http
POST /api/v1/twins/{twin_id}/state/batch
Authorization: Bearer <api-key>

{
  "readings": [
    {"timestamp": "2026-05-07T10:01:30.000Z", "values": {"temperature": 185.3}},
    {"timestamp": "2026-05-07T10:01:31.000Z", "values": {"temperature": 186.1}},
    {"timestamp": "2026-05-07T10:01:32.000Z", "values": {"temperature": 187.5}}
  ]
}
```

**验收**：
- 单条和批量接入均正常
- 批量接入按时间戳顺序处理
- 时间戳早于最后更新时间的数据标记为 delayed，不影响约束评估

### 5.2 控制器接口（Bridge → 控制器）

```http
POST /api/v1/twins/{twin_id}/actions/{action_id}/execute
Authorization: Bearer <api-key>

{
  "confirmed_by": "user_id",
  "parameters": {"coolant_flow": 150.0}
}
```

**Webhook 回调配置**：

```http
PUT /api/v1/twins/{twin_id}/webhooks/
Authorization: Bearer <api-key>

{
  "on_fallback_triggered": "https://controller.example.com/api/emergency",
  "on_constraint_failed": "https://monitor.example.com/api/alert",
  "on_action_executed": "https://controller.example.com/api/confirm"
}
```

**验收**：
- 执行请求校验行动空间有效期
- Webhook 回调在事件触发后 1s 内发出
- 回调失败不阻塞引擎操作，记录在审计日志中

### 5.3 审计导出

```http
GET /api/v1/audit/export?from=2026-05-07T00:00:00Z&to=2026-05-07T23:59:59Z&format=json
Authorization: Bearer <api-key>
```

**支持格式**：JSON, CSV

**验收**：
- 导出数据包含时间范围内的全部审计事件
- CSV 格式可被 Excel 打开
- 大数据量（>10万条）支持流式下载

---

## 6. 部署架构

### 6.1 Docker 镜像

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e ".[postgres]"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

CMD ["uvicorn", "polymorphic_twin.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 docker-compose.yml

```yaml
version: "3.9"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PT_STORAGE_BACKEND=postgres
      - PT_STORAGE_URL=postgresql+asyncpg://pt:pt@db:5432/polymorphic_twin
      - PT_LOG_LEVEL=INFO
      - PT_ADMIN_API_KEY=${ADMIN_API_KEY}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=polymorphic_twin
      - POSTGRES_USER=pt
      - POSTGRES_PASSWORD=pt
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pt"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

### 6.3 环境配置

| 环境变量 | 必填 | 默认值 | 说明 |
|----------|------|--------|------|
| `PT_STORAGE_BACKEND` | 否 | memory | memory / sqlite / postgres |
| `PT_STORAGE_URL` | 条件 | — | postgres 时必填 |
| `PT_LOG_LEVEL` | 否 | INFO | DEBUG / INFO / WARNING / ERROR |
| `PT_LOG_FORMAT` | 否 | json | json / text |
| `PT_ADMIN_API_KEY` | 是 | — | 初始管理员 Key |
| `PT_MAX_TWINS` | 否 | 100 | 最大 TwinObject 实例数 |
| `PT_CORS_ORIGINS` | 否 | — | 允许的 CORS 来源，逗号分隔 |

### 6.4 健康检查

```http
GET /api/v1/health/
```

**响应**：
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "storage": "connected",
  "active_twins": 3,
  "uptime_seconds": 86400
}
```

**降级状态**：
```json
{
  "status": "degraded",
  "version": "0.1.0",
  "storage": "reconnecting",
  "active_twins": 3,
  "warnings": ["Storage connection intermittent"]
}
```

### 6.5 备份恢复

| 操作 | 方式 | 验收 |
|------|------|------|
| 备份 TwinObject 快照 | `POST /api/v1/twins/{id}/snapshots/` | 快照创建成功 |
| 导出全部数据 | `GET /api/v1/audit/export?format=json` + TwinObject dump | 数据完整 |
| PostgreSQL 备份 | `pg_dump` | 标准工具支持 |
| 恢复 | 从 SQL dump 恢复 + 重启服务 | 数据一致性校验通过 |

---

## 7. 监控指标

### 7.1 应用指标

| 指标 | 类型 | 含义 |
|------|------|------|
| `pt_requests_total` | Counter | HTTP 请求总数（按 method, path, status） |
| `pt_request_duration_seconds` | Histogram | 请求延迟 |
| `pt_active_twins` | Gauge | 当前活跃 TwinObject 数 |
| `pt_constraint_evaluations_total` | Counter | 约束评估次数（按 result） |
| `pt_fallback_triggered_total` | Counter | 安全回落触发次数 |
| `pt_lab_explorations_total` | Counter | Lab 探索次数（按 status） |
| `pt_bridge_generations_total` | Counter | Bridge 行动空间生成次数 |
| `pt_websocket_connections` | Gauge | 当前 WebSocket 连接数 |

### 7.2 端点

```http
GET /metrics
```

格式：Prometheus exposition format。

**验收**：所有指标在对应事件触发后递增/更新。

---

## 8. 测试要求

### 8.1 单元测试

| 测试类 | 测试点 | 数量要求 |
|--------|--------|----------|
| `TestAPIEndpoints` | 每个端点的正常/异常请求 | ≥ 30 |
| `TestAuthentication` | Key 创建/验证/过期、角色权限 | ≥ 15 |
| `TestMultiInstance` | 创建/删除/暂停/恢复/并行操作 | ≥ 10 |
| `TestWebhookDelivery` | 回调发送/失败重试 | ≥ 5 |
| `TestDataIntegrity` | 并发更新不丢数据 | ≥ 5 |

### 8.2 集成测试

| 场景 | 步骤 | 通过标准 |
|------|------|----------|
| 五闭环 API 流 | 创建 TwinObject → 更新状态 → 触发探索 → 生成行动空间 → 执行行动 → 查看演化 | 全链路 HTTP 200/201/202 |
| 多用户并发 | admin 创建 TwinObject，operator 更新状态，viewer 查看结果 | 各角色权限正确，数据一致 |
| 安全回落 API 流 | 更新状态触发 safety_critical → 检查回落响应 → 检查审计日志 | 回落触发，审计记录完整 |
| Docker 部署 | docker-compose up → 健康检查 → 创建 TwinObject → 操作 | 全部正常 |

### 8.3 性能测试

| 指标 | 测试方法 | 目标 |
|------|----------|------|
| 状态更新吞吐 | 并发 100 连续 PUT /state/ | ≥ 1000 req/s |
| 约束验证延迟 | 单次状态更新中测量 | p99 < 10ms |
| 安全回落延迟 | 触发 safety_critical 到回落完成 | < 200ms |
| WebSocket 延迟 | 事件触发到客户端接收 | < 100ms |
| API 启动时间 | 冷启动到健康检查通过 | < 10s |

### 8.4 验收点

| 编号 | 类别 | 验收项 | 通过标准 |
|------|------|--------|----------|
| M10-V01 | 功能 | Docker 部署 | `docker-compose up` 后健康检查通过 |
| M10-V02 | 功能 | 全部 API 端点 | Swagger UI 可访问，所有端点可操作 |
| M10-V03 | 功能 | 认证授权 | 5 种角色权限与矩阵一致 |
| M10-V04 | 功能 | 多实例并行 | 3 个不同 DomainPack 的 TwinObject 同时运行 |
| M10-V05 | 功能 | WebSocket 推送 | 状态更新后 1s 内收到推送事件 |
| M10-F01 | 检查点 | OpenAPI 文档 | 自动生成，覆盖全部端点 |
| M10-F02 | 检查点 | 审计完整 | 每次状态变更、约束评估、行动执行都有审计记录 |
| M10-F03 | 检查点 | 监控指标 | /metrics 端点暴露全部 §7.1 指标 |
| M10-T01 | 测试 | 单元测试覆盖率 | ≥ 85% |
| M10-T02 | 测试 | 集成测试 | 4 个场景全部通过 |
| M10-T03 | 测试 | 性能测试 | 全部指标达标 |
| M10-T04 | 测试 | 安全测试 | 无认证无法访问任何端点，越权全部 403 |

---

## 9. 文件结构

```
polymorphic_twin/
├── api/
│   ├── __init__.py
│   ├── app.py                    # FastAPI 应用
│   ├── config.py                 # API 配置
│   ├── dependencies.py           # 依赖注入（认证、引擎实例）
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py               # API Key 认证中间件
│   │   ├── logging.py            # 请求日志中间件
│   │   └── error_handler.py      # 全局异常处理
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── twins.py              # TwinObject 端点
│   │   ├── domain_packs.py       # DomainPack 端点
│   │   ├── lab.py                # Lab 探索端点
│   │   ├── actions.py            # Bridge 行动端点
│   │   ├── audit.py              # 审计端点
│   │   └── websocket.py          # WebSocket 端点
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── api_key.py            # API Key 管理
│   │   ├── rbac.py               # RBAC 权限检查
│   │   └── models.py             # 用户/角色数据模型
│   └── services/
│       ├── __init__.py
│       ├── twin_manager.py       # TwinObject 生命周期管理
│       └── event_bus.py          # 内部事件总线（WebSocket 推送用）
├── tests/
│   └── api/
│       ├── unit/
│       │   ├── test_endpoints.py
│       │   ├── test_auth.py
│       │   └── test_multi_instance.py
│       ├── integration/
│       │   ├── test_five_loops.py
│       │   ├── test_multi_user.py
│       │   ├── test_safety_fallback.py
│       │   └── test_docker_deploy.py
│       └── performance/
│           ├── test_throughput.py
│           ├── test_latency.py
│           └── test_websocket.py
├── Dockerfile
├── docker-compose.yml
└── docker-compose.dev.yml          # 开发用（SQLite + 热重载）
```

---

## 10. 审核记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-05-07 | 初始版本：API 设计、认证授权、多实例管理、外部集成、部署架构 |
| v1.1.0 | 2026-05-08 | Jelly 集成：DomainPack 端点可代理 Jelly 搜索、Lab explore 可触发 Jelly 数据获取、知识查询端点、RBAC 新增 query_external_knowledge 动作 |
