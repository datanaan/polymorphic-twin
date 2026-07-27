<div align="center">

# Polymorphic Twin

**The trust layer for digital twins. Not a simulation platform — the thing that answers "can I trust this model right now?"**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/datanaan/polymorphic-twin?style=social)](https://github.com/datanaan/polymorphic-twin)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-%E2%9C%94-green)](https://fastapi.tiangolo.com)

</div>

[**中文文档**](README.zh-CN.md) | **English**

---

## The Problem

Digital twins are everywhere — Ansys, Azure DT, Siemens, Unity. They're great at **simulation**. But none of them answer the fundamental question:

> **"Can I trust this model's output right now, in this specific scenario?"**

A model that's 99% accurate in normal conditions can fail catastrophically at the boundary. A sensor drift can make a perfectly good model produce dangerously wrong predictions. Current platforms have no mechanism to detect this at runtime — they simulate, they output, and the human is left to decide whether to trust the result.

**Polymorphic Twin fills this gap.** It's not another simulation platform. It's a **trust adjudication layer** that sits between models and their controllers.

---

## What It Actually Does

### Core Architecture: Three Systems + Two Foundations

```
                     ┌─────────────────────┐
                     │      Bridge          │
                     │  Decision Interface  │
                     │  (stateless, async)  │
                     └──────────┬──────────┘
                                │
┌───────────────────────────────▼──────────────────────────────┐
│                           Core                                │
│  ConstraintEngine · SafetyFallback · IdentityMonitor          │
│  M2-C2: safety_critical violations → IMMEDIATE INTERRUPT     │
│  AuditLogWriter · HardGate · Quarantine · Evidence Admission  │
└──────┬─────────────────────────────────────┬─────────────────┘
       │                                     │
┌──────▼──────────┐              ┌───────────▼──────────────┐
│      Lab         │              │        TOM               │
│  Exploration     │              │  TwinObjectModel          │
│  Engine          │              │                           │
│                  │              │  TwinObjectBase            │
│  Counterexample  │              │  Identity · State          │
│  Hypothesis      │              │  Lineage · Provenance      │
│  FailureCorrel.  │              │  Constraints · Views       │
│  Counterfactual  │              │                           │
└──────────────────┘              └───────────┬──────────────┘
                                              │
                                     ┌───────▼──────────────┐
                                     │    DomainPack          │
                                     │  YAML scenario config  │
                                     │  (state vars,          │
                                     │   constraint cards,    │
                                     │   fallback, roles)     │
                                     └───────────────────────┘
```

### Runtime Flow

```
1. DomainPack loaded → declares state variables, constraint cards, fallback strategies, human roles
2. TOM creates TwinObject → Identity + State + Lineage + Constraints
3. Core.validate() called with current state values
   → evaluate_constraint() for each card
   → M2-C2: safety_critical FAIL → IMMEDIATE SafetyFallback, stop further checks
   → AuditLogWriter records every evaluation
4. Lab (offline, isolated) explores:
   → Counterexample search: find boundary violations
   → Hypothesis generation: propose testable patterns
   → Failure correlation: connect failure events
   → Counterfactual: explore alternative states
5. Bridge generates action space:
   → ActionSpaceBuilder builds structured options from view data
   → BridgeOutput with validity window and version tag
   → Human makes informed decision, not blind pass/fail
```

### View Isolation (The Key Innovation)

| View | Sees | Cannot See |
|------|------|-----------|
| **CoreFullView** | Everything | — |
| **LabExplorationView** | Constraints summary (no thresholds) | Hidden validation sets, fallback strategy |
| **BridgeDecisionView** | Action space, uncertainty bounds | Certifier logic, audit fields |
| **AuditView** | All + change history | — |

**Lab literally cannot cheat** — it never sees the validation set or the fallback strategy.

### API Endpoints

```
POST /v1/validate       — Validate state against constraint cards
POST /v1/explore        — Run lab exploration (counterexample/hypothesis/etc.)
POST /v1/decide         — Generate action space for human decision
POST /v1/domainpacks    — Register a DomainPack
GET  /v1/domainpacks/:id — Get DomainPack configuration
GET  /v1/health         — Service health
```

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| **Falsifiability-first** | Every constraint card must be verifiable/falsifiable at runtime — not just at design time |
| **Safety-critical interrupt** | M2-C2: one safety failure stops everything. No "let's check the rest first" |
| **View isolation** | Lab cannot see validation sets — prevents overfitting the governance |
| **Stateless Bridge** | Each decision is fresh — no stale state poisoning future decisions |
| **Hash-chain audit** | Every validation, exploration, and decision is immutably recorded |

---

## Quick Start

```bash
# Install
pip install -e .

# Start API server
polytwin-cli serve

# Or with Docker
docker compose -f docker/docker-compose.yml up -d
```

### Python SDK

```python
from polytwin import PolymorphicTwinEngine, EngineConfig

engine = PolymorphicTwinEngine(EngineConfig())

# Validate current state against constraint cards
result = await engine.validate(
    state_values={"temperature": 85.0, "pressure": 2.5},
    constraint_cards=[{...}],  # From DomainPack
)

if result.safety_fallback_triggered:
    print("⚠️ Safety-critical violation — fallback activated!")
else:
    print(f"✅ All constraints passed: {result.status}")
```

---

## Project Structure

```
src/polytwin/
├── core/           # Constraint governance engine
│   ├── engine.py       # ConstraintEngine — main validation loop
│   ├── fallback.py     # SafetyFallback — M2-C2 interrupt handler
│   ├── audit.py        # AuditLogWriter — immutable record
│   ├── identity_monitor.py
│   └── rules/          # Constraint evaluation + combination
├── tom/            # TwinObjectModel
│   ├── facade.py       # TwinObjectFacade — unified entry point
│   ├── base_models.py  # Identity, State, Lineage, TwinObjectBase
│   ├── domain_models.py# ActionState, ConstraintState, etc.
│   └── views.py        # View isolation (Core, Lab, Bridge, Audit)
├── lab/            # Exploration engine
│   ├── explorer.py     # LabExplorer — 4 exploration modes
│   ├── counterexample.py
│   ├── hypothesis.py
│   ├── sandbox.py      # Isolated execution environment
│   └── strategies/     # Algorithmic, heuristic strategies
├── bridge/         # Decision interface
│   ├── orchestrator.py # BridgeOrchestrator — stateless action space
│   └── action_space.py # ActionSpaceBuilder
├── domainpack/     # YAML/JSON scenario configuration
├── api/            # FastAPI endpoints
│   └── routes/         # validate, explore, decide, health
├── cli/            # CLI tools (click)
└── jelly/          # Jelly platform integration
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
