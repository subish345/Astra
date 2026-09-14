"""Core data structures and state definitions for ASTRA-EA procedure management.

Defines step candidates, step evaluations, procedure status enumerations,
and traceable state snapshots.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class StepMatchStatus(str, Enum):
    """Evaluation result for an activity against candidate experiment steps."""
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    UNCERTAIN = "UNCERTAIN"
    NOT_MATCHED = "NOT_MATCHED"
    UNEXPECTED_CANDIDATE = "UNEXPECTED_CANDIDATE"


class ProcedureStatus(str, Enum):
    """Lifecycle state of the autonomous experiment procedure monitor."""
    READY = "READY"
    MONITORING = "MONITORING"
    CANDIDATE = "CANDIDATE"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    UNCERTAIN = "UNCERTAIN"
    NEXT_STEP = "NEXT_STEP"
    COMPLETED = "COMPLETED"


class ProcedureProgressEvent(str, Enum):
    """Discrete procedure state transition events emitted for assurance logging."""
    STEP_CANDIDATE_FOUND = "StepCandidateFound"
    STEP_VERIFICATION_STARTED = "StepVerificationStarted"
    STEP_VERIFIED = "StepVerified"
    STEP_UNCERTAIN = "StepUncertain"
    PROCEDURE_ADVANCED = "ProcedureAdvanced"
    PROCEDURE_COMPLETED = "ProcedureCompleted"


@dataclass
class StepCandidate:
    """Hypothesis that an observed activity corresponds to a configured procedure step."""
    step_id: str
    activity_type: str
    object_id: Optional[str]
    match_score: float
    status: StepMatchStatus = StepMatchStatus.CANDIDATE
    candidate_id: str = field(default_factory=lambda: f"CAND_{uuid.uuid4().hex[:8].upper()}")
    activity_id: str = ""
    actor: str = "ASTRONAUT"
    timestamp_start: float = 0.0
    timestamp_end: float = 0.0
    match_details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "step_id": self.step_id,
            "activity_type": self.activity_type,
            "object_id": self.object_id,
            "match_score": round(self.match_score, 3),
            "status": self.status.value,
            "activity_id": self.activity_id,
            "actor": self.actor,
            "timestamp_start": round(self.timestamp_start, 3),
            "timestamp_end": round(self.timestamp_end, 3),
            "match_details": self.match_details,
            "metadata": self.metadata,
        }


@dataclass
class StepEvaluation:
    """Formal audit decision verifying or questioning completion of an experiment step."""
    experiment_id: str
    run_id: str
    step_id: str
    status: StepMatchStatus
    confidence: float
    evidence_bundle_id: str
    timestamp_start: float
    timestamp_end: float
    evaluation_id: str = field(default_factory=lambda: f"EVAL_{uuid.uuid4().hex[:8].upper()}")
    source_activity_ids: List[str] = field(default_factory=list)
    procedure_version: str = "1.0.0"
    model_version: str = "yolov8n-custom-0.1"
    software_version: str = "0.4.0"
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "experiment_id": self.experiment_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "status": self.status.value,
            "confidence": round(self.confidence, 3),
            "evidence_bundle_id": self.evidence_bundle_id,
            "timestamp_start": round(self.timestamp_start, 3),
            "timestamp_end": round(self.timestamp_end, 3),
            "source_activity_ids": self.source_activity_ids,
            "procedure_version": self.procedure_version,
            "model_version": self.model_version,
            "software_version": self.software_version,
            "reasons": self.reasons,
            "metadata": self.metadata,
        }


@dataclass
class ProcedureState:
    """Consolidated state snapshot of the active experiment procedure."""
    experiment_id: str
    run_id: str
    current_step: Optional[str] = None
    previous_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    candidate_step: Optional[str] = None
    uncertain_step: Optional[str] = None
    next_expected_step: Optional[str] = None
    next_allowed_steps: List[str] = field(default_factory=list)
    procedure_status: ProcedureStatus = ProcedureStatus.READY
    active_bundle_id: Optional[str] = None
    last_evaluation: Optional[StepEvaluation] = None
    timestamp: float = 0.0

    @property
    def status(self) -> ProcedureStatus:
        """Alias for procedure_status for UI worker compatibility."""
        return self.procedure_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "run_id": self.run_id,
            "current_step": self.current_step,
            "previous_step": self.previous_step,
            "completed_steps": list(self.completed_steps),
            "candidate_step": self.candidate_step,
            "uncertain_step": self.uncertain_step,
            "next_expected_step": self.next_expected_step,
            "next_allowed_steps": list(self.next_allowed_steps),
            "procedure_status": self.procedure_status.value,
            "active_bundle_id": self.active_bundle_id,
            "last_evaluation": self.last_evaluation.to_dict() if self.last_evaluation else None,
            "timestamp": round(self.timestamp, 3),
        }
