<div align="center">

# Polymorphic Twin

**数字孪生的信任层。不是仿真平台——是回答"这个模型现在能信吗？"的那个东西。**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-%E2%9C%94-green)](https://fastapi.tiangolo.com)

</div>

**中文** | [English](README.md)

---

## 问题

数字孪生无处不在——Ansys、Azure DT、Siemens、Unity。它们擅长**仿真**。但没有人回答那个根本问题：

> **"这个模型现在的输出，在这个具体场景下，能信吗？"**

一个在正常情况下 99% 准确的模型，在边界条件下可能灾难性失败。一个传感器漂移就可以让一个本来完美的模型产生危险错误的预测。现有平台没有运行时检测机制——它们仿真、输出，然后让人类自己去判断要不要信。

**Polymorphic Twin 填补了这个空白。** 它不是又一个仿真平台。它是一个**信任裁决层**，部署在模型和控制器之间。

---

## 运行时实际流程

```
1. DomainPack 加载 → 声明状态变量、约束卡、回退策略、人类角色
2. TOM 创建 TwinObject → Identity + State + Lineage + Constraints
3. Core.validate() 接收当前状态值
   → evaluate_constraint() 逐条检查约束卡
   → M2-C2: safety_critical 失败 → 立即触发安全回退，停止后续检查
   → AuditLogWriter 记录每一次评估
4. Lab（离线隔离）探索：
   → 反例搜索：发现约束边界违反
   → 假设生成：提出可测试的模式
   → 失败关联：连接失败事件
   → 反事实：探索替代状态
5. Bridge 生成决策空间：
   → ActionSpaceBuilder 构建结构化选项
   → BridgeOutput 带有效期窗口和版本标签
   → 人类做知情决策，而不是盲目的通过/拒绝
```

### 视图隔离（核心创新）

| 视图 | 能看到 | 不能看到 |
|------|--------|---------|
| **CoreFullView** | 一切 | — |
| **LabExplorationView** | 约束摘要（无阈值） | 隐藏验证集、回退策略 |
| **BridgeDecisionView** | 行动空间、不确定度 | 验证逻辑、审计字段 |
| **AuditView** | 全部 + 变更历史 | — |

**Lab 无法作弊**——它永远看不到验证集和回退策略。

### API 端点

```
POST /v1/validate       — 验证状态 vs 约束卡
POST /v1/explore        — 运行 Lab 探索（反例/假设/等）
POST /v1/decide         — 生成人类决策空间
POST /v1/domainpacks    — 注册 DomainPack
GET  /v1/domainpacks/:id — 获取 DomainPack 配置
```

---

## 核心设计决策

| 决策 | 为什么 |
|------|--------|
| **可证伪性优先** | 每条约束卡必须在运行时可验证/可证伪——不仅仅是设计时 |
| **安全关键中断** | M2-C2：一个安全失败就停止一切。不存在"先检查完其他的再说" |
| **视图隔离** | Lab 看不到验证集——防止对治理的过拟合 |
| **无状态 Bridge** | 每次决策都是新鲜的——没有陈腐状态污染未来的决策 |
| **哈希链审计** | 每次验证、探索、决策都被不可变地记录 |

---

## 快速开始

```bash
# 安装
pip install -e .

# 启动 API 服务
polytwin-cli serve

# 或使用 Docker
docker compose -f docker/docker-compose.yml up -d
```

### Python SDK

```python
from polytwin import PolymorphicTwinEngine, EngineConfig

engine = PolymorphicTwinEngine(EngineConfig())

# 验证当前状态
result = await engine.validate(
    state_values={"temperature": 85.0, "pressure": 2.5},
    constraint_cards=[{...}],
)

if result.safety_fallback_triggered:
    print("⚠️ 安全关键违反——回退已激活！")
else:
    print(f"✅ 全部约束通过: {result.status}")
```

---

## License

Apache 2.0 — 详见 [LICENSE](LICENSE)。
