"""Automated Tests for Maintenance Mode, Rehearsal Engine, and Metrics (Phase 19, D19.15, D19.17, D19.21)."""

import pytest

from core.operations.maintenance import MaintenanceModeManager
from core.operations.metrics import OperationalMetricsTracker
from core.operations.rehearsal import MissionRehearsalEngine, RehearsalSpeed


def test_maintenance_mode_lifecycle_and_interlock():
    """Verify entering/exiting maintenance mode and live start safety interlocks (Section 37, 38)."""
    mgr = MaintenanceModeManager()

    # Ensure clean starting state
    mgr.exit_maintenance_mode("TESTRUNNER")
    assert mgr.is_maintenance_mode() is False
    assert mgr.verify_live_start_safety()[0] is True

    # Enter maintenance
    ok, msg = mgr.enter_maintenance_mode("SYSTEM_ENGINEER", "Calibrating optical alignment")
    assert ok is True
    assert mgr.is_maintenance_mode() is True

    # Interlock blocks live start
    can_start, reason = mgr.verify_live_start_safety()
    assert can_start is False
    assert "REJECTED" in reason

    # Diagnostics work
    cam_res = mgr.run_camera_diagnostic()
    assert cam_res.passed is True
    stor_res = mgr.run_storage_diagnostic()
    assert stor_res.passed is True

    # Exit maintenance
    ok, msg = mgr.exit_maintenance_mode("SYSTEM_ENGINEER")
    assert ok is True
    assert mgr.is_maintenance_mode() is False
    assert mgr.verify_live_start_safety()[0] is True


def test_rehearsal_engine_execution():
    """Verify GOLDEN_MISSION rehearsal execution across lifecycle phases (Section 47, 48)."""
    engine = MissionRehearsalEngine(scenario_name="GOLDEN_MISSION", speed=RehearsalSpeed.ACCELERATED)
    assert len(engine.steps) == 10
    assert engine.is_completed is False

    res = engine.run_all()
    assert res["status"] == "PASS"
    assert res["total_steps"] == 10
    assert res["executed_steps"] == 10
    assert engine.is_completed is True


def test_rehearsal_stepwise_stepping():
    """Verify stepwise pacing for operator practice (Section 49)."""
    engine = MissionRehearsalEngine(scenario_name="GOLDEN_MISSION", speed=RehearsalSpeed.STEPWISE)
    s1 = engine.advance_step()
    assert s1 is not None
    assert s1["step_index"] == 1
    assert s1["phase"] == "PREPARATION"

    s2 = engine.advance_step()
    assert s2 is not None
    assert s2["step_index"] == 2
    assert s2["phase"] == "INITIALIZATION"


def test_operational_metrics_tracker():
    """Verify operational timing measurements and KPI aggregations (Section 58, 59)."""
    tracker = OperationalMetricsTracker(run_id="RUN_TEST_KPI")
    tracker.record_startup_duration(2.45)
    tracker.record_preparation_duration(15.2)
    tracker.record_experiment_duration(180.0)
    tracker.record_deviation(45.0)
    tracker.record_recovery(55.0)
    tracker.record_operator_mistake()

    summary = tracker.compute_summary()
    assert summary["run_id"] == "RUN_TEST_KPI"
    assert summary["timings"]["startup_time_seconds"] == 2.45
    assert summary["timings"]["mean_recovery_seconds"] == 10.0
    assert summary["kpis"]["deviations_count"] == 1
    assert summary["kpis"]["recoveries_count"] == 1
    assert summary["kpis"]["recovery_success_rate"] == 100.0
    assert summary["kpis"]["mission_success"] is True
