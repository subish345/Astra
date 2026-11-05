"""Mission State Persistence, Restart Handling, and Crash Recovery (Phase 18).

In accordance with Section 34, 35, 36 & 37:
- Atomically persists critical mission state (experiment, run, step, procedure, assurance, recovery, sequence).
- Implements restart policy: Default REVIEW_REQUIRED (prohibits blind automatic resumption).
- Provides power loss and crash recovery verification.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("mission_persistence")


class RestartPolicy(str, enum.Enum):
    """Action taken upon detecting an incomplete run after process termination (Section 35)."""
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SAFE_RESUME = "SAFE_RESUME"
    START_NEW_RUN = "START_NEW_RUN"


@dataclass
class MissionStateRecord:
    experiment_id: str
    run_id: str
    current_step_id: str
    procedure_state: str  # INITIALIZING, RUNNING, PAUSED, COMPLETED, ABORTED
    assurance_state: str  # VERIFIED, UNCERTAIN, DEVIATION, PAUSED
    recovery_state: str   # NONE, IN_PROGRESS, RECOVERED, FAILED
    last_event_sequence: int
    timestamp_utc: str
    is_completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MissionStateManager:
    """Handles atomic state persistence and restart anomaly recovery (D18.11 & D18.12)."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        restart_policy: RestartPolicy = RestartPolicy.REVIEW_REQUIRED,
    ) -> None:
        self.storage_dir = storage_dir or Path("flight_data/mission")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.storage_dir / "active_mission_state.json"
        self.backup_file = self.storage_dir / "active_mission_state.json.bak"
        self.restart_policy = restart_policy

    def persist_state(self, state: MissionStateRecord) -> bool:
        """Atomically persist active mission state to disk."""
        temp_file = self.storage_dir / "active_mission_state.json.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2)
            # Atomic rename / replace
            if self.state_file.exists():
                shutil.copy2(self.state_file, self.backup_file)
            temp_file.replace(self.state_file)
            return True
        except Exception as e:
            logger.error("Failed to persist mission state: %s", e)
            return False

    def load_persisted_state(self) -> Optional[MissionStateRecord]:
        """Load active state if file exists and is valid."""
        target = self.state_file if self.state_file.exists() else self.backup_file
        if not target.exists():
            return None
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            return MissionStateRecord(**data)
        except Exception as e:
            logger.error("Corrupted mission state file: %s", e)
            return None

    def evaluate_startup_state(self) -> Dict[str, Any]:
        """Audit previous state on boot. Detects crashes or power interruptions (Section 35 & 36)."""
        prev = self.load_persisted_state()
        if prev is None:
            return {
                "restart_status": "CLEAN_BOOT",
                "incomplete_run_detected": False,
                "action": "READY_FOR_NEW_EXPERIMENT",
                "previous_state": None,
            }

        if prev.is_completed or prev.procedure_state in ("COMPLETED", "ABORTED"):
            return {
                "restart_status": "NORMAL_RESTART",
                "incomplete_run_detected": False,
                "action": "READY_FOR_NEW_EXPERIMENT",
                "previous_state": prev.to_dict(),
            }

        # Incomplete run detected!
        return {
            "restart_status": "INCOMPLETE_RUN_DETECTED",
            "incomplete_run_detected": True,
            "policy": self.restart_policy.value,
            "action": (
                "HOLD_FOR_OPERATOR_REVIEW"
                if self.restart_policy == RestartPolicy.REVIEW_REQUIRED
                else self.restart_policy.value
            ),
            "previous_state": prev.to_dict(),
        }

    def mark_completed(self) -> bool:
        """Mark active mission as cleanly completed."""
        state = self.load_persisted_state()
        if state:
            state.is_completed = True
            state.procedure_state = "COMPLETED"
            return self.persist_state(state)
        return False
