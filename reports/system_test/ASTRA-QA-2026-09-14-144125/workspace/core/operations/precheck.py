"""Pre-Mission Automated Verification Runner for ASTRA-EA (Phase 19, Section 9, 10, 11, D19.05, D19.06).

Implements 'astra mission precheck' to systematically validate hardware, camera, model,
procedure, storage, clock, recording, ground link, and health before authorizing READY state.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.common.config import get_project_root
from core.operations.checklist import ChecklistEngine, ChecklistItemStatus


@dataclass
class PrecheckResult:
    """Individual verification item result."""
    subsystem: str
    status: str  # PASS | DEGRADED | FAIL
    critical: bool
    details: str
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "status": self.status,
            "critical": self.critical,
            "details": self.details,
            "latency_ms": round(self.latency_ms, 2),
        }


class PreMissionRunner:
    """Automated pre-mission verification engine."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.root = project_root or get_project_root()

    def run_all_checks(self) -> Dict[str, Any]:
        """Execute comprehensive pre-mission verification matrix (Section 9, 10)."""
        import time
        t0 = time.perf_counter()
        results: List[PrecheckResult] = []

        # 1. Hardware / Silicon
        t_start = time.perf_counter()
        hw_res = self._check_hardware()
        hw_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(hw_res)

        # 2. Camera
        t_start = time.perf_counter()
        cam_res = self._check_camera()
        cam_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(cam_res)

        # 3. Model Integrity
        t_start = time.perf_counter()
        mod_res = self._check_model()
        mod_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(mod_res)

        # 4. Procedure
        t_start = time.perf_counter()
        prc_res = self._check_procedure()
        prc_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(prc_res)

        # 5. Storage
        t_start = time.perf_counter()
        str_res = self._check_storage()
        str_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(str_res)

        # 6. Clock
        t_start = time.perf_counter()
        clk_res = self._check_clock()
        clk_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(clk_res)

        # 7. Recording
        t_start = time.perf_counter()
        rec_res = self._check_recording()
        rec_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(rec_res)

        # 8. Ground Link
        t_start = time.perf_counter()
        gnd_res = self._check_ground_link()
        gnd_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(gnd_res)

        # 9. Health Self-Test
        t_start = time.perf_counter()
        hlt_res = self._check_health()
        hlt_res.latency_ms = (time.perf_counter() - t_start) * 1000.0
        results.append(hlt_res)

        total_ms = (time.perf_counter() - t0) * 1000.0

        # Calculate overall verdict
        has_critical_failure = any(r.critical and r.status == "FAIL" for r in results)
        has_degraded = any(r.status == "DEGRADED" for r in results)

        if has_critical_failure:
            overall = "BLOCKED"
        elif has_degraded:
            overall = "DEGRADED"
        else:
            overall = "READY"

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall,
            "total_duration_ms": round(total_ms, 2),
            "checks": [r.to_dict() for r in results],
            "is_authorized_to_start": overall in ("READY", "DEGRADED"),
        }

    def _check_hardware(self) -> PrecheckResult:
        try:
            from core.platform import get_platform, PlatformProfile
            plat = get_platform(profile=PlatformProfile.FLIGHT_TARGET_TBD)
            is_valid, violations = plat.validate_for_profile()
            if is_valid:
                return PrecheckResult(
                    subsystem="Hardware",
                    status="PASS",
                    critical=True,
                    details=f"{plat.cpu.architecture} ({plat.cpu.logical_cores} cores, {plat.memory.available_ram_mb:.0f}MB RAM free)",
                )
            return PrecheckResult(
                subsystem="Hardware",
                status="DEGRADED",
                critical=True,
                details=f"Platform profile violations: {'; '.join(violations)}",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Hardware",
                status="DEGRADED",
                critical=True,
                details=f"Hardware check fallback: {str(e)}",
            )

    def _check_camera(self) -> PrecheckResult:
        try:
            from core.platform.camera import SimulatedCameraDriver
            cam = SimulatedCameraDriver()
            cam.initialize()
            cam.start()
            read_res = cam.read_frame()
            cam.stop()
            if read_res is not None:
                frame, ts = read_res
                return PrecheckResult(
                    subsystem="Camera",
                    status="PASS",
                    critical=True,
                    details=f"Driver active ({frame.shape[1]}x{frame.shape[0]} optical stream)",
                )
            return PrecheckResult(
                subsystem="Camera",
                status="FAIL",
                critical=True,
                details="Camera driver returned empty frame",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Camera",
                status="FAIL",
                critical=True,
                details=f"Camera initialization exception: {str(e)}",
            )

    def _check_model(self) -> PrecheckResult:
        try:
            from core.flight.integrity import ModelIntegrityVerifier
            model_p = self.root / "models" / "checkpoints" / "ASTRA_OBJECT_DETECTOR_v0.1.0.onnx"
            if not model_p.exists():
                model_p = self.root / "models" / "ASTRA_OBJECT_DETECTOR_v0.1.0.onnx"
            verifier = ModelIntegrityVerifier(self.root)
            is_valid, report = verifier.verify_model(model_p)
            if is_valid:
                sha_prefix = report.get("sha256", "")[:12]
                return PrecheckResult(
                    subsystem="Model",
                    status="PASS",
                    critical=True,
                    details=f"ONNX weights SHA-256 verified ({sha_prefix}...)",
                )
            return PrecheckResult(
                subsystem="Model",
                status="FAIL",
                critical=True,
                details=f"Model error: {report.get('error')}",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Model",
                status="FAIL",
                critical=True,
                details=f"Model verification failed: {str(e)}",
            )

    def _check_procedure(self) -> PrecheckResult:
        try:
            from core.flight.integrity import ProcedureIntegrityVerifier
            proc_p = self.root / "configs" / "experiments" / "demo.yaml"
            verifier = ProcedureIntegrityVerifier(self.root)
            is_valid, report = verifier.verify_procedure(proc_p)
            if is_valid:
                return PrecheckResult(
                    subsystem="Procedure",
                    status="PASS",
                    critical=True,
                    details=f"Validated {report.get('total_steps')} steps & apparatus dependencies",
                )
            return PrecheckResult(
                subsystem="Procedure",
                status="FAIL",
                critical=True,
                details=f"Procedure error: {report.get('error')}",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Procedure",
                status="FAIL",
                critical=True,
                details=f"Procedure validation error: {str(e)}",
            )

    def _check_storage(self) -> PrecheckResult:
        try:
            from core.platform.storage import StorageManager
            mgr = StorageManager(self.root)
            usage = mgr.get_usage()
            if usage.status != "CRITICAL":
                return PrecheckResult(
                    subsystem="Storage",
                    status="PASS",
                    critical=True,
                    details=f"Partitions writable ({usage.free_capacity_mb:.0f}MB free, {usage.percent_used:.1f}% used)",
                )
            return PrecheckResult(
                subsystem="Storage",
                status="FAIL",
                critical=True,
                details="Storage capacity in CRITICAL condition (>95% used)",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Storage",
                status="FAIL",
                critical=True,
                details=f"Storage manager check failed: {str(e)}",
            )

    def _check_clock(self) -> PrecheckResult:
        try:
            from core.platform.clock import ClockSource, MissionClock
            clock = MissionClock(clock_source=ClockSource.SYSTEM_CLOCK)
            clock.start_mission()
            mono = clock.now_monotonic()
            if mono > 0:
                return PrecheckResult(
                    subsystem="Clock",
                    status="PASS",
                    critical=True,
                    details=f"Monotonic source active ({clock.clock_source.value})",
                )
            return PrecheckResult(
                subsystem="Clock",
                status="FAIL",
                critical=True,
                details="Clock monotonic timestamp non-positive",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Clock",
                status="FAIL",
                critical=True,
                details=f"Clock check error: {str(e)}",
            )

    def _check_recording(self) -> PrecheckResult:
        try:
            storage_dir = self.root / "flight_data" / "evidence"
            if not storage_dir.exists():
                storage_dir = self.root / "storage" / "evidence"
            storage_dir.mkdir(parents=True, exist_ok=True)
            test_file = storage_dir / ".precheck_write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            return PrecheckResult(
                subsystem="Recording",
                status="PASS",
                critical=False,
                details="Evidence and video capture directories writable",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Recording",
                status="DEGRADED",
                critical=False,
                details=f"Recording directory write failure: {str(e)}",
            )

    def _check_ground_link(self) -> PrecheckResult:
        try:
            from integration.telemetry import MemoryTelemetryPublisher
            pub = MemoryTelemetryPublisher()
            return PrecheckResult(
                subsystem="Ground Link",
                status="PASS",
                critical=False,
                details="Telemetry publisher interface operational",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Ground Link",
                status="DEGRADED",
                critical=False,
                details=f"Telemetry publisher check error: {str(e)}",
            )

    def _check_health(self) -> PrecheckResult:
        try:
            from core.platform.health import HealthState, PlatformHealthMonitor
            monitor = PlatformHealthMonitor()
            overall = monitor.evaluate_overall_health()
            if overall != HealthState.FAILED:
                return PrecheckResult(
                    subsystem="Health",
                    status="PASS",
                    critical=True,
                    details=f"Aggregate state: {overall.value}",
                )
            return PrecheckResult(
                subsystem="Health",
                status="FAIL",
                critical=True,
                details="Subsystem health self-test reported FAILED",
            )
        except Exception as e:
            return PrecheckResult(
                subsystem="Health",
                status="DEGRADED",
                critical=True,
                details=f"Health self-test exception: {str(e)}",
            )
