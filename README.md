<div align="center">

# Polymorphic Twin

**The trust layer for digital twins — not another simulation platform, the answer to "can I trust this model right now?"**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/datanaan/polymorphic-twin?style=social)](https://github.com/datanaan/polymorphic-twin)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-%E2%9C%94-green)](https://fastapi.tiangolo.com)

</div>

---

<p align="center">
  <b>🇨🇳 中文</b> | <a href="#english">🇬🇧 English</a>
</p>

---

<h2>🇨🇳 什么是 Polymorphic Twin？</h2>

**每一个数字孪生都在做预测。Polymorphic Twin 决定哪些预测可以信任。**

现有的数字孪生平台（Ansys、Azure DT 等）擅长仿真——但它们都不回答那个最困难的问题："这个模型现在的输出，在这个场景下，能信吗？"

Polymorphic Twin 填补了这个空白。它不是又一个仿真平台，而是一个**信任裁决层**。

### 核心架构：三系统 + 两基础

```
┌─────────────────────────────────────────────────────┐
│                   Bridge                             │
│            (决策接口层 · 结构化人机交互)               │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                    Core                               │
│        (约束守门员 · 运行时验证 · 安全回退)           │
└──────┬───────────────────────────────────┬──────────┘
       │                                   │
┌──────▼──────┐                  ┌─────────▼──────────┐
│    Lab       │                  │       TOM          │
│ (探索引擎    │                  │  (统一孪生对象模型)  │
│  隔离验证)   │                  │                     │
└──────────────┘                  └─────────┬──────────┘
                                            │
                                   ┌────────▼─────────┐
                                   │   DomainPack      │
                                   │ (场景配置 · YAML)  │
                                   └──────────────────┘
```

### 核心创新

| 问题 | Polymorphic Twin 的方案 |
|------|----------------------|
| "这个模型现在能信吗？" | **可证伪性优先** — 每个模型带约束卡，运行时验证 |
| "Lab 会不会作弊？" | **视图隔离** — Lab 永远看不到验证集 |
| "人怎么参与决策？" | **结构化决策接口** — 不是简单的通过/拒绝，而是展示完整的决策空间 |

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

<h2 id="english">🇬🇧 What is Polymorphic Twin?</h2>

**Every digital twin makes predictions. Polymorphic Twin decides which predictions to trust.**

Current digital twin platforms (Ansys, Azure DT, etc.) are great at simulation — but none of them answer the hard question: "Can I trust this model's output right now, in this scenario?" Polymorphic Twin fills that gap. It's not another simulation platform — it's a **trust adjudication layer**.

### Architecture: Three Systems + Two Foundations

| Component | Role |
|-----------|------|
| **Core** | Runtime constraint gatekeeper — validates, enforces, falls back |
| **Lab** | Isolated exploration engine — generates hypotheses, finds counterexamples |
| **Bridge** | Decision interface — structured human-in-the-loop, not just pass/fail |
| **TOM** | TwinObjectModel — unified data model with state, constraints, intent |
| **DomainPack** | YAML scenario configuration — declares boundaries, safety rules |

### Key Innovations

| Problem | How Polymorphic Twin Solves It |
|---------|-------------------------------|
| "Can I trust this model right now?" | **Falsifiability-first** — constraint cards verified at runtime, not just design time |
| "Can the Lab cheat?" | **View isolation** — Lab literally cannot see the validation set |
| "How do humans decide?" | **Structured decision interface** — presents action spaces with uncertainty bounds |

### Quick Start

```bash
# Install
pip install -e .

# Start server
polytwin-cli serve

# Or with Docker
docker compose -f docker/docker-compose.yml up -d
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
