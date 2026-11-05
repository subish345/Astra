"""Expected Next Step Engine (D4.05) for ASTRA-EA.

Determines valid and expected procedural transitions based on graph topology,
branch conditions, and optional step resolution, avoiding simplistic sequential hardcoding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.procedure.schema import ExperimentDefinition, ExperimentStep, TransitionRule


class ExpectedNextStepEngine:
    """Graph-based transition resolver for experiment procedures."""

    def __init__(self, procedure: ExperimentDefinition):
        self.procedure = procedure
        self._step_map: Dict[str, ExperimentStep] = {s.id: s for s in procedure.steps}
        self._sorted_steps: List[ExperimentStep] = sorted(procedure.steps, key=lambda s: s.sequence)

    def get_initial_step(self) -> Optional[str]:
        """Return the first step ID in the procedure."""
        return self._sorted_steps[0].id if self._sorted_steps else None

    def get_next_allowed_steps(
        self,
        current_step_id: Optional[str],
        completed_steps: Optional[List[str]] = None,
        runtime_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Resolve all permissible next step IDs from the current position in the procedure graph."""
        completed_steps = completed_steps or []
        runtime_conditions = runtime_conditions or {}

        if not current_step_id:
            init = self.get_initial_step()
            return [init] if init else []

        current_step = self._step_map.get(current_step_id)
        if not current_step:
            return []

        allowed: List[str] = []

        # 1. Check step-level transitions attribute
        transitions = current_step.transitions
        if transitions is None and self.procedure.transitions and current_step_id in self.procedure.transitions:
            transitions = self.procedure.transitions[current_step_id]

        if transitions is not None:
            if isinstance(transitions, list):
                for item in transitions:
                    if isinstance(item, str) and item in self._step_map:
                        allowed.append(item)
                    elif isinstance(item, dict):
                        target = item.get("next")
                        cond = item.get("condition")
                        if not cond or runtime_conditions.get(cond, False):
                            if isinstance(target, str) and target in self._step_map:
                                allowed.append(target)
                            elif isinstance(target, list):
                                allowed.extend([t for t in target if t in self._step_map])
            elif isinstance(transitions, dict):
                next_val = transitions.get("next", [])
                if isinstance(next_val, list):
                    allowed.extend([t for t in next_val if t in self._step_map])
                elif isinstance(next_val, str) and next_val in self._step_map:
                    allowed.append(next_val)
            elif isinstance(transitions, TransitionRule):
                allowed.extend([t for t in transitions.next if t in self._step_map])

        # 2. Fallback to sequence order if no explicit transition graph rule was configured
        if transitions is None and not allowed:
            seq = current_step.sequence
            subsequent = [s for s in self._sorted_steps if s.sequence > seq]
            if subsequent:
                # Add immediate next step
                allowed.append(subsequent[0].id)
                # If immediate next is optional, also allow skipping to the step after it
                if subsequent[0].optional and len(subsequent) > 1:
                    allowed.append(subsequent[1].id)

        # 3. If repeatable, current step is also allowed
        if current_step.repeatable and current_step.id not in allowed:
            allowed.append(current_step.id)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for s in allowed:
            if s not in seen:
                seen.add(s)
                deduped.append(s)

        return deduped

    def get_primary_expected_step(
        self,
        current_step_id: Optional[str],
        completed_steps: Optional[List[str]] = None,
        runtime_conditions: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Return the primary (most canonical) next step expected."""
        allowed = self.get_next_allowed_steps(
            current_step_id=current_step_id,
            completed_steps=completed_steps,
            runtime_conditions=runtime_conditions,
        )
        return allowed[0] if allowed else None

    def is_valid_transition(
        self,
        from_step_id: Optional[str],
        to_step_id: str,
        completed_steps: Optional[List[str]] = None,
        runtime_conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Verify whether moving from from_step_id to to_step_id satisfies procedural constraints."""
        allowed = self.get_next_allowed_steps(
            current_step_id=from_step_id,
            completed_steps=completed_steps,
            runtime_conditions=runtime_conditions,
        )
        return to_step_id in allowed
