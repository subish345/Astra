"""Automated Test Suite for State Persistence, Recovery, and Flight Logging (Phase 18)."""

import pytest

from core.flight.logger import FlightLogger
from core.flight.persistence import MissionStateManager, MissionStateRecord, RestartPolicy


def test_mission_state_persistence_and_restart_policy(tmp_path):
    """Verify atomic state persistence and REVIEW_REQUIRED restart policy (Section 34 & 35)."""
    state_mgr = MissionStateManager(
        storage_dir=tmp_path / "mission",
        restart_policy=RestartPolicy.REVIEW_REQUIRED,
    )

    # Clean boot
    clean_eval = state_mgr.evaluate_startup_state()
    assert clean_eval["restart_status"] == "CLEAN_BOOT"
    assert clean_eval["incomplete_run_detected"] is False

    # Persist active uncompleted mission state (simulating mid-run power drop)
    rec = MissionStateRecord(
        experiment_id="EXP-FLIGHT-01",
        run_id="RUN-404",
        current_step_id="STEP-03",
        procedure_state="IN_PROGRESS",
        assurance_state="VERIFIED",
        recovery_state="NONE",
        last_event_sequence=88,
        timestamp_utc="2026-09-13T12:30:00Z",
        is_completed=False,
    )
    assert state_mgr.persist_state(rec) is True

    # Reboot evaluation
    reboot_eval = state_mgr.evaluate_startup_state()
    assert reboot_eval["restart_status"] == "INCOMPLETE_RUN_DETECTED"
    assert reboot_eval["incomplete_run_detected"] is True
    assert reboot_eval["policy"] == "REVIEW_REQUIRED"
    assert reboot_eval["action"] == "HOLD_FOR_OPERATOR_REVIEW"

    # Mark completed cleanly
    assert state_mgr.mark_completed() is True
    clean_reboot = state_mgr.evaluate_startup_state()
    assert clean_reboot["restart_status"] == "NORMAL_RESTART"
    assert clean_reboot["incomplete_run_detected"] is False


def test_flight_logger_structured_and_rotating(tmp_path):
    """Verify structured sequence-numbered flight logging (Section 38)."""
    flogger = FlightLogger(log_dir=tmp_path / "diagnostics", max_bytes=1024, backup_count=2)
    entry1 = flogger.info("TEST_SRC", "System startup nominal")
    entry2 = flogger.warning("TEST_SRC", "Thermal zone elevated")
    entry3 = flogger.error("TEST_SRC", "Telemetry buffer backpressure")

    assert entry1["sequence"] == 1
    assert entry2["sequence"] == 2
    assert entry3["sequence"] == 3
    assert entry1["severity"] == "INFO"
    assert entry2["severity"] == "WARNING"
    assert entry3["severity"] == "ERROR"

    # Verify log file exists on disk
    assert flogger.log_file.exists()
    content = flogger.log_file.read_text(encoding="utf-8")
    assert "System startup nominal" in content
