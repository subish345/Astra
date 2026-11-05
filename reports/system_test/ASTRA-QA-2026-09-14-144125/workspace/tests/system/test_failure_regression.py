"""Failure Regression and System Hardening Tests (D11.18, D11.26)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from core.health.aggregator import HealthStatus, UnifiedHealthAggregator
from core.mission.lifecycle import MissionLifecycleState
from core.mission.orchestrator import MissionOrchestrator
from core.mission.run_manager import MissionRunManager
from core.mission.storage_manager import StorageManager


def test_camera_failure_and_recovery(tmp_path: Path):
    """Verify camera failure safely pauses mission and recovery restores it."""
    orchestrator = MissionOrchestrator(
        profile_name="demo",
        root_dir=str(tmp_path),
    )
    orchestrator.boot()
    orchestrator.run_self_test()
    orchestrator.start_mission("DEMO_EXP_001", run_id="CAM_FAIL_RUN")
    assert orchestrator.lifecycle.state == MissionLifecycleState.RUNNING

    # 1. Camera failure
    orchestrator.handle_camera_failure("Simulated hardware disconnect")
    assert orchestrator.lifecycle.state == MissionLifecycleState.PAUSED
    health = orchestrator.health_aggregator.evaluate_system_health()
    assert health["subsystems"]["camera"]["status"] == "FAILED"

    # 2. Camera recovery
    orchestrator.handle_camera_recovery()
    assert orchestrator.lifecycle.state == MissionLifecycleState.RUNNING
    health = orchestrator.health_aggregator.evaluate_system_health()
    assert health["subsystems"]["camera"]["status"] == "NORMAL"

    orchestrator.abort_mission("Test end")
    orchestrator.shutdown()


def test_crash_recovery_incomplete_runs(tmp_path: Path):
    """Verify detection of abandoned or crashed runs from previous sessions."""
    runs_dir = tmp_path / "data" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Simulate completed run
    comp_run = runs_dir / "RUN_COMPLETED"
    comp_run.mkdir()
    (comp_run / "mission_report.json").write_text("{}")

    # Simulate crashed run (missing report)
    crashed_run = runs_dir / "RUN_CRASHED"
    crashed_run.mkdir()
    (crashed_run / "run_metadata.json").write_text(json.dumps({"run_id": "RUN_CRASHED", "status": "RUNNING"}))

    run_mgr = MissionRunManager(base_dir=str(runs_dir))
    incomplete = run_mgr.detect_incomplete_runs()

    assert len(incomplete) == 1
    assert incomplete[0]["run_id"] == "RUN_CRASHED"
    assert incomplete[0]["status"] == "INCOMPLETE"


def test_storage_manager_warning_threshold(tmp_path: Path):
    """Verify storage manager warns on tight disk space limits."""
    # Set threshold unnaturally high (e.g. 100,000 GB) to guarantee low space warning
    mgr = StorageManager(root_dir=str(tmp_path), min_free_gb=100000.0)
    usage = mgr.get_disk_usage()
    assert usage["low_space_warning"] is True

    health = mgr.health_check()
    assert health["status"] in ("DEGRADED", "FAILED")


def test_non_critical_service_degradation():
    """Verify non-critical failures (voice, streaming) do not fail the overall system."""
    agg = UnifiedHealthAggregator()

    # Voice failure (OPTIONAL criticality)
    agg.update_component("voice", HealthStatus.FAILED, message="Audio driver unavailable")
    status = agg.evaluate_system_health()
    assert status["overall_status"] == "NORMAL" # Optional component does not degrade mission

    # Ground streaming failure (OPTIONAL criticality)
    agg.update_component("streaming", HealthStatus.FAILED, message="Network interface down")
    status = agg.evaluate_system_health()
    assert status["overall_status"] == "NORMAL"

    # Storage failure (IMPORTANT criticality)
    agg.update_component("storage", HealthStatus.DEGRADED, message="Approaching storage threshold")
    status = agg.evaluate_system_health()
    assert status["overall_status"] == "DEGRADED"

    # Camera failure (CRITICAL criticality)
    agg.update_component("camera", HealthStatus.FAILED, message="Sensor signal loss")
    status = agg.evaluate_system_health()
    assert status["overall_status"] == "FAILED"
