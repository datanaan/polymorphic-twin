"""Core constraint evaluation rules.

Exports the evaluator (four-state logic + domain_of_validity),
combinators (AND / OR / weighted / priority), and the built-in
validation registry.
"""

from polytwin.core.rules.combinator import combine
from polytwin.core.rules.evaluator import evaluate_constraint, evaluate_domain_of_validity
from polytwin.core.rules.registry import get_validator, register_validator

__all__ = [
    "combine",
    "evaluate_constraint",
    "evaluate_domain_of_validity",
    "get_validator",
    "register_validator",
]
