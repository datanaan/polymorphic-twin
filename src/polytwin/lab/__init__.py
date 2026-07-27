"""Lab module: isolated exploration engine for the Polymorphic-Twin framework.

The Lab operates in complete isolation from Core internals. It can ONLY
access LabExplorationView-projected data and cannot see hidden validation
sets, certifier logic, or Core engine state.

Key components:
- Sandbox: isolated execution environment
- LabExplorer: four exploration mode orchestrator
- DataReleaseManager: controlled Core-to-Lab data channel
- SubmissionChain: Lab-to-Core candidate submission pipeline
- ExplorationStrategy (ABC): pluggable strategy interface
- AlgorithmicStrategy: grid-search based implementation
"""
from polytwin.lab.counterexample import CounterexampleFinder
from polytwin.lab.counterfactual import CounterfactualGenerator
from polytwin.lab.data_release import DataReleaseManager
from polytwin.lab.explorer import LabExplorer
from polytwin.lab.failure_analyzer import FailureAnalyzer
from polytwin.lab.hypothesis import HypothesisGenerator
from polytwin.lab.sandbox import Sandbox
from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.strategies.base import ExplorationStrategy
from polytwin.lab.submission import SubmissionChain
from polytwin.lab.types import (
    CandidateModelPackage,
    CorrelationFinding,
    Counterexample,
    CounterfactualScenario,
    ExplorationBudget,
    ExplorationResult,
    Finding,
    Hypothesis,
    LabSubmission,
    LabSubmissionResponse,
    StrategyManifest,
)

__all__ = [
    "AlgorithmicStrategy",
    "CandidateModelPackage",
    "Counterexample",
    "CounterexampleFinder",
    "CounterfactualScenario",
    "CounterfactualGenerator",
    "CorrelationFinding",
    "DataReleaseManager",
    "ExplorationBudget",
    "ExplorationResult",
    "ExplorationStrategy",
    "FailureAnalyzer",
    "Finding",
    "Hypothesis",
    "HypothesisGenerator",
    "LabExplorer",
    "LabSubmission",
    "LabSubmissionResponse",
    "Sandbox",
    "StrategyManifest",
    "SubmissionChain",
]
