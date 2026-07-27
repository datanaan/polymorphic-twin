<div align="center">

# Polymorphic Twin

**数字孪生的信任治理层——不是又一个仿真平台，而是回答"这个模型现在能信吗？"**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-%E2%9C%94-green)](https://fastapi.tiangolo.com)

</div>

---

**中文** | [English](README.md)

---

## 什么是 Polymorphic Twin？

**每一个数字孪生都在做预测。Polymorphic Twin 决定哪些预测可以信任。**

现有的数字孪生平台（Ansys、Azure DT 等）擅长仿真——但它们都不回答那个最困难的问题："这个模型现在的输出，在这个场景下，能信吗？"

Polymorphic Twin 填补了这个空白。它不是又一个仿真平台，而是一个**信任裁决层**。

### 核心架构：三系统 + 两基础

| 组件 | 职责 |
|------|------|
| **Core** | 运行时约束守门员——验证、执行、安全回退 |
| **Lab** | 隔离探索引擎——生成假设、发现反例 |
| **Bridge** | 决策接口——结构化人机交互，不只是通过/拒绝 |
| **TOM** | 统一孪生对象模型——带状态、约束、意图的数据模型 |
| **DomainPack** | YAML 场景配置——声明边界、安全规则 |

### 核心创新

| 问题 | Polymorphic Twin 的方案 |
|------|----------------------|
| "这个模型现在能信吗？" | **可证伪性优先** — 每个模型带约束卡，运行时验证 |
| "Lab 会不会作弊？" | **视图隔离** — Lab 永远看不到验证集 |
| "人怎么参与决策？" | **结构化决策接口** — 展示完整的决策空间和不确定度 |

### 快速开始

```bash
# 安装
pip install -e .

# 启动服务
polytwin-cli serve

# 或使用 Docker
docker compose -f docker/docker-compose.yml up -d
```

---

## License

Apache 2.0 — 详见 [LICENSE](LICENSE)。
