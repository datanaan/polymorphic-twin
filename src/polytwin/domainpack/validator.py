"""DomainPack validation logic.

Extracted from the M0 CLI validation script. Provides importable validation
functions that check DomainPack data dictionaries for structural correctness,
rigidity-criticality compatibility, and reference integrity.
"""
from __future__ import annotations


class ValidationError:
    """A single validation error with a path and message."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"[{self.path}] {self.message}"

    def __repr__(self) -> str:
        return f"ValidationError(path={self.path!r}, message={self.message!r})"


def validate_domainpack_data(data: dict, name: str = "<data>") -> list[ValidationError]:
    """Validate a DomainPack data dictionary.

    Performs the same checks as the M0 CLI script:
    1. Required top-level fields
    2. Rigidity-criticality compatibility
    3. Reference integrity (constraint cards reference defined state variables)
    4. Safe fallback target_state
    5. Human roles role_id
    6. Action templates action_type_id

    Args:
        data: The parsed DomainPack dictionary.
        name: A name for error path prefixes (e.g., filename).

    Returns:
        List of ValidationError objects. Empty list means valid.
    """
    errors: list[ValidationError] = []

    if not isinstance(data, dict):
        return [ValidationError(name, "Top-level must be a mapping")]

    # ── 1. Required top-level fields ──
    required_fields = [
        "domain_id", "domain_name", "domain_version",
        "state_semantics_template", "constraint_cards",
        "safe_fallback", "action_templates", "human_roles",
    ]
    for field in required_fields:
        if field not in data:
            errors.append(ValidationError(name, f"Missing required field: {field}"))

    if errors:
        return errors  # stop here if basic structure is broken

    # ── 2. Collect defined state variable names ──
    defined_vars: set[str] = set()
    for var in data.get("state_semantics_template", {}).get("variables", []):
        if "name" in var:
            defined_vars.add(var["name"])

    # ── 3. Rigidity-criticality compatibility check ──
    constraint_cards = data.get("constraint_cards", {})

    # Check absolute constraints
    for i, card in enumerate(constraint_cards.get("absolute", [])):
        cid = card.get("constraint_id", f"absolute[{i}]")
        criticality = card.get("scenario_criticality", "")
        if criticality not in ("safety_critical", "identity_critical", "operational", "informational"):
            errors.append(ValidationError(
                f"{name}:constraint_cards.absolute.{cid}",
                f"Invalid scenario_criticality: {criticality}",
            ))

    # Check soft constraints — must NOT be safety_critical
    for i, card in enumerate(constraint_cards.get("soft", [])):
        cid = card.get("constraint_id", f"soft[{i}]")
        criticality = card.get("scenario_criticality", "")
        if criticality in ("safety_critical",):
            errors.append(ValidationError(
                f"{name}:constraint_cards.soft.{cid}",
                f"Rigidity-criticality violation: soft constraint has {criticality} criticality. "
                f"safety_critical constraints must be absolute.",
            ))

    # Check learnable constraints — must NOT be safety_critical; identity_critical needs audit
    for i, card in enumerate(constraint_cards.get("learnable", [])):
        cid = card.get("constraint_id", f"learnable[{i}]")
        criticality = card.get("scenario_criticality", "")
        if criticality == "safety_critical":
            errors.append(ValidationError(
                f"{name}:constraint_cards.learnable.{cid}",
                "Rigidity-criticality violation: learnable constraint has safety_critical criticality. "
                "safety_critical constraints must be absolute.",
            ))
        if criticality == "identity_critical" and not card.get("audit_config"):
            errors.append(ValidationError(
                f"{name}:constraint_cards.learnable.{cid}",
                "identity_critical + learnable requires audit_config",
            ))

    # ── 4. Reference integrity: domain_of_validity references defined variables ──
    all_cards = (
        constraint_cards.get("absolute", [])
        + constraint_cards.get("soft", [])
        + constraint_cards.get("learnable", [])
    )
    for card in all_cards:
        cid = card.get("constraint_id", "unknown")
        dov = card.get("domain_of_validity", {})
        for cond in dov.get("conditions", []):
            cond_type = cond.get("type", "")
            if cond_type in ("state_range", "state_enum"):
                var_name = cond.get("variable", "")
                if var_name and var_name not in defined_vars:
                    errors.append(ValidationError(
                        f"{name}:constraint_cards.{cid}.domain_of_validity",
                        f"References undefined state variable: {var_name}",
                    ))

        # Also check validation config references
        validation = card.get("validation", {})
        config = validation.get("config", {})
        var_name = config.get("variable", "")
        if var_name and var_name not in defined_vars:
            errors.append(ValidationError(
                f"{name}:constraint_cards.{cid}.validation",
                f"References undefined state variable: {var_name}",
            ))

    # ── 5. Safe fallback must have target_state ──
    fallback = data.get("safe_fallback", {})
    if not fallback.get("target_state"):
        errors.append(ValidationError(
            f"{name}:safe_fallback",
            "Missing target_state in safe_fallback",
        ))

    # ── 6. Human roles must have role_id ──
    for i, role in enumerate(data.get("human_roles", [])):
        if not role.get("role_id"):
            errors.append(ValidationError(
                f"{name}:human_roles[{i}]",
                "Missing role_id",
            ))

    # ── 7. Action templates reference check ──
    for group in ("immediate_action_types", "conditional_action_types", "forbidden_action_types"):
        for i, action in enumerate(data.get("action_templates", {}).get(group, [])):
            if not action.get("action_type_id"):
                errors.append(ValidationError(
                    f"{name}:action_templates.{group}[{i}]",
                    "Missing action_type_id",
                ))

    return errors
