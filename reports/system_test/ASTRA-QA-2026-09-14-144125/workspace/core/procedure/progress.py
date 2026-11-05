"""Procedure Progress Manager (D4.04) for ASTRA-EA.

Maintains the procedure state machine, handles step transitions, enforces event deduplication,
prevents premature advancement on uncertain evidence, and detects procedure completion.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from core.activity.types import ActivityObservation
from core.evidence.types import EvidenceBundle
from core.procedure.evaluator import StepEvaluator
from core.procedure.matcher import ProcedureMatcher
from core.procedure.next_step import ExpectedNextStepEngine
from core.procedure.schema import ExperimentDefinition, ExperimentStep
from core.procedure.types import (
    ProcedureProgressEvent,
    ProcedureState,
    ProcedureStatus,
    StepCandidate,
    StepEvaluation,
    StepMatchStatus,
)

logger = logging.getLogger(__name__)


class ProcedureProgressManager:
    """Manages execution state, validation, and lifecycle transitions of an experiment procedure."""

    def __init__(
        self,
        procedure: ExperimentDefinition,
        run_id: str = "RUN_001",
        matcher: Optional[ProcedureMatcher] = None,
        evaluator: Optional[StepEvaluator] = None,
        next_step_engine: Optional[ExpectedNextStepEngine] = None,
        event_callback: Optional[Callable[[ProcedureProgressEvent, Dict[str, Any]], None]] = None,
    ):
        self.procedure = procedure
        self.run_id = run_id
        self.matcher = matcher or ProcedureMatcher()
        self.evaluator = evaluator or StepEvaluator()
        self.next_step_engine = next_step_engine or ExpectedNextStepEngine(procedure)
        self.event_callback = event_callback

        self._step_map: Dict[str, ExperimentStep] = {s.id: s for s in procedure.steps}

        # Lifecycle state
        self.completed_steps: List[str] = []
        self.current_step: Optional[str] = self.next_step_engine.get_initial_step()
        self.previous_step: Optional[str] = None
        self.candidate_step: Optional[str] = None
        self.uncertain_step: Optional[str] = None
        self.procedure_status: ProcedureStatus = ProcedureStatus.READY
        self.last_evaluation: Optional[StepEvaluation] = None
        self.active_bundle_id: Optional[str] = None
        self.last_timestamp: float = 0.0

        # Event deduplication: set of step IDs verified in this session
        self._verified_step_ids: set[str] = set()

    def update(
        self,
        activity: ActivityObservation,
        bundle: Optional[EvidenceBundle] = None,
        timestamp: Optional[float] = None,
    ) -> ProcedureState:
        """Process an incoming activity observation and optional evidence bundle."""
        current_time = timestamp if timestamp is not None else activity.end_time
        self.last_timestamp = current_time

        if self.procedure_status == ProcedureStatus.COMPLETED:
            return self.get_state()

        if self.procedure_status == ProcedureStatus.READY:
            self.procedure_status = ProcedureStatus.MONITORING

        # Resolve next allowed steps
        allowed_next = self.next_step_engine.get_next_allowed_steps(
            current_step_id=self.current_step,
            completed_steps=self.completed_steps,
        )

        # 1. Match activity against procedure steps
        candidates = self.matcher.match(
            activity=activity,
            procedure=self.procedure,
            current_step_id=self.current_step,
            completed_steps=self.completed_steps,
            next_allowed_steps=allowed_next,
        )

        if not candidates:
            # No candidate found; keep monitoring
            self.candidate_step = None
            return self.get_state()

        best_cand = candidates[0]
        self.candidate_step = best_cand.step_id
        self._emit(
            ProcedureProgressEvent.STEP_CANDIDATE_FOUND,
            {"step_id": best_cand.step_id, "score": best_cand.match_score, "activity": best_cand.activity_type},
        )

        # Future candidates remain observations; they cannot bypass the active step.
        if best_cand.step_id != self.current_step:
            self.procedure_status = ProcedureStatus.MONITORING
            return self.get_state()

        # 2. Check if candidate step is already verified (Deduplication)
        step_def = self._step_map.get(best_cand.step_id)
        if step_def and best_cand.step_id in self._verified_step_ids and not step_def.repeatable:
            # Already verified and not repeatable: ignore duplicate triggers
            logger.debug(f"Step {best_cand.step_id} already verified; ignoring duplicate trigger.")
            return self.get_state()

        # 3. If evidence bundle is provided, evaluate step
        if bundle is not None and step_def is not None:
            self.procedure_status = ProcedureStatus.VERIFYING
            self.active_bundle_id = bundle.bundle_id
            self._emit(
                ProcedureProgressEvent.STEP_VERIFICATION_STARTED,
                {"step_id": best_cand.step_id, "bundle_id": bundle.bundle_id},
            )

            evaluation = self.evaluator.evaluate_step(
                candidate=best_cand,
                bundle=bundle,
                step=step_def,
                experiment_id=self.procedure.experiment.id,
                run_id=self.run_id,
            )
            self.last_evaluation = evaluation

            if evaluation.status == StepMatchStatus.VERIFIED:
                self._handle_step_verified(step_def, evaluation)
            elif evaluation.status == StepMatchStatus.UNCERTAIN:
                self._handle_step_uncertain(step_def, evaluation)
            else:
                self.procedure_status = ProcedureStatus.MONITORING
        else:
            self.procedure_status = ProcedureStatus.CANDIDATE

        return self.get_state()

    def _handle_step_verified(self, step: ExperimentStep, evaluation: StepEvaluation) -> None:
        """Process successful verification of an experiment step."""
        step_id = step.id

        # Guard against duplicate advancement
        if step_id in self._verified_step_ids and not step.repeatable:
            return

        self._verified_step_ids.add(step_id)
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)

        self.uncertain_step = None
        self.previous_step = step_id
        self.procedure_status = ProcedureStatus.VERIFIED

        self._emit(
            ProcedureProgressEvent.STEP_VERIFIED,
            {"step_id": step_id, "confidence": evaluation.confidence},
        )

        # Advance current step
        next_step_id = self.next_step_engine.get_primary_expected_step(
            current_step_id=step_id,
            completed_steps=self.completed_steps,
        )

        if next_step_id:
            self.current_step = next_step_id
            self.procedure_status = ProcedureStatus.NEXT_STEP
            self._emit(
                ProcedureProgressEvent.PROCEDURE_ADVANCED,
                {"from_step": step_id, "to_step": next_step_id},
            )
        else:
            # Check if all required steps are completed
            all_required_completed = all(
                s.id in self.completed_steps for s in self.procedure.steps if not s.optional
            )
            if all_required_completed or not next_step_id:
                self.current_step = None
                self.procedure_status = ProcedureStatus.COMPLETED
                self._emit(
                    ProcedureProgressEvent.PROCEDURE_COMPLETED,
                    {"completed_steps": list(self.completed_steps)},
                )

    def _handle_step_uncertain(self, step: ExperimentStep, evaluation: StepEvaluation) -> None:
        """Process uncertain evaluation: flag without silently advancing."""
        self.uncertain_step = step.id
        self.procedure_status = ProcedureStatus.UNCERTAIN
        self._emit(
            ProcedureProgressEvent.STEP_UNCERTAIN,
            {"step_id": step.id, "reasons": evaluation.reasons, "confidence": evaluation.confidence},
        )

    def _emit(self, event: ProcedureProgressEvent, payload: Dict[str, Any]) -> None:
        if self.event_callback:
            try:
                self.event_callback(event, payload)
            except Exception as e:
                logger.error(f"Error in procedure event callback: {e}")

    def get_state(self) -> ProcedureState:
        """Return an immutable snapshot of current procedure state."""
        allowed_next = self.next_step_engine.get_next_allowed_steps(
            current_step_id=self.current_step,
            completed_steps=self.completed_steps,
        )
        primary_next = self.next_step_engine.get_primary_expected_step(
            current_step_id=self.current_step,
            completed_steps=self.completed_steps,
        )

        return ProcedureState(
            experiment_id=self.procedure.experiment.id,
            run_id=self.run_id,
            current_step=self.current_step,
            previous_step=self.previous_step,
            completed_steps=list(self.completed_steps),
            candidate_step=self.candidate_step,
            uncertain_step=self.uncertain_step,
            next_expected_step=primary_next,
            next_allowed_steps=allowed_next,
            procedure_status=self.procedure_status,
            active_bundle_id=self.active_bundle_id,
            last_evaluation=self.last_evaluation,
            timestamp=self.last_timestamp,
        )

    def reset(self) -> None:
        """Reset procedure manager to initial baseline state."""
        self.completed_steps.clear()
        self._verified_step_ids.clear()
        self.current_step = self.next_step_engine.get_initial_step()
        self.previous_step = None
        self.candidate_step = None
        self.uncertain_step = None
        self.procedure_status = ProcedureStatus.READY
        self.last_evaluation = None
        self.active_bundle_id = None
        self.last_timestamp = 0.0

    def is_completed(self) -> bool:
        """Return whether all required procedure steps have completed."""
        return self.procedure_status == ProcedureStatus.COMPLETED

    def advance(self, step_id: str) -> None:
        """Mark a step verified and advance the procedure state machine."""
        step = self._step_map.get(step_id)
        if step:
            now = time.time()
            evaluation = StepEvaluation(
                experiment_id=self.procedure.experiment.id,
                run_id=self.run_id,
                step_id=step_id,
                status=StepMatchStatus.VERIFIED,
                confidence=1.0,
                evidence_bundle_id=self.active_bundle_id or f"BUNDLE_{step_id}",
                timestamp_start=now - 0.5,
                timestamp_end=now,
                reasons=["Step verified by orchestrator"],
            )
            self._handle_step_verified(step, evaluation)
