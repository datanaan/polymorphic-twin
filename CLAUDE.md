# CLAUDE.md

This file provides guidance to AI agents when working with code in this repository.

## Repository Overview

Polymorphic-Twin is a **trusted governance infrastructure for digital twin systems**. It is a governance layer deployed between digital twin models and their controllers, determining which models can be trusted under what conditions.

This is a Python project with:
- Source code in `src/polytwin/` (FastAPI + SQLAlchemy)
- Complete test suite in `tests/`
- Design documents in `docs/` (Chinese language)

## Quick Start

```bash
pip install -e .
polytwin-cli --help
```

## Architecture

The framework consists of **five components** organized as "three systems + two foundations":

**Two Foundations:**
- **TOM (TwinObjectModel)** — Unified data model
- **DomainPack** — YAML/JSON scenario configuration

**Three Systems:**
- **Core** — Runtime constraint governance gatekeeper
- **Lab** — Isolated offline exploration engine
- **Bridge** — Stateless decision interface layer

## Key Design Principles

- **Falsifiability first**: All constraints, assumptions, conclusions must be verifiable/falsifiable
- **View isolation**: Different components see different views of the data
- **Scenario as boundary**: DomainPack defines clear scenario boundaries
- **Exploration/decision separation**: Lab explores without constraints; Bridge decides with constraints
