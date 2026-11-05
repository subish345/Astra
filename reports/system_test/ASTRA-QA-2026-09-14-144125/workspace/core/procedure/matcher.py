"""Procedure Matcher (D4.01) for ASTRA-EA.

Maps observed human activities and interaction events to candidate experiment steps
defined in the configured ExperimentDefinition schema.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.activity.types import ActivityObservation
from core.interaction.types import InteractionEvent
from core.procedure.schema import ExperimentDefinition, ExperimentStep
from core.procedure.types import StepCandidate, StepMatchStatus


class ProcedureMatcher:
    """Evaluates incoming activity observations against procedure step definitions."""

    # Activity to ActionPrimitive mapping/aliases
    ACTIVITY_ACTION_MAP: Dict[str, List[str]] = {
        "APPROACH": ["APPROACH", "REACH"],
        "APPROACH_DESTINATION": ["APPROACH_DESTINATION", "APPROACH", "MOVE", "PLACE"],
        "TOUCH": ["TOUCH", "REACH"],
        "GRASP": ["GRASP", "HOLD", "TOUCH"],
        "LIFT": ["LIFT", "GRASP", "MOVE"],
        "HOLD": ["HOLD", "GRASP"],
        "MOVE": ["MOVE", "CARRY", "APPROACH_DESTINATION"],
        "PLACE": ["PLACE", "RELEASE", "APPROACH_DESTINATION"],
        "RELEASE": ["RELEASE", "PLACE"],
        "PICKUP": ["GRASP", "LIFT"],
        "MOVE_OBJECT": ["MOVE", "CARRY", "APPROACH_DESTINATION"],
        "PLACE_OBJECT": ["PLACE", "RELEASE", "APPROACH_DESTINATION"],
        "INSPECT_OBJECT": ["HOLD", "TOUCH"],
    }

    def __init__(
        self,
        min_match_threshold: float = 0.50,
        context_bonus_current: float = 0.20,
        context_bonus_next: float = 0.10,
    ):
        self.min_match_threshold = min_match_threshold
        self.context_bonus_current = context_bonus_current
        self.context_bonus_next = context_bonus_next

    def match(
        self,
        activity: ActivityObservation,
        procedure: ExperimentDefinition,
        current_step_id: Optional[str] = None,
        completed_steps: Optional[List[str]] = None,
        next_allowed_steps: Optional[List[str]] = None,
    ) -> List[StepCandidate]:
        """Evaluate an activity against all relevant procedure steps and return ranked candidates."""
        completed_steps = completed_steps or []
        candidates: List[StepCandidate] = []

        act_name_upper = activity.activity_name.upper().strip()
        target_obj = activity.target_object_id

        for step in procedure.steps:
            # If step is already completed and not repeatable, skip or heavily downweight
            if step.id in completed_steps and not step.repeatable:
                continue

            score, details = self._calculate_match_score(
                step=step,
                activity=activity,
                current_step_id=current_step_id,
                next_allowed_steps=next_allowed_steps,
            )

            if score >= self.min_match_threshold:
                cand = StepCandidate(
                    step_id=step.id,
                    activity_type=act_name_upper,
                    object_id=target_obj,
                    match_score=score,
                    status=StepMatchStatus.CANDIDATE,
                    activity_id=activity.activity_id,
                    actor=activity.actor,
                    timestamp_start=activity.start_time,
                    timestamp_end=activity.end_time,
                    match_details=details,
                )
                candidates.append(cand)

        # Sort descending by match_score
        candidates.sort(key=lambda c: c.match_score, reverse=True)
        return candidates

    def match_best(
        self,
        activity: ActivityObservation,
        procedure: ExperimentDefinition,
        current_step_id: Optional[str] = None,
        completed_steps: Optional[List[str]] = None,
        next_allowed_steps: Optional[List[str]] = None,
    ) -> Optional[StepCandidate]:
        """Return the highest scoring StepCandidate, or None if no step exceeds threshold."""
        candidates = self.match(
            activity=activity,
            procedure=procedure,
            current_step_id=current_step_id,
            completed_steps=completed_steps,
            next_allowed_steps=next_allowed_steps,
        )
        return candidates[0] if candidates else None

    def _calculate_match_score(
        self,
        step: ExperimentStep,
        activity: ActivityObservation,
        current_step_id: Optional[str],
        next_allowed_steps: Optional[List[str]],
    ) -> tuple[float, Dict[str, Any]]:
        """Compute explainable match score between an activity and a candidate step."""
        details: Dict[str, Any] = {}
        act_name_upper = activity.activity_name.upper().strip()
        target_obj = (activity.target_object_id or "").upper().strip()

        # 1. Action compatibility (0.0 to 1.0)
        action_score = 0.0
        expected_actions = [a.upper().strip() for a in step.expected_actions]
        if step.action_sequence:
            for act in step.action_sequence:
                act_norm = act.upper().strip()
                if act_norm not in expected_actions:
                    expected_actions.append(act_norm)

        compatible_actions = self.ACTIVITY_ACTION_MAP.get(act_name_upper, [act_name_upper])

        if act_name_upper in expected_actions:
            action_score = 1.0
        elif any(ca in expected_actions for ca in compatible_actions):
            action_score = 0.85
        elif not expected_actions:
            action_score = 0.50  # Step doesn't constrain action
        details["action_match"] = action_score

        # 2. Object identity match (0.0 to 1.0)
        object_score = 0.0
        expected_objects = [o.upper().strip() for o in step.expected_objects]
        if not expected_objects:
            object_score = 0.80  # Step doesn't require specific object
        elif target_obj and target_obj in expected_objects:
            object_score = 1.0
        elif target_obj and any(target_obj in eo or eo in target_obj for eo in expected_objects):
            object_score = 0.90
        elif not target_obj:
            object_score = 0.30  # Object missing from activity observation
        else:
            object_score = 0.0  # Explicit object mismatch!
        details["object_match"] = object_score

        # If either action or object is a hard mismatch (0.0), step match fails
        if action_score == 0.0 or (expected_objects and object_score == 0.0):
            details["hard_mismatch"] = True
            return 0.0, details

        # 3. Base observation confidence
        obs_conf = min(1.0, max(0.0, activity.confidence))
        details["observation_confidence"] = obs_conf

        # 4. Procedure Context Bonus
        context_bonus = 0.0
        if current_step_id and step.id == current_step_id:
            context_bonus = self.context_bonus_current
            details["context"] = "CURRENT_STEP"
        elif next_allowed_steps and step.id in next_allowed_steps:
            context_bonus = self.context_bonus_next
            details["context"] = "NEXT_ALLOWED_STEP"
        else:
            details["context"] = "OTHER_STEP"
        details["context_bonus"] = context_bonus

        # Weighted combination: 45% action, 35% object, 20% observation conf + context bonus
        raw_score = (action_score * 0.45) + (object_score * 0.35) + (obs_conf * 0.20) + context_bonus
        final_score = min(1.0, max(0.0, raw_score))
        details["final_score"] = round(final_score, 3)

        return final_score, details
