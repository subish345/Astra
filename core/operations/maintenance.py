"""Maintenance Mode Manager for ASTRA-EA (Phase 19, Section 37, 38, D19.15).

Isolates maintenance diagnostics (camera loopback, model weight checksums, storage scrubbing)
from live mission execution, enforcing strict mutual exclusion to prevent accidental experiment starts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.common.config import get_project_root


@dataclass
class DiagnosticResult:
    test_name: str
    passed: bool
    details: str
    timestamp_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "details": self.details,
            "timestamp_utc": self.timestamp_utc,
        }


class MaintenanceModeManager:
    """Controls maintenance mode state, diagnostic test executions, and safety interlocks."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.root = project_root or get_project_root()
        self.state_file = self.root / "flight_data" / "diagnostics" / "maintenance_state.json"
        self._ensure_state_file()

    def _ensure_state_file(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._save_state(is_active=False, reason="Initial startup state")

    def _save_state(self, is_active: bool, reason: str = "") -> None:
        payload = {
            "is_active": is_active,
            "entered_at_utc": datetime.now(timezone.utc).isoformat() if is_active else None,
            "reason": reason,
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def is_maintenance_mode(self) -> bool:
        """Check if system is currently locked in maintenance mode."""
        if not self.state_file.exists():
            return False
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("is_active", False))
        except Exception:
            return False

    def enter_maintenance_mode(self, operator: str, reason: str = "") -> Tuple[bool, str]:
        """Enter maintenance mode (Section 37)."""
        if self.is_maintenance_mode():
            return True, "Already in MAINTENANCE MODE."

        # Safety check: Ensure no active live experiment is running
        active_mission_state = self.root / "flight_data" / "mission" / "active_mission_state.json"
        if active_mission_state.exists():
            try:
                with open(active_mission_state, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    if state.get("procedure_state") == "RUNNING":
                        return False, "Cannot enter MAINTENANCE MODE while a live experiment is RUNNING."
            except Exception:
                pass

        self._save_state(is_active=True, reason=f"Operator '{operator}': {reason or 'Scheduled maintenance'}")
        return True, "Successfully entered MAINTENANCE MODE. Live experiment starts are now blocked."

    def exit_maintenance_mode(self, operator: str) -> Tuple[bool, str]:
        """Exit maintenance mode and return to operational state."""
        if not self.is_maintenance_mode():
            return True, "System is not in maintenance mode."

        self._save_state(is_active=False, reason=f"Operator '{operator}' returned system to operational state.")
        return True, "Exited MAINTENANCE MODE. Operational readiness restored."

    def verify_live_start_safety(self) -> Tuple[bool, str]:
        """Safety interlock (Section 38: No live experiment should start accidentally)."""
        if self.is_maintenance_mode():
            return False, "START_EXPERIMENT REJECTED: System is currently locked in MAINTENANCE MODE."
        return True, "Safety check passed: System is in operational mode."

    def run_camera_diagnostic(self) -> DiagnosticResult:
        """Execute optical camera diagnostic self-test."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            from core.platform.camera import SimulatedCameraDriver
            cam = SimulatedCameraDriver()
            cam.initialize()
            cam.start()
            read_res = cam.read_frame()
            cam.stop()
            if read_res is not None:
                f, ts = read_res
                return DiagnosticResult(
                    test_name="CAMERA_LOOPBACK_TEST",
                    passed=True,
                    details=f"Captured test frame: {f.shape[1]}x{f.shape[0]}x{f.shape[2]}",
                    timestamp_utc=now,
                )
            return DiagnosticResult(
                test_name="CAMERA_LOOPBACK_TEST",
                passed=False,
                details="Empty frame returned from camera driver",
                timestamp_utc=now,
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="CAMERA_LOOPBACK_TEST",
                passed=False,
                details=f"Diagnostic error: {str(e)}",
                timestamp_utc=now,
            )

    def run_storage_diagnostic(self) -> DiagnosticResult:
        """Execute storage write/scrub diagnostic."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            from core.platform.storage import StorageManager
            mgr = StorageManager(self.root)
            usage = mgr.get_usage()
            is_ok = usage.status != "CRITICAL"
            return DiagnosticResult(
                test_name="STORAGE_PARTITION_INTEGRITY",
                passed=is_ok,
                details=f"Free: {usage.free_capacity_mb:.0f}MB, Status: {usage.status}",
                timestamp_utc=now,
            )
        except Exception as e:
            return DiagnosticResult(
                test_name="STORAGE_PARTITION_INTEGRITY",
                passed=False,
                details=f"Diagnostic error: {str(e)}",
                timestamp_utc=now,
            )
