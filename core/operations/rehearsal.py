"""Mission Rehearsal Engine for ASTRA-EA (Phase 19, Section 47, 48, 49, 50, D19.17).

Executes end-to-end simulated missions (GOLDEN_MISSION) supporting REALTIME, ACCELERATED,
and STEPWISE speeds, completely isolated from live flight records.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.common.config import get_project_root


class RehearsalSpeed(str, Enum):
    """Execution pace for operational rehearsal (Section 48)."""
    REALTIME = "REALTIME"          # True 1:1 real-time pacing with operational pauses
    ACCELERATED = "ACCELERATED"    # High-speed synthetic clock for fast training sweeps
    STEPWISE = "STEPWISE"          # Pauses at each milestone awaiting explicit operator step input


@dataclass
class RehearsalStep:
    """Individual milestone step in a rehearsal scenario."""
    step_id: str
    phase: str
    description: str
    event_type: str
    severity: str
    simulated_delay_seconds: float
    payload: Dict[str, Any] = field(default_factory=dict)


class MissionRehearsalEngine:
    """Orchestrates operational mission rehearsals in an isolated simulation sandbox."""

    def __init__(
        self,
        scenario_name: str = "GOLDEN_MISSION",
        speed: RehearsalSpeed = RehearsalSpeed.ACCELERATED,
        project_root: Optional[Path] = None,
    ) -> None:
        self.scenario_name = scenario_name
        self.speed = speed
        self.root = project_root or get_project_root()
        self.current_step_index: int = 0
        self.is_completed: bool = False
        self.rehearsal_log: List[Dict[str, Any]] = []

        # Load predefined GOLDEN_MISSION sequence (Section 47)
        self.steps: List[RehearsalStep] = self._build_golden_mission()

    def _build_golden_mission(self) -> List[RehearsalStep]:
        return [
            RehearsalStep(
                step_id="REH_01_PREP",
                phase="PREPARATION",
                description="Pre-mission hardware & checklist verification",
                event_type="PRECHECK_COMPLETED",
                severity="INFO",
                simulated_delay_seconds=0.1,
                payload={"checklist_status": "ALL_ITEMS_SIGNED", "verdict": "READY"},
            ),
            RehearsalStep(
                step_id="REH_02_INIT",
                phase="INITIALIZATION",
                description="Subsystem clock initialization & camera sync",
                event_type="CLOCK_INITIALIZED",
                severity="INFO",
                simulated_delay_seconds=0.1,
                payload={"met_started": True},
            ),
            RehearsalStep(
                step_id="REH_03_START",
                phase="READY",
                description="Authorized mission start dispatch",
                event_type="EXPERIMENT_STARTED",
                severity="INFO",
                simulated_delay_seconds=0.1,
                payload={"experiment_id": "REHEARSAL_EXP_001", "total_steps": 4},
            ),
            RehearsalStep(
                step_id="REH_04_EXP_STEP1",
                phase="EXPERIMENT",
                description="Step 1: Approach Workstation & Stage Apparatus",
                event_type="STEP_VERIFIED",
                severity="INFO",
                simulated_delay_seconds=0.2,
                payload={"step_id": "STEP_01", "verified": True},
            ),
            RehearsalStep(
                step_id="REH_05_ANOMALY",
                phase="ANOMALY",
                description="Step 2: Inadvertent Wrong Apparatus Gripped (DEVIATION)",
                event_type="DEVIATION_DETECTED",
                severity="WARNING",
                simulated_delay_seconds=0.2,
                payload={
                    "step_id": "STEP_02",
                    "deviation_type": "WRONG_APPARATUS",
                    "expected": "Centrifuge Tube",
                    "observed": "Pipette Tip Box",
                    "recovery_instruction": "Return pipette box to rack; retrieve centrifuge tube.",
                },
            ),
            RehearsalStep(
                step_id="REH_06_RECOVERY",
                phase="RECOVERY",
                description="Operator follows recovery guidance; correct apparatus placed",
                event_type="RECOVERY_VERIFIED",
                severity="INFO",
                simulated_delay_seconds=0.2,
                payload={"step_id": "STEP_02", "recovery_confirmed": True},
            ),
            RehearsalStep(
                step_id="REH_07_EXP_STEP3",
                phase="EXPERIMENT",
                description="Step 3: Centrifuge vortexing completed nominally",
                event_type="STEP_VERIFIED",
                severity="INFO",
                simulated_delay_seconds=0.2,
                payload={"step_id": "STEP_03", "verified": True},
            ),
            RehearsalStep(
                step_id="REH_08_EXP_STEP4",
                phase="EXPERIMENT",
                description="Step 4: Final specimen deposition & sealing",
                event_type="STEP_VERIFIED",
                severity="INFO",
                simulated_delay_seconds=0.2,
                payload={"step_id": "STEP_04", "verified": True},
            ),
            RehearsalStep(
                step_id="REH_09_COMPLETE",
                phase="COMPLETION",
                description="Mission completed; all step assertions satisfied",
                event_type="EXPERIMENT_COMPLETED",
                severity="INFO",
                simulated_delay_seconds=0.1,
                payload={"status": "SUCCESS", "deviations_resolved": 1},
            ),
            RehearsalStep(
                step_id="REH_10_POST",
                phase="POST_MISSION",
                description="Post-mission audit report generation & archive",
                event_type="REPORT_GENERATED",
                severity="INFO",
                simulated_delay_seconds=0.1,
                payload={"report_hash": "sha256_mock_rehearsal"},
            ),
        ]

    def advance_step(self) -> Optional[Dict[str, Any]]:
        """Advance one step in STEPWISE mode (Section 49)."""
        if self.current_step_index >= len(self.steps):
            self.is_completed = True
            return None

        step = self.steps[self.current_step_index]
        self.current_step_index += 1

        entry = {
            "step_index": self.current_step_index,
            "step_id": step.step_id,
            "phase": step.phase,
            "description": step.description,
            "event_type": step.event_type,
            "severity": step.severity,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "payload": step.payload,
        }
        self.rehearsal_log.append(entry)

        if self.current_step_index >= len(self.steps):
            self.is_completed = True

        return entry

    def run_all(self, event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Execute full scenario run under configured speed (Section 48)."""
        t0 = time.perf_counter()
        while not self.is_completed:
            step = self.steps[self.current_step_index]
            if self.speed == RehearsalSpeed.REALTIME:
                time.sleep(step.simulated_delay_seconds)
            elif self.speed == RehearsalSpeed.ACCELERATED:
                # Accelerate 10x
                time.sleep(step.simulated_delay_seconds * 0.05)

            evt = self.advance_step()
            if evt and event_callback:
                event_callback(evt)

        duration = time.perf_counter() - t0
        summary = {
            "scenario": self.scenario_name,
            "speed": self.speed.value,
            "total_steps": len(self.steps),
            "executed_steps": len(self.rehearsal_log),
            "execution_duration_seconds": round(duration, 3),
            "status": "PASS",
            "log": self.rehearsal_log,
        }

        # Save isolated rehearsal report (Section 50: zero pollution of live records)
        out_dir = self.root / "reports" / "rehearsal"
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / f"rehearsal_{self.scenario_name.lower()}.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary
