# ==============================================================================
# ASTRA-EA Tri-State Assurance Engine
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Tri-State Assurance Engine evaluating VERIFIED, UNCERTAIN, and DEVIATION states.

Enforces viewpoint invariance, ensuring physical actions produce identical semantic
assurance decisions regardless of whether the camera is positioned at VIEW_LEFT or VIEW_RIGHT.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set

from core.activity.types import ActivityObservation
from core.assurance.interface import AssuranceEngine
from core.assurance.types import AssuranceDecision
from core.camera.profile import CameraProfile, get_camera_profile
from core.common.logging import get_logger
from core.evidence.types import EvidenceBundle
from core.mission.events import DecisionType, DeviationReason
from core.procedure.schema import ExperimentProcedure, ExperimentStep

logger = get_logger("assurance_engine")


class TriStateAssuranceEngine(AssuranceEngine):
    """Evaluates procedure compliance against multimodal evidence and activity events.

    Guarantees:
    1. Camera viewpoint is an observation condition, not an experiment state.
    2. Occlusion, ambient dropouts, and low visibility produce UNCERTAIN, never false DEVIATION.
    3. Active deviations (WRONG_OBJECT, SKIPPED_STEP, etc.) are strictly classified and accompanied
       by contextual recovery guidance.
    """

    def __init__(
        self,
        default_camera_profile: str = "VIEW_LEFT",
        default_session_id: str = "SESSION_001",
        uncertain_threshold_ratio: float = 0.60,
        min_uncertain_confidence: float = 0.30,
        default_procedure_version: str = "1.0.0",
    ) -> None:
        self.default_camera_profile = default_camera_profile
        self.default_session_id = default_session_id
        self.uncertain_threshold_ratio = uncertain_threshold_ratio
        self.min_uncertain_confidence = min_uncertain_confidence
        self.default_procedure_version = default_procedure_version

    def evaluate_step(
        self,
        current_step: ExperimentStep,
        activity: ActivityObservation,
        evidence: EvidenceBundle,
        camera_profile: Optional[str | CameraProfile] = None,
        session_id: Optional[str] = None,
        procedure: Optional[ExperimentProcedure] = None,
        completed_step_ids: Optional[Set[str]] = None,
        elapsed_step_seconds: Optional[float] = None,
    ) -> AssuranceDecision:
        """Evaluate procedural satisfaction or deviation for the active step.

        Implements strict viewpoint invariance and tri-state decision logic.
        """
        # Resolve camera profile metadata
        if isinstance(camera_profile, CameraProfile):
            cam_prof_str = camera_profile.id
        elif camera_profile:
            cam_prof_str = str(camera_profile).upper()
        else:
            cam_prof_str = self.default_camera_profile

        active_session = session_id or self.default_session_id
        completed_ids = completed_step_ids or set()
        reasons: List[str] = []

        # ----------------------------------------------------------------------
        # 1. TIMEOUT EVALUATION
        # ----------------------------------------------------------------------
        if elapsed_step_seconds is not None and current_step.timeout_seconds > 0:
            if elapsed_step_seconds > current_step.timeout_seconds:
                return AssuranceDecision(
                    experiment_id=procedure.id if procedure else "DEMO_EXP_001",
                    step_id=current_step.id,
                    sequence=current_step.sequence,
                    decision=DecisionType.DEVIATION,
                    confidence=0.95,
                    deviation_reason=DeviationReason.TIMEOUT,
                    reason=f"Step execution timed out after {elapsed_step_seconds:.1f}s (limit: {current_step.timeout_seconds:.1f}s)",
                    reasons=[f"Step elapsed duration {elapsed_step_seconds:.1f}s exceeds limit {current_step.timeout_seconds:.1f}s"],
                    evidence_summary={"elapsed_seconds": elapsed_step_seconds, "timeout_seconds": current_step.timeout_seconds},
                    camera_profile=cam_prof_str,
                    session_id=active_session,
                    procedure_version=procedure.version if procedure else self.default_procedure_version,
                    severity=current_step.criticality.value if hasattr(current_step.criticality, "value") else str(current_step.criticality),
                    recommended_recovery=(
                        current_step.recovery.instruction if current_step.recovery else f"Re-initiate {current_step.name}"
                    ),
                )

        # ----------------------------------------------------------------------
        # 2. SKIPPED STEP / WRONG ORDER DETECTION
        # ----------------------------------------------------------------------
        if procedure and current_step.id not in completed_ids:
            matching_future_step = self._detect_premature_future_step(activity, evidence, procedure, current_step, completed_ids)
            if matching_future_step:
                rec_text = f"Halt current action. Return to and complete {current_step.name} first."
                return AssuranceDecision(
                    experiment_id=procedure.id,
                    step_id=current_step.id,
                    sequence=current_step.sequence,
                    decision=DecisionType.DEVIATION,
                    confidence=0.88,
                    deviation_reason=DeviationReason.SKIPPED_STEP,
                    reason=f"Skipped step: detected actions for {matching_future_step.name} before completing {current_step.name}",
                    reasons=[
                        f"Premature execution of {matching_future_step.id} ({matching_future_step.name}) while {current_step.id} remains unverified"
                    ],
                    evidence_summary={"matching_step": matching_future_step.id, "current_step": current_step.id},
                    camera_profile=cam_prof_str,
                    session_id=active_session,
                    procedure_version=procedure.version,
                    severity=current_step.criticality.value if hasattr(current_step.criticality, "value") else str(current_step.criticality),
                    recommended_recovery=rec_text,
                )

        # ----------------------------------------------------------------------
        # 3. OBJECT MATCHING & WRONG OBJECT DETECTION
        # ----------------------------------------------------------------------
        observed_objects = self._extract_interacted_objects(activity, evidence)
        expected_objects_norm = [obj.strip().upper() for obj in current_step.expected_objects]

        if expected_objects_norm and observed_objects:
            unauthorized_objects = [
                obj for obj in observed_objects
                if obj not in expected_objects_norm and not self._is_permissible_auxiliary(obj, current_step)
            ]
            if unauthorized_objects:
                wrong_obj = unauthorized_objects[0]
                rec_text = (
                    f"Release {wrong_obj} and acquire {expected_objects_norm[0]}"
                    if expected_objects_norm
                    else "Discontinue unauthorized object interaction"
                )
                if current_step.recovery and current_step.recovery.instruction:
                    rec_text = current_step.recovery.instruction

                return AssuranceDecision(
                    experiment_id=procedure.id if procedure else "DEMO_EXP_001",
                    step_id=current_step.id,
                    sequence=current_step.sequence,
                    decision=DecisionType.DEVIATION,
                    confidence=round(min(0.95, activity.confidence + 0.1), 3),
                    deviation_reason=DeviationReason.WRONG_OBJECT,
                    reason=f"Wrong object detected: interacted with {wrong_obj}, expected {expected_objects_norm}",
                    reasons=[f"Observed unauthorized object {wrong_obj}; step requires {expected_objects_norm}"],
                    evidence_summary={"observed_objects": observed_objects, "expected_objects": expected_objects_norm},
                    camera_profile=cam_prof_str,
                    session_id=active_session,
                    procedure_version=procedure.version if procedure else self.default_procedure_version,
                    severity=current_step.criticality.value if hasattr(current_step.criticality, "value") else str(current_step.criticality),
                    recommended_recovery=rec_text,
                )

        # ----------------------------------------------------------------------
        # 4. UNEXPECTED ACTION DETECTION
        # ----------------------------------------------------------------------
        action_conflict, conflict_reason = self._check_action_conflict(activity, current_step)
        if action_conflict and activity.confidence >= 0.75:
            rec_text = (
                current_step.recovery.instruction
                if current_step.recovery
                else f"Perform expected action: {current_step.expected_actions[0] if current_step.expected_actions else current_step.name}"
            )
            return AssuranceDecision(
                experiment_id=procedure.id if procedure else "DEMO_EXP_001",
                step_id=current_step.id,
                sequence=current_step.sequence,
                decision=DecisionType.DEVIATION,
                confidence=round(activity.confidence, 3),
                deviation_reason=DeviationReason.UNEXPECTED_ACTION,
                reason=conflict_reason,
                reasons=[conflict_reason],
                evidence_summary={"activity_type": activity.activity_type, "expected_actions": current_step.expected_actions},
                camera_profile=cam_prof_str,
                session_id=active_session,
                procedure_version=procedure.version if procedure else self.default_procedure_version,
                severity=current_step.criticality.value if hasattr(current_step.criticality, "value") else str(current_step.criticality),
                recommended_recovery=rec_text,
            )

        # ----------------------------------------------------------------------
        # 5. MULTIMODAL EVIDENCE & COMPOSITE CONFIDENCE
        # ----------------------------------------------------------------------
        composite_conf = (evidence.evidence_score * 0.60) + (activity.confidence * 0.40)
        req_satisfied = evidence.required_satisfied
        missing_req = evidence.missing_required

        # Check for explicit occlusion or partial visibility in evidence metadata
        is_occluded = bool(
            evidence.metadata.get("occluded")
            or evidence.metadata.get("is_occluded")
            or activity.metadata.get("occluded")
        )

        # Step confidence threshold
        conf_satisfied = composite_conf >= current_step.min_confidence

        # ----------------------------------------------------------------------
        # 6. INCOMPLETE ACTION (ABANDONED STEP) vs UNCERTAIN
        # ----------------------------------------------------------------------
        was_abandoned = bool(activity.metadata.get("abandoned") or evidence.metadata.get("abandoned"))
        if was_abandoned:
            return AssuranceDecision(
                experiment_id=procedure.id if procedure else "DEMO_EXP_001",
                step_id=current_step.id,
                sequence=current_step.sequence,
                decision=DecisionType.DEVIATION,
                confidence=0.85,
                deviation_reason=DeviationReason.INCOMPLETE_ACTION,
                reason="Action was abandoned prematurely prior to stabilization/completion",
                reasons=["Premature abandonment of step action"],
                evidence_summary={"missing_required": missing_req},
                camera_profile=cam_prof_str,
                session_id=active_session,
                procedure_version=procedure.version if procedure else self.default_procedure_version,
                severity=current_step.criticality.value if hasattr(current_step.criticality, "value") else str(current_step.criticality),
                recommended_recovery=current_step.recovery.instruction if current_step.recovery else f"Re-attempt {current_step.name}",
            )

        # ----------------------------------------------------------------------
        # 7. TRI-STATE DECISION: VERIFIED vs UNCERTAIN
        # ----------------------------------------------------------------------
        # Verification requires all mandatory evidence, confidence threshold, and no active occlusion
        if req_satisfied and conf_satisfied and not is_occluded:
            return AssuranceDecision(
                experiment_id=procedure.id if procedure else "DEMO_EXP_001",
                step_id=current_step.id,
                sequence=current_step.sequence,
                decision=DecisionType.VERIFIED,
                confidence=round(composite_conf, 3),
                reason="Step criteria and multimodal evidence satisfied",
                reasons=["All required evidence verified", f"Composite confidence {composite_conf:.2f} >= {current_step.min_confidence:.2f}"],
                evidence_summary={
                    "evidence_score": evidence.evidence_score,
                    "activity_confidence": activity.confidence,
                    "verified_items": [k for k, v in evidence.items.items() if v.verified],
                },
                camera_profile=cam_prof_str,
                session_id=active_session,
                procedure_version=procedure.version if procedure else self.default_procedure_version,
                severity=current_step.criticality.value if hasattr(current_step.criticality, "value") else str(current_step.criticality),
            )

        # UNCERTAIN: If visibility is reduced, occlusion is present, or confidence is moderate
        # CRITICAL PRINCIPLE: Reduced visibility or viewpoint ambiguity NEVER generates false deviations.
        reason_msg = (
            f"Observation viewpoint ({cam_prof_str}) experienced partial occlusion"
            if is_occluded
            else f"Partial evidence from {cam_prof_str}; composite confidence {composite_conf:.2f} below threshold {current_step.min_confidence:.2f}"
        )
        return AssuranceDecision(
            experiment_id=procedure.id if procedure else "DEMO_EXP_001",
            step_id=current_step.id,
            sequence=current_step.sequence,
            decision=DecisionType.UNCERTAIN,
            confidence=round(composite_conf, 3),
            reason=reason_msg,
            reasons=[reason_msg, f"Missing evidence: {missing_req}" if missing_req else "Awaiting continuous confirmation"],
            evidence_summary={
                "is_occluded": is_occluded,
                "missing_required": missing_req,
                "composite_confidence": round(composite_conf, 3),
                "camera_profile": cam_prof_str,
            },
            camera_profile=cam_prof_str,
            session_id=active_session,
            procedure_version=procedure.version if procedure else self.default_procedure_version,
            severity=current_step.criticality.value if hasattr(current_step.criticality, "value") else str(current_step.criticality),
        )

    # --------------------------------------------------------------------------
    # Helper Inspection Methods
    # --------------------------------------------------------------------------
    def _extract_interacted_objects(self, activity: ActivityObservation, evidence: EvidenceBundle) -> List[str]:
        """Extract set of normalized object IDs involved in current observation."""
        objs: Set[str] = set()

        if activity.target_objects:
            for o in activity.target_objects:
                objs.add(o.strip().upper())

        for key, val in activity.metadata.items():
            if "object" in key.lower() and isinstance(val, str):
                objs.add(val.strip().upper())

        # Evidence checks
        for key, item in evidence.items.items():
            if item.verified:
                if item.object_id:
                    objs.add(item.object_id.strip().upper())
                details = getattr(item, "details", {})
                if isinstance(details, dict):
                    for mk, mv in details.items():
                        if "object" in mk.lower() and isinstance(mv, str):
                            objs.add(mv.strip().upper())

        return list(objs)

    def _is_permissible_auxiliary(self, obj_id: str, step: ExperimentStep) -> bool:
        """Allow experiment workstations, work surfaces, or containers if contextually appropriate."""
        obj_norm = obj_id.strip().upper()
        if step.destination:
            if step.destination.object and obj_norm == step.destination.object.strip().upper():
                return True
            if step.destination.zone and obj_norm == step.destination.zone.strip().upper():
                return True
        if obj_norm in ("WORK_SURFACE", "MAIN_BOX", "EXPERIMENT_STATION", "BENCH"):
            return True
        return False

    def _detect_premature_future_step(
        self,
        activity: ActivityObservation,
        evidence: EvidenceBundle,
        procedure: ExperimentProcedure,
        current_step: ExperimentStep,
        completed_ids: Set[str],
    ) -> Optional[ExperimentStep]:
        """Detect if activity matches an unexecuted step ahead in the procedure graph."""
        act_type = activity.activity_type.upper().strip()

        for step in procedure.steps:
            if step.sequence > current_step.sequence and step.id not in completed_ids:
                # Check if activity matches future step's expected actions
                step_actions = [a.upper().strip() for a in step.expected_actions]
                if act_type in step_actions or (step.action_sequence and act_type == step.action_sequence[-1].upper()):
                    # Also check if destination or object matches
                    target_objs = self._extract_interacted_objects(activity, evidence)
                    future_objs = [o.upper().strip() for o in step.expected_objects]
                    if not future_objs or any(o in future_objs for o in target_objs):
                        return step
        return None

    def _check_action_conflict(self, activity: ActivityObservation, step: ExperimentStep) -> tuple[bool, str]:
        """Check whether observed action primitive directly conflicts with expected actions."""
        if not step.expected_actions:
            return False, ""

        act_type = activity.activity_type.upper().strip()
        expected = [a.upper().strip() for a in step.expected_actions]

        # If action matches expected or is an allowable precursor, no conflict
        if act_type in expected:
            return False, ""
        if step.action_sequence and act_type in [a.upper().strip() for a in step.action_sequence]:
            return False, ""

        # Allow basic ambient activities like IDLE, APPROACH if approaching
        if act_type in ("IDLE", "STAND", "ASTRONAUT_APPROACH", "APPROACH") and any("APPROACH" in a for a in expected):
            return False, ""

        # Explicitly incompatible pairs or unauthorized primitives
        if any(a in ("RELEASE", "DETACH") for a in expected) and act_type in ("GRASP", "LIFT"):
            return True, f"Unexpected action {act_type}; expected release"
        if any(a in ("GRASP", "LIFT") for a in expected) and act_type in ("RELEASE", "DETACH"):
            return True, f"Unexpected action {act_type}; expected grasp"
        if act_type in ("POUR", "MIX", "PUSH", "PULL", "SHAKE", "PRESS", "DISCONNECT", "UNEXPECTED"):
            return True, f"Unexpected action primitive {act_type}; expected {expected}"

        return False, ""
