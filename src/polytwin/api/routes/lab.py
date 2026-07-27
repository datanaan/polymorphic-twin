"""Lab routes: exploration modes, data release, and submission chain.

All Lab endpoints operate on LabExplorationView-projected data only.
Hidden validation sets are never exposed through these routes.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from polytwin.api.deps import (
    get_data_release,
    get_explorer,
    get_submission_chain,
)
from polytwin.lab.types import CandidateModelPackage, ExplorationBudget

router = APIRouter()


# ── Request models ──────────────────────────────────────────────────


class ExploreCounterexampleRequest(BaseModel):
    """Request body for counterexample search."""

    data: dict = Field(default_factory=dict)
    constraints: list[dict] = Field(default_factory=list)
    budget: ExplorationBudget | None = None


class ExploreHypothesisRequest(BaseModel):
    """Request body for hypothesis generation."""

    data: dict = Field(default_factory=dict)
    constraints: list[dict] = Field(default_factory=list)
    budget: ExplorationBudget | None = None


class ExploreCorrelationRequest(BaseModel):
    """Request body for failure correlation analysis."""

    failure_logs: list[dict] = Field(default_factory=list)
    budget: ExplorationBudget | None = None


class ExploreCounterfactualRequest(BaseModel):
    """Request body for counterfactual generation."""

    base_state: dict = Field(default_factory=dict)
    constraints: list[dict] = Field(default_factory=list)
    budget: ExplorationBudget | None = None


class SubmitCandidatesRequest(BaseModel):
    """Request body for Lab-to-Core submission."""

    candidates: list[dict] = Field(default_factory=list)


# ── Routes ──────────────────────────────────────────────────────────


@router.post("/explore/counterexample")
async def explore_counterexample(body: ExploreCounterexampleRequest) -> dict:
    """Mode 1: Find boundary violations via counterexample search."""
    explorer = get_explorer()
    results = await explorer.run_counterexample_search(
        data=body.data,
        constraints=body.constraints,
        budget=body.budget,
    )
    return {
        "counterexamples": [c.model_dump() for c in results],
        "count": len(results),
    }


@router.post("/explore/hypothesis")
async def explore_hypothesis(body: ExploreHypothesisRequest) -> dict:
    """Mode 2: Generate constraint hypotheses."""
    explorer = get_explorer()
    results = await explorer.run_constraint_hypothesis(
        data=body.data,
        constraints=body.constraints,
        budget=body.budget,
    )
    return {
        "hypotheses": [h.model_dump() for h in results],
        "count": len(results),
    }


@router.post("/explore/correlation")
async def explore_correlation(body: ExploreCorrelationRequest) -> dict:
    """Mode 3: Correlate failure events."""
    explorer = get_explorer()
    results = await explorer.run_failure_correlation(
        failure_logs=body.failure_logs,
        budget=body.budget,
    )
    return {
        "findings": [f.model_dump() for f in results],
        "count": len(results),
    }


@router.post("/explore/counterfactual")
async def explore_counterfactual(body: ExploreCounterfactualRequest) -> dict:
    """Mode 4: Explore alternative states."""
    explorer = get_explorer()
    results = await explorer.run_counterfactual_generation(
        base_state=body.base_state,
        constraints=body.constraints,
        budget=body.budget,
    )
    return {
        "scenarios": [s.model_dump() for s in results],
        "count": len(results),
    }


@router.get("/strategies")
async def list_strategies() -> dict:
    """List available exploration strategies."""
    explorer = get_explorer()
    strategy = explorer._strategy
    return {
        "strategies": [
            {
                "name": strategy.name(),
                "constraint_awareness": strategy.constraint_awareness(),
                "data_requirements": strategy.data_requirements(),
                "exploration_space": strategy.exploration_space_mapping(),
                "health": strategy.health_indicators(),
            }
        ],
    }


@router.get("/data-release/{dp_id}")
async def data_release(dp_id: str) -> dict:
    """Get Core-released data for Lab exploration.

    Only LabExplorationView-compatible data is returned. Hidden
    validation sets are never exposed.
    """
    data_mgr = get_data_release()
    data = await data_mgr.get_authorized_data(dp_id)
    return {"data": data, "hidden_exposure": False}


@router.post("/submit")
async def submit_candidates(body: SubmitCandidatesRequest) -> dict:
    """Submit candidate models from Lab to Core through the submission chain.

    Returns desensitized feedback -- Lab cannot distinguish rejection reasons.
    """
    chain = get_submission_chain()
    candidates = [CandidateModelPackage(**c) for c in body.candidates]
    result = await chain.submit(candidates)
    return result.model_dump()
