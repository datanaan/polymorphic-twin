# Polymorphic Twin

> **Trusted governance infrastructure for digital twin systems.**

Polymorphic Twin is a governance layer that sits between digital twin models and their controllers, determining which models can be trusted under what conditions. It does not predict — it adjudicates.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

---

## What is Polymorphic Twin?

Polymorphic Twin is **not** a digital twin platform (it doesn't replace Ansys Twin Builder or Azure Digital Twins). It is a **trusted governance layer** deployed between digital twins and controllers.

### Core Architecture

The framework consists of **five components** organized as "three systems + two foundations":

**Two Foundations:**
- **TOM (TwinObjectModel)** — Unified data model representing all entities as TwinObjects with structure, state, constraints, and intent
- **DomainPack** — Lightweight YAML/JSON configuration units that declare scenario-specific parameters

**Three Systems:**
- **Core** — Runtime constraint governance gatekeeper. Validates model qualification, enforces physical constraints, executes safe fallback, manages evidence admission
- **Lab** — Isolated offline exploration engine. Generates hypotheses, discovers constraints, finds counterexamples
- **Bridge** — Stateless decision interface layer. Translates TwinObject views into structured action option spaces for human decision makers

### Five Closed Loops

1. **Perception Loop**: External input → TOM → View projection → Scenario match
2. **Exploration Loop**: Scenario activation → Lab hypothesis → Pattern discovery → Hypothesis ranking
3. **Decision Loop**: Candidate hypotheses → Core qualification → Bridge orchestration → Execution plan
4. **Execution Loop**: Plan distribution → Tool calls → Result collection → State update
5. **Evolution Loop**: Execution results → Constraint learning → Scenario update → Lineage evolution

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Docker (optional, for containerized deployment)

### Install

```bash
# Clone the repository
git clone https://github.com/datanaan/polymorphic-twin
cd polymorphic-twin

# Install dependencies
pip install -e .

# For ML features
pip install -e ".[lab-ml]"

# For development
pip install -e ".[dev]"
```

### Run

```bash
# Start the API server
polytwin-cli serve

# Or with Docker
docker compose -f docker/docker-compose.yml up -d
```

### CLI Usage

```bash
# Validate a DomainPack configuration
polytwin-cli validate path/to/domainpack.yaml

# Run a simulation
polytwin-cli simulate path/to/scenario.yaml

# Export governance report
polytwin-cli export --format pdf
```

---

## Project Structure

```
├── src/polytwin/          # Main source package
│   ├── core/              # Constraint governance engine
│   ├── tom/               # TwinObjectModel
│   ├── lab/               # Exploration engine
│   ├── bridge/            # Decision interface layer
│   ├── domainpack/        # Scenario configuration
│   ├── api/               # FastAPI endpoints
│   ├── cli/               # CLI tools
│   └── jelly/             # Jelly platform integration
├── tests/                 # Test suite
├── docs/                  # Documentation
├── configs/               # Example configurations
├── docker/                # Docker deployment
└── examples/              # Usage examples
```

## Key Design Principles

- **Falsifiability first**: All constraints, assumptions, and conclusions must be verifiable/falsifiable
- **View isolation**: Different components see different views of the data
- **Scenario as boundary**: DomainPack defines clear scenario boundaries with maximum freedom within
- **Exploration/decision separation**: Lab explores without constraints; Bridge decides with constraints

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
