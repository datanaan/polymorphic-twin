<div align="center">

# Polymorphic Twin

**The trust layer for digital twins — not another simulation platform, the answer to "can I trust this model right now?"**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/datanaan/polymorphic-twin?style=social)](https://github.com/datanaan/polymorphic-twin)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-%E2%9C%94-green)](https://fastapi.tiangolo.com)

</div>

---

[**中文文档**](README.zh-CN.md) | **English**

---

## What is Polymorphic Twin?

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
