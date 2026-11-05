# ==============================================================================
# ASTRA-EA Mission Console UI State Store
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Typed UI data store translating backend mission events into presentation state.

Follows the fundamental rule: The UI consumes typed state and does NOT make
procedural, assurance, deviation, or recovery decisions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.ui.theme import UIStatus


@dataclass
class ExperimentState:
    experiment_id: str = "DEMO_EXP_001"
    name: str = "Sample Material Handling & Container Verification"
    version: str = "1.0.0"
    total_steps: int = 4
    description: str = "Baseline demonstration procedure for container transfer and inspection."


@dataclass
class SessionState:
    run_id: str = "RUN_001"
    status: str = "READY"  # CREATED, INITIALIZING, READY, RUNNING, PAUSED, RECOVERY, COMPLETED, ABORTED, FAILED
    start_time: float = field(default_factory=time.time)
    elapsed_seconds: float = 0.0


@dataclass
class CurrentStepState:
    step_id: str = "STEP_01"
    step_number: int = 1
    step_name: str = "Approach Experiment Station"
    status: str = "WAITING"  # WAITING, IN_PROGRESS, VERIFIED, UNCERTAIN, DEVIATION
    time_in_step: float = 0.0
    expected_action: str = "APPROACH"
    target_object: str = "EXPERIMENT_STATION"


@dataclass
class NextActionState:
    action_text: str = "Approach the experiment station work surface"
    step_id: str = "STEP_01"
    is_completed: bool = False


@dataclass
class AssuranceState:
    decision: str = "NONE"  # NONE, VERIFIED, UNCERTAIN, DEVIATION
    confidence: float = 0.0
    reasons: List[str] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class DeviationState:
    is_active: bool = False
    deviation_type: str = "NONE"
    expected_obj: str = ""
    detected_obj: str = ""
    reason: str = ""
    recovery_instruction: str = ""


@dataclass
class RecoveryUIState:
    is_recovering: bool = False
    state_name: str = "IDLE"  # IDLE, DETECT, EXPLAIN, RECOMMEND, OBSERVE, VERIFY, RESUME
    instruction: str = ""
    verified: bool = False


@dataclass
class EvidenceItemState:
    evidence_type: str
    score: float
    is_satisfied: bool
    details: str
    timestamp: float
    source_frame: int = 0
    hand_id: Optional[str] = None
    object_id: Optional[str] = None


@dataclass
class TimelineEventState:
    timestamp_str: str
    event_type: str  # STEP, ASSURANCE, DEVIATION, RECOVERY, SYSTEM, UI
    title: str
    description: str
    severity: str = "INFO"  # INFO, SUCCESS, WARNING, DANGER


@dataclass
class HealthState:
    subsystems: Dict[str, str] = field(
        default_factory=lambda: {
            "Camera": "ONLINE",
            "Perception": "ACTIVE",
            "Procedure": "ACTIVE",
            "Assurance": "ACTIVE",
            "Voice": "ACTIVE",
            "Database": "ACTIVE",
            "Storage": "NORMAL",
            "Network": "OFFLINE",  # Air-gapped
        }
    )
    fps: float = 30.0
    latency_ms: float = 12.5
    cpu_pct: float = 18.0
    ram_mb: float = 450.0


@dataclass
class CameraState:
    profile: str = "VIEW_LEFT"
    source: str = "0"
    resolution: str = "1280x720"
    fps: float = 30.0
    status: str = "ONLINE"  # ONLINE, FAILED


@dataclass
class OverlayConfigState:
    show_pose: bool = True
    show_hands: bool = True
    show_objects: bool = True
    show_tracking: bool = True
    show_interaction: bool = True
    show_debug: bool = False


class MissionUIState:
    """Central presentation state container for the Mission Console."""

    def __init__(self) -> None:
        self.experiment = ExperimentState()
        self.session = SessionState()
        self.current_step = CurrentStepState()
        self.next_action = NextActionState()
        self.assurance = AssuranceState()
        self.deviation = DeviationState()
        self.recovery = RecoveryUIState()
        self.evidence_items: List[EvidenceItemState] = []
        self.timeline: List[TimelineEventState] = []
        self.health = HealthState()
        self.camera = CameraState()
        self.overlay = OverlayConfigState()

        # Step statuses for all steps in procedure: dict of step_id -> status string
        self.step_statuses: Dict[str, str] = {
            "STEP_01": "WAITING",
            "STEP_02": "WAITING",
            "STEP_03": "WAITING",
            "STEP_04": "WAITING",
        }

        # Operational flags
        self.offline_mode: bool = True
        self.is_demo_mode: bool = True

    def add_timeline_event(
        self,
        event_type: str,
        title: str,
        description: str = "",
        severity: str = "INFO",
        timestamp: Optional[float] = None,
    ) -> TimelineEventState:
        """Add a chronological entry to the mission timeline."""
        ts = timestamp if timestamp is not None else time.time()
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        ev = TimelineEventState(
            timestamp_str=time_str,
            event_type=event_type,
            title=title,
            description=description,
            severity=severity,
        )
        self.timeline.append(ev)
        return ev

    def apply_step_progress(
        self,
        current_step_id: Optional[str],
        next_step_id: Optional[str],
        completed_steps: List[str],
        status_name: str,
    ) -> None:
        """Update step progress states based on ProcedureProgressState."""
        for cid in completed_steps:
            self.step_statuses[cid] = "VERIFIED"

        if current_step_id:
            self.step_statuses[current_step_id] = "IN_PROGRESS"
            self.current_step.step_id = current_step_id

        if status_name == "COMPLETED":
            self.session.status = "COMPLETED"
            self.next_action.action_text = "EXPERIMENT COMPLETE"
            self.next_action.is_completed = True
        elif next_step_id:
            self.next_action.step_id = next_step_id

    def apply_assurance_decision(
        self,
        decision_type: str,
        confidence: float,
        reasons: List[str],
        step_id: Optional[str] = None,
        target_obj: Optional[str] = None,
    ) -> None:
        """Update assurance evaluation state."""
        self.assurance.decision = decision_type
        self.assurance.confidence = confidence
        self.assurance.reasons = list(reasons)
        self.assurance.timestamp = time.time()

        if decision_type == "VERIFIED":
            self.deviation.is_active = False
            self.recovery.is_recovering = False
            if step_id:
                self.step_statuses[step_id] = "VERIFIED"
        elif decision_type == "DEVIATION":
            self.deviation.is_active = True
            if step_id:
                self.step_statuses[step_id] = "DEVIATION"
        elif decision_type == "UNCERTAIN":
            if step_id and self.step_statuses.get(step_id) != "VERIFIED":
                self.step_statuses[step_id] = "UNCERTAIN"

    def apply_deviation(
        self,
        dev_type: str,
        expected_obj: str,
        detected_obj: str,
        reason: str,
        recovery_guidance: str,
    ) -> None:
        """Update deviation alert state."""
        self.deviation.is_active = True
        self.deviation.deviation_type = dev_type
        self.deviation.expected_obj = expected_obj
        self.deviation.detected_obj = detected_obj
        self.deviation.reason = reason
        self.deviation.recovery_instruction = recovery_guidance

        self.recovery.is_recovering = True
        self.recovery.state_name = "RECOMMEND"
        self.recovery.instruction = recovery_guidance

    def apply_recovery(self, state_name: str, instruction: str, verified: bool = False) -> None:
        """Update recovery lifecycle state."""
        self.recovery.state_name = state_name
        self.recovery.instruction = instruction
        self.recovery.verified = verified
        if verified:
            self.recovery.is_recovering = False
            self.deviation.is_active = False

    def clear_evidence(self) -> None:
        """Clear current evidence items."""
        self.evidence_items.clear()

    def add_evidence_item(
        self,
        evidence_type: str,
        score: float,
        is_satisfied: bool,
        details: str,
        source_frame: int = 0,
        hand_id: Optional[str] = None,
        object_id: Optional[str] = None,
    ) -> None:
        """Record an evidence item supporting the current step evaluation."""
        self.evidence_items.append(
            EvidenceItemState(
                evidence_type=evidence_type,
                score=score,
                is_satisfied=is_satisfied,
                details=details,
                timestamp=time.time(),
                source_frame=source_frame,
                hand_id=hand_id,
                object_id=object_id,
            )
        )
