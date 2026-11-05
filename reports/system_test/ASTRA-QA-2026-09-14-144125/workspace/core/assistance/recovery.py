# ==============================================================================
# ASTRA-EA Closed-Loop Deviation Recovery State Machine
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Closed-loop recovery state machine for procedural deviations.

Implements the formal recovery loop:
DETECT -> EXPLAIN -> RECOMMEND -> OBSERVE -> VERIFY -> RESUME
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.activity.types import ActivityObservation
from core.assistance.interface import GuidanceEngine
from core.assistance.types import AssistantMessage
from core.assurance.types import AssuranceDecision
from core.common.logging import get_logger
from core.evidence.types import EvidenceBundle
from core.mission.events import AssistantPriority, DecisionType, DeviationReason
from core.procedure.schema import ExperimentStep

logger = get_logger("recovery_engine")


class RecoveryState(str, Enum):
    """Formal states in closed-loop deviation recovery."""
    IDLE = "IDLE"
    DETECTED = "DETECTED"
    EXPLAINING = "EXPLAINING"
    RECOMMENDING = "RECOMMENDING"
    OBSERVING = "OBSERVING"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    RESUMED = "RESUMED"


@dataclass
class RecoveryContext:
    """Active deviation context tracking corrective progression."""
    session_id: str
    step_id: str
    deviation_reason: DeviationReason
    explanation: str
    recommendation: str
    target_step_id: str
    detected_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    state: RecoveryState = RecoveryState.DETECTED
    attempts: int = 1
    verified_corrective_action: bool = False
    context_id: str = field(default_factory=lambda: f"REC_{uuid.uuid4().hex[:8].upper()}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "step_id": self.step_id,
            "deviation_reason": self.deviation_reason.value if hasattr(self.deviation_reason, "value") else str(self.deviation_reason),
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "target_step_id": self.target_step_id,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "state": self.state.value,
            "attempts": self.attempts,
            "verified_corrective_action": self.verified_corrective_action,
        }


class ClosedLoopRecoveryManager(GuidanceEngine):
    """Manages closed-loop recovery state machine and astronaut guidance."""

    def __init__(self) -> None:
        self._current_state: RecoveryState = RecoveryState.IDLE
        self._active_context: Optional[RecoveryContext] = None
        self._state_change_listeners: List[Callable[[RecoveryState, Optional[RecoveryContext]], None]] = []

    @property
    def current_state(self) -> RecoveryState:
        return self._current_state

    @property
    def active_context(self) -> Optional[RecoveryContext]:
        return self._active_context

    @property
    def is_recovering(self) -> bool:
        return self._current_state != RecoveryState.IDLE

    def add_state_listener(self, listener: Callable[[RecoveryState, Optional[RecoveryContext]], None]) -> None:
        self._state_change_listeners.append(listener)

    def _transition_to(self, new_state: RecoveryState) -> None:
        old_state = self._current_state
        self._current_state = new_state
        if self._active_context:
            self._active_context.state = new_state
        logger.info("Recovery transition: %s -> %s", old_state.value, new_state.value)
        for listener in self._state_change_listeners:
            try:
                listener(new_state, self._active_context)
            except Exception as e:
                logger.error("Error in recovery state listener: %s", e)

    def handle_decision(
        self,
        decision: AssuranceDecision,
        step: ExperimentStep,
    ) -> List[AssistantMessage]:
        """Process an assurance decision.

        If a DEVIATION is detected, kicks off DETECT -> EXPLAIN -> RECOMMEND -> OBSERVING
        and generates prioritized assistant messages for voice/HUD.
        """
        messages: List[AssistantMessage] = []

        if decision.decision != DecisionType.DEVIATION:
            # If in OBSERVING or RECOVERY_VERIFIED and we just got VERIFIED, finish recovery
            if self._current_state in (RecoveryState.OBSERVING, RecoveryState.RECOVERY_VERIFIED) and decision.is_verified:
                self.complete_recovery()
            return messages

        dev_reason = decision.deviation_reason or DeviationReason.UNEXPECTED_ACTION

        # 1. DETECTED
        self._transition_to(RecoveryState.DETECTED)

        # Build explanation & recommendation
        explanation = self._build_explanation(decision, step)
        recommendation = decision.recommended_recovery or self._build_recommendation(decision, step)
        target_step_id = step.recovery.target_step if step.recovery and step.recovery.target_step else step.id

        self._active_context = RecoveryContext(
            session_id=decision.session_id,
            step_id=step.id,
            deviation_reason=dev_reason,
            explanation=explanation,
            recommendation=recommendation,
            target_step_id=target_step_id,
            state=RecoveryState.DETECTED,
        )

        # 2. EXPLAINING
        self._transition_to(RecoveryState.EXPLAINING)
        explain_priority = (
            AssistantPriority.CRITICAL if step.criticality.value == "CRITICAL" else AssistantPriority.WARNING
        )
        messages.append(AssistantMessage(text=explanation, priority=explain_priority))

        # 3. RECOMMENDING
        self._transition_to(RecoveryState.RECOMMENDING)
        messages.append(AssistantMessage(text=recommendation, priority=AssistantPriority.GUIDANCE))

        # 4. Move to OBSERVING corrective action
        self._transition_to(RecoveryState.OBSERVING)

        return messages

    def observe_corrective_action(
        self,
        activity: ActivityObservation,
        evidence: EvidenceBundle,
        step: ExperimentStep,
    ) -> tuple[bool, Optional[AssistantMessage]]:
        """Evaluate incoming observations while in OBSERVING state.

        Returns (is_recovered, optional_completion_message).
        """
        if self._current_state != RecoveryState.OBSERVING or not self._active_context:
            return False, None

        ctx = self._active_context
        reason = ctx.deviation_reason

        recovered = False

        if reason == DeviationReason.WRONG_OBJECT:
            # Astronaut recovers if they released or detached the wrong object,
            # or ceased contact with it
            act_type = activity.activity_type.upper().strip()
            if act_type in ("RELEASE", "DETACH", "RETRACT") and activity.confidence >= step.min_confidence:
                recovered = True
            elif evidence.check_requirement("CONTACT_CLEARED"):
                recovered = True

        elif reason == DeviationReason.SKIPPED_STEP:
            # Astronaut returns to previous step or stops premature forward action
            act_type = activity.activity_type.upper().strip()
            if (act_type in ("APPROACH", "ASTRONAUT_APPROACH") and step.id == ctx.target_step_id
                    and evidence.required_satisfied and activity.confidence >= step.min_confidence):
                recovered = True

        elif reason == DeviationReason.INCOMPLETE_ACTION:
            # Astronaut resumes stabilizing or placement
            act_type = activity.activity_type.upper().strip()
            if act_type in ("PLACE", "STABILIZE", "HOLD", "RELEASE"):
                recovered = True

        elif reason in (DeviationReason.UNEXPECTED_ACTION, DeviationReason.TIMEOUT):
            act_type = activity.activity_type.upper().strip()
            if any(ea.upper() in act_type for ea in step.expected_actions):
                recovered = True

        if recovered:
            ctx.verified_corrective_action = True
            # 5. RECOVERY_VERIFIED
            self._transition_to(RecoveryState.RECOVERY_VERIFIED)
            msg = AssistantMessage(
                text=f"Correction verified. Resuming {step.name}.",
                priority=AssistantPriority.INFO,
            )
            return True, msg

        return False, None

    def complete_recovery(self) -> None:
        """Mark recovery complete, transition to RESUMED, then reset to IDLE."""
        if self._active_context:
            self._active_context.resolved_at = time.time()
        self._transition_to(RecoveryState.RESUMED)
        self._transition_to(RecoveryState.IDLE)
        self._active_context = None

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        self._current_state = RecoveryState.IDLE
        self._active_context = None

    # --------------------------------------------------------------------------
    # GuidanceEngine Interface Implementation
    # --------------------------------------------------------------------------
    def get_step_guidance(self, step: ExperimentStep) -> AssistantMessage:
        text = f"Step {step.sequence}: {step.name}. {step.description or ''}".strip()
        return AssistantMessage(text=text, priority=AssistantPriority.GUIDANCE)

    def get_deviation_guidance(self, decision: AssuranceDecision, step: ExperimentStep) -> AssistantMessage:
        rec = decision.recommended_recovery or self._build_recommendation(decision, step)
        return AssistantMessage(text=rec, priority=AssistantPriority.WARNING)

    # --------------------------------------------------------------------------
    # Internal explanation & recommendation formatters
    # --------------------------------------------------------------------------
    def _build_explanation(self, decision: AssuranceDecision, step: ExperimentStep) -> str:
        if decision.reason:
            return f"Deviation detected: {decision.reason}."
        if decision.deviation_reason == DeviationReason.WRONG_OBJECT:
            return f"Incorrect object manipulated during {step.name}."
        if decision.deviation_reason == DeviationReason.SKIPPED_STEP:
            return f"Step execution order skipped. Prior step {step.name} is incomplete."
        if decision.deviation_reason == DeviationReason.INCOMPLETE_ACTION:
            return f"Action for {step.name} was not fully completed."
        if decision.deviation_reason == DeviationReason.TIMEOUT:
            return f"Step {step.name} execution time limit exceeded."
        return f"Unexpected procedural deviation detected at {step.name}."

    def _build_recommendation(self, decision: AssuranceDecision, step: ExperimentStep) -> str:
        if step.recovery and step.recovery.instruction:
            return step.recovery.instruction
        if decision.deviation_reason == DeviationReason.WRONG_OBJECT:
            exp_obj = step.expected_objects[0] if step.expected_objects else "the required item"
            return f"Release current item and acquire {exp_obj}."
        if decision.deviation_reason == DeviationReason.SKIPPED_STEP:
            return f"Return to workstation and verify {step.name}."
        if decision.deviation_reason == DeviationReason.INCOMPLETE_ACTION:
            return f"Re-seat and stabilize specimen on work surface."
        if decision.deviation_reason == DeviationReason.TIMEOUT:
            return f"Check experiment status and re-attempt {step.name}."
        return f"Please halt action and follow protocol for {step.name}."

    def generate_recovery(self, decision: Any, step: Any) -> Optional[RecoveryContext]:
        """Generate structured recovery guidance context for an assurance deviation."""
        self.handle_decision(decision, step)
        return self._active_context


# Canonical alias for mission orchestrator
ClosedLoopRecoveryEngine = ClosedLoopRecoveryManager
