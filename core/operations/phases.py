"""Mission Lifecycle Phases and State Transitions for ASTRA-EA (Phase 19, Section 8).

Defines the formal state machine governing mission execution:
PREPARATION -> INITIALIZATION -> READY -> EXPERIMENT -> ANOMALY -> RECOVERY -> COMPLETION -> POST_MISSION
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class MissionPhase(str, Enum):
    """Authoritative mission lifecycle phases (Section 8)."""
    PREPARATION = "PREPARATION"
    INITIALIZATION = "INITIALIZATION"
    READY = "READY"
    EXPERIMENT = "EXPERIMENT"
    ANOMALY = "ANOMALY"
    RECOVERY = "RECOVERY"
    COMPLETION = "COMPLETION"
    POST_MISSION = "POST_MISSION"


@dataclass
class PhaseDefinition:
    """Specification of entry, exit, allowed actions, and required records for a phase."""
    phase: MissionPhase
    entry_conditions: List[str]
    allowed_actions: List[str]
    exit_conditions: List[str]
    required_records: List[str]


class MissionPhaseManager:
    """Manages mission phase state transitions, enforcing operational preconditions."""

    VALID_TRANSITIONS: Dict[MissionPhase, Set[MissionPhase]] = {
        MissionPhase.PREPARATION: {MissionPhase.INITIALIZATION},
        MissionPhase.INITIALIZATION: {MissionPhase.READY, MissionPhase.PREPARATION},
        MissionPhase.READY: {MissionPhase.EXPERIMENT, MissionPhase.INITIALIZATION, MissionPhase.PREPARATION},
        MissionPhase.EXPERIMENT: {MissionPhase.ANOMALY, MissionPhase.COMPLETION, MissionPhase.READY},
        MissionPhase.ANOMALY: {MissionPhase.RECOVERY, MissionPhase.COMPLETION},
        MissionPhase.RECOVERY: {MissionPhase.EXPERIMENT, MissionPhase.ANOMALY, MissionPhase.COMPLETION},
        MissionPhase.COMPLETION: {MissionPhase.POST_MISSION},
        MissionPhase.POST_MISSION: {MissionPhase.PREPARATION},
    }

    PHASE_DEFINITIONS: Dict[MissionPhase, PhaseDefinition] = {
        MissionPhase.PREPARATION: PhaseDefinition(
            phase=MissionPhase.PREPARATION,
            entry_conditions=["System power applied", "Configuration loaded"],
            allowed_actions=["Run precheck", "Inspect checklist", "Load procedure", "Verify hardware"],
            exit_conditions=["Pre-mission checklist items signed", "Procedure validated"],
            required_records=["pre_mission_checklist.json"],
        ),
        MissionPhase.INITIALIZATION: PhaseDefinition(
            phase=MissionPhase.INITIALIZATION,
            entry_conditions=["Precheck passed", "Authorized startup signal received"],
            allowed_actions=["Initialize camera", "Load model ONNX", "Check storage partitions", "Sync clocks"],
            exit_conditions=["Subsystems healthy", "Mission clock started", "Perception online"],
            required_records=["startup_configuration_report.json"],
        ),
        MissionPhase.READY: PhaseDefinition(
            phase=MissionPhase.READY,
            entry_conditions=["Initialization successful", "Zero critical subsystem faults"],
            allowed_actions=["Authorize experiment start", "Review experiment metadata", "Request status"],
            exit_conditions=["START_EXPERIMENT command received from authorized operator"],
            required_records=["ready_state_snapshot.json"],
        ),
        MissionPhase.EXPERIMENT: PhaseDefinition(
            phase=MissionPhase.EXPERIMENT,
            entry_conditions=["READY state verified", "Experiment run ID minted"],
            allowed_actions=["Execute procedure step", "Record video/telemetry", "Evaluate assurance", "Pause/Resume"],
            exit_conditions=["Final step verified (NOMINAL) OR Deviation detected (ANOMALY)"],
            required_records=["events.json", "timeline.json", "evidence_clips/"],
        ),
        MissionPhase.ANOMALY: PhaseDefinition(
            phase=MissionPhase.ANOMALY,
            entry_conditions=["Deviation triggered OR Subsystem failure detected"],
            allowed_actions=["Acknowledge alert", "Issue recovery guidance", "Inspect deviation evidence"],
            exit_conditions=["Recovery instructions dispatched and acknowledged"],
            required_records=["deviation_event.json", "alert_record.json"],
        ),
        MissionPhase.RECOVERY: PhaseDefinition(
            phase=MissionPhase.RECOVERY,
            entry_conditions=["Anomaly acknowledged", "Operator executing corrective guidance"],
            allowed_actions=["Verify corrective action", "Re-evaluate apparatus state", "Escalate if failed"],
            exit_conditions=["Corrective action verified (Return to EXPERIMENT) OR Unrecoverable (COMPLETION)"],
            required_records=["recovery_event.json"],
        ),
        MissionPhase.COMPLETION: PhaseDefinition(
            phase=MissionPhase.COMPLETION,
            entry_conditions=["All steps verified OR Early abort concluded"],
            allowed_actions=["Flush storage buffers", "Close video streams", "Finalize telemetry sequence"],
            exit_conditions=["All buffers flushed and persisted to disk"],
            required_records=["completion_summary.json"],
        ),
        MissionPhase.POST_MISSION: PhaseDefinition(
            phase=MissionPhase.POST_MISSION,
            entry_conditions=["Mission records finalized"],
            allowed_actions=["Export run bundle", "Generate mission report", "Review evidence", "Archive run"],
            exit_conditions=["Report signed and archived"],
            required_records=["report.json", "report.html", "manifest.json", "checksums.sha256"],
        ),
    }

    def __init__(self, initial_phase: MissionPhase = MissionPhase.PREPARATION) -> None:
        self.current_phase: MissionPhase = initial_phase
        self.phase_history: List[Dict[str, Any]] = [
            {
                "phase": initial_phase.value,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "reason": "Initial state",
            }
        ]

    def transition_to(self, target_phase: MissionPhase, reason: str = "") -> Tuple[bool, str]:
        """Attempt to transition to target mission phase."""
        if target_phase == self.current_phase:
            return True, f"Already in phase {target_phase.value}."

        allowed_targets = self.VALID_TRANSITIONS.get(self.current_phase, set())
        if target_phase not in allowed_targets:
            msg = (
                f"Invalid phase transition: Cannot transition from {self.current_phase.value} "
                f"to {target_phase.value}. Allowed: {[p.value for p in allowed_targets]}"
            )
            return False, msg

        old_phase = self.current_phase
        self.current_phase = target_phase
        self.phase_history.append({
            "phase": target_phase.value,
            "previous_phase": old_phase.value,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "reason": reason or f"Transition from {old_phase.value}",
        })
        return True, f"Successfully transitioned from {old_phase.value} to {target_phase.value}."

    def get_phase_info(self, phase: Optional[MissionPhase] = None) -> PhaseDefinition:
        """Get definition metadata for current or target phase."""
        target = phase or self.current_phase
        return self.PHASE_DEFINITIONS[target]
