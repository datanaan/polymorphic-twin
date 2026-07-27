"""DomainPack version tracking and inheritance compatibility.

Provides check_inheritance_compatibility() to verify that a child DomainPack
does not violate the constraints declared in its parent.
"""
from __future__ import annotations

from .types import ConstraintCard, DomainPack


def _get_all_constraint_cards(pack: DomainPack) -> list[ConstraintCard]:
    """Extract all constraint cards from a DomainPack as typed ConstraintCard models."""
    cards: list[ConstraintCard] = []
    constraint_cards = pack.constraint_cards

    for rigidity in ("absolute", "soft", "learnable"):
        for raw_card in constraint_cards.get(rigidity, []):
            try:
                cards.append(ConstraintCard.model_validate(raw_card))
            except Exception:
                continue

    return cards


def check_inheritance_compatibility(
    child: DomainPack,
    parent: DomainPack | None,
) -> list[str]:
    """Verify that a child DomainPack does not violate parent constraints.

    Checks:
    1. Child cannot relax parent's absolute constraints (unless allowed)
    2. Child cannot lower parent's criticality levels (unless allowed)
    3. Child constraint_ids that exist in parent must be at least as strict
    4. Child must declare all parent's safety_critical constraints

    Args:
        child: The child DomainPack.
        parent: The parent DomainPack (None means no parent to check against).

    Returns:
        List of warning/error messages. Empty list means compatible.
    """
    if parent is None:
        return []

    warnings: list[str] = []
    inheritance = child.inheritance_policy

    # Build maps of constraint cards by ID
    parent_cards: dict[str, ConstraintCard] = {}
    for card in _get_all_constraint_cards(parent):
        parent_cards[card.constraint_id] = card

    child_cards: dict[str, ConstraintCard] = {}
    for card in _get_all_constraint_cards(child):
        child_cards[card.constraint_id] = card

    # ── 1. Check that all parent safety_critical constraints are present ──
    parent_safety_ids = {
        cid for cid, card in parent_cards.items()
        if card.scenario_criticality == "safety_critical"
    }
    child_ids = set(child_cards.keys())
    missing_safety = parent_safety_ids - child_ids
    if missing_safety:
        warnings.append(
            f"Child is missing parent safety_critical constraints: {sorted(missing_safety)}"
        )

    # ── 2. Check criticality lowering ──
    if not inheritance.can_lower_parent_criticality:
        criticality_order = {
            "safety_critical": 4,
            "identity_critical": 3,
            "operational": 2,
            "informational": 1,
        }
        for cid, parent_card in parent_cards.items():
            if cid not in child_cards:
                continue
            child_card = child_cards[cid]
            parent_level = criticality_order.get(parent_card.scenario_criticality, 0)
            child_level = criticality_order.get(child_card.scenario_criticality, 0)
            if child_level < parent_level:
                warnings.append(
                    f"Constraint '{cid}' lowers criticality from "
                    f"{parent_card.scenario_criticality} to {child_card.scenario_criticality}"
                )

    # ── 3. Check absolute constraint relaxation ──
    if not inheritance.can_relax_parent_absolute_constraints:
        for cid, _parent_card_unused in parent_cards.items():
            if cid not in child_cards:
                continue
            child_card = child_cards[cid]
            # If parent is absolute, child should also be absolute
            # (Check by looking at the raw constraint_cards structure)
            parent_absolute_ids = {
                card.constraint_id
                for card in _get_all_constraint_cards_from_rigidity(parent, "absolute")
            }
            child_in_soft = cid in {
                card.constraint_id
                for card in _get_all_constraint_cards_from_rigidity(child, "soft")
            }
            child_in_learnable = cid in {
                card.constraint_id
                for card in _get_all_constraint_cards_from_rigidity(child, "learnable")
            }
            if cid in parent_absolute_ids and (child_in_soft or child_in_learnable):
                warnings.append(
                    f"Constraint '{cid}' relaxes parent absolute rigidity to "
                    f"{'soft' if child_in_soft else 'learnable'}"
                )

    return warnings


def _get_all_constraint_cards_from_rigidity(
    pack: DomainPack, rigidity: str
) -> list[ConstraintCard]:
    """Extract constraint cards of a specific rigidity from a DomainPack."""
    cards: list[ConstraintCard] = []
    for raw_card in pack.constraint_cards.get(rigidity, []):
        try:
            cards.append(ConstraintCard.model_validate(raw_card))
        except Exception:
            continue
    return cards
