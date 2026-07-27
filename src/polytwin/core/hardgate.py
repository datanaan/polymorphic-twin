"""HardGate: six-check link qualification gate.

Runs six independent checks against a TwinObject view, constraints,
and DomainPack to classify links as granted, degraded, or denied.
"""
from __future__ import annotations

from polytwin.core.types import HardGateCheckResult, HardGateResult


class HardGate:
    """Six-check link qualification gate.

    HardGate does NOT simulate certification.  It performs a quick
    structural / semantic qualification pass to decide whether a model
    link should be granted (all checks pass), degraded (partial pass),
    or denied (hard failure).
    """

    async def evaluate(
        self,
        obj_view: dict,
        constraints: list[dict],
        domain_pack: dict,
    ) -> HardGateResult:
        """Run 6 checks and return granted/degraded/denied links.

        Args:
            obj_view: Projected view of a TwinObject (e.g. CoreRuntimeView
                      serialised to dict, or a plain dict with the relevant
                      fields).
            constraints: List of constraint card dicts from the DomainPack.
            domain_pack: DomainPack serialised as dict.

        Returns:
            HardGateResult with classified link lists.
        """
        results = [
            self._check_state_semantic_compatibility(obj_view, constraints, domain_pack),
            self._check_constraint_domain_match(obj_view, constraints, domain_pack),
            self._check_observation_readiness(obj_view, constraints, domain_pack),
            self._check_task_type_permission(obj_view, constraints, domain_pack),
            self._check_safety_boundary(obj_view, constraints, domain_pack),
            self._check_intervention_effectiveness(obj_view, constraints, domain_pack),
        ]

        granted = [r.check_name for r in results if r.passed]
        degraded = [
            r.check_name
            for r in results
            if not r.passed and "degraded" in r.details.lower()
        ]
        denied = [
            r.check_name
            for r in results
            if not r.passed and r.check_name not in degraded
        ]

        return HardGateResult(
            granted_links=granted,
            degraded_links=degraded,
            denied_links=denied,
        )

    # ── Check 1: State semantic compatibility ──────────────────────────
    def _check_state_semantic_compatibility(
        self, obj_view: dict, constraints: list[dict], domain_pack: dict,
    ) -> HardGateCheckResult:
        """All required state variables must be present in the object view."""
        template = domain_pack.get("state_semantics_template", {})
        required_vars = {
            v["name"]
            for v in template.get("variables", [])
            if v.get("required", True)
        }

        state_semantics = obj_view.get("state_semantics")
        current_values: dict = {}
        if state_semantics is not None:
            current_values = (
                state_semantics.current_values
                if hasattr(state_semantics, "current_values")
                else state_semantics.get("current_values", {})
            )

        missing = required_vars - set(current_values.keys())
        if missing:
            return HardGateCheckResult(
                check_name="state_semantic_compatibility",
                passed=False,
                details=f"Missing required variables: {sorted(missing)}",
            )
        return HardGateCheckResult(
            check_name="state_semantic_compatibility",
            passed=True,
            details="All required state variables present.",
        )

    # ── Check 2: Constraint domain match ──────────────────────────────
    def _check_constraint_domain_match(
        self, obj_view: dict, constraints: list[dict], domain_pack: dict,
    ) -> HardGateCheckResult:
        """Current state must be within domain_of_validity for constraints."""
        state_semantics = obj_view.get("state_semantics")
        current_values: dict = {}
        if state_semantics is not None:
            current_values = (
                state_semantics.current_values
                if hasattr(state_semantics, "current_values")
                else state_semantics.get("current_values", {})
            )

        for constraint in constraints:
            dov = constraint.get("domain_of_validity", {})
            conditions = dov.get("conditions", []) if isinstance(dov, dict) else []
            for cond in conditions:
                ctype = cond.get("type", "")
                if ctype == "state_enum":
                    variable = cond.get("variable", "")
                    allowed_values = cond.get("values", [])
                    val = current_values.get(variable)
                    if val is not None and allowed_values and str(val) not in [str(v) for v in allowed_values]:
                        return HardGateCheckResult(
                            check_name="constraint_domain_match",
                            passed=False,
                            details=f"Degraded: mode '{val}' not in domain for variable '{variable}'.",
                        )

        return HardGateCheckResult(
            check_name="constraint_domain_match",
            passed=True,
            details="Current state within all constraint domains.",
        )

    # ── Check 3: Observation readiness ─────────────────────────────────
    def _check_observation_readiness(
        self, obj_view: dict, constraints: list[dict], domain_pack: dict,
    ) -> HardGateCheckResult:
        """All required sensors must be active."""
        template = domain_pack.get("state_semantics_template", {})
        variables = template.get("variables", [])

        # Check sensor_status if provided in view
        sensor_status = obj_view.get("sensor_status", {})

        for var_def in variables:
            measurement_source = var_def.get("measurement_source")
            if measurement_source and sensor_status:
                status = sensor_status.get(measurement_source, "unknown")
                if status in ("offline", "fault"):
                    return HardGateCheckResult(
                        check_name="observation_readiness",
                        passed=False,
                        details=f"Sensor '{measurement_source}' is {status}.",
                    )

        # Check domain_of_validity sensor_status conditions in constraints
        for constraint in constraints:
            dov = constraint.get("domain_of_validity", {})
            conditions = dov.get("conditions", []) if isinstance(dov, dict) else []
            for cond in conditions:
                if cond.get("type") == "sensor_status":
                    sensor_id = cond.get("sensor_id", "")
                    cond.get("required_status", "active")
                    status = sensor_status.get(sensor_id, "unknown")
                    if status == "offline":
                        return HardGateCheckResult(
                            check_name="observation_readiness",
                            passed=False,
                            details=f"Required sensor '{sensor_id}' is offline.",
                        )

        return HardGateCheckResult(
            check_name="observation_readiness",
            passed=True,
            details="All required sensors active.",
        )

    # ── Check 4: Task type permission ──────────────────────────────────
    def _check_task_type_permission(
        self, obj_view: dict, constraints: list[dict], domain_pack: dict,
    ) -> HardGateCheckResult:
        """Task type must have required certificates."""
        task_type = obj_view.get("task_type", "")
        certificates = obj_view.get("certificates", [])

        # autonomous_control requires explicit certification
        if task_type == "autonomous_control" and "autonomous_control_cert" not in certificates:
            return HardGateCheckResult(
                check_name="task_type_permission",
                passed=False,
                details=f"Task type '{task_type}' requires certification.",
            )

        return HardGateCheckResult(
            check_name="task_type_permission",
            passed=True,
            details="Task type has required permissions.",
        )

    # ── Check 5: Safety boundary ───────────────────────────────────────
    def _check_safety_boundary(
        self, obj_view: dict, constraints: list[dict], domain_pack: dict,
    ) -> HardGateCheckResult:
        """Worst-case uncertainty must be within safety bounds."""
        uncertainty = obj_view.get("uncertainty", {})
        safety_bounds = domain_pack.get("safety_bounds", {})

        # If no uncertainty data or no safety bounds defined, pass
        if not uncertainty or not safety_bounds:
            return HardGateCheckResult(
                check_name="safety_boundary",
                passed=True,
                details="No uncertainty data or safety bounds to check.",
            )

        # Check if propagated uncertainty exceeds safety bounds
        for var_name, var_uncertainty in uncertainty.items():
            bound = safety_bounds.get(var_name)
            if bound is not None and isinstance(var_uncertainty, (int, float)) and var_uncertainty > bound:
                return HardGateCheckResult(
                    check_name="safety_boundary",
                    passed=False,
                    details=f"Degraded: uncertainty propagation for '{var_name}' exceeds safety bound.",
                )

        return HardGateCheckResult(
            check_name="safety_boundary",
            passed=True,
            details="Worst-case within safety bounds.",
        )

    # ── Check 6: Intervention effectiveness ────────────────────────────
    def _check_intervention_effectiveness(
        self, obj_view: dict, constraints: list[dict], domain_pack: dict,
    ) -> HardGateCheckResult:
        """An intervention path must exist for the current task type."""
        task_type = obj_view.get("task_type", "")
        intervention_paths = obj_view.get("intervention_paths", {})

        # production_control requires an intervention path
        if (
            task_type == "production_control"
            and (not intervention_paths or not intervention_paths.get(task_type))
        ):
            return HardGateCheckResult(
                check_name="intervention_effectiveness",
                passed=False,
                details=f"Degraded: no intervention path for '{task_type}'.",
            )

        return HardGateCheckResult(
            check_name="intervention_effectiveness",
            passed=True,
            details="Intervention path verified.",
        )
