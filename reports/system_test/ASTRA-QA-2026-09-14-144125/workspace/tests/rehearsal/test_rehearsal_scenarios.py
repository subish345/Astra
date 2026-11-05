"""Tests for the 12 Formal Operational Rehearsal Scenarios (Phase 20, D20.06 - D20.17)."""

from pathlib import Path
import pytest

from core.operations.rehearsal import (
    MissionRehearsalEngine,
    RehearsalMode,
    RehearsalSpeed,
)


def test_clean_run_scenario(tmp_path: Path) -> None:
    """D20.06: Rehearsal #2 — Clean Run with zero deviations."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_02_CLEAN",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    assert res.deviations_count == 0
    assert res.recoveries_count == 0
    assert res.false_verifications == 0
    assert res.data_consistency == "CONSISTENT"


def test_deviation_run_scenario(tmp_path: Path) -> None:
    """D20.07: Rehearsal #1 — Planned wrong object deviation and recovery."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_01_DEVIATION",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    assert res.deviations_count == 1
    assert res.recoveries_count == 1
    assert res.data_consistency == "CONSISTENT"


def test_uncertainty_scenario(tmp_path: Path) -> None:
    """D20.08: Rehearsal #3 — Partial visual occlusion without false deviation."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_03_UNCERTAINTY",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    assert any(e["event_type"] == "STEP_UNCERTAIN" for e in eng.rehearsal_log)
    assert res.false_deviations == 0


def test_network_failure_scenario(tmp_path: Path) -> None:
    """D20.09: Rehearsal #4 — Telemetry ground sever and reconciliation."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_04_NETWORK_FAILURE",
        mode=RehearsalMode.HIL,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    assert any(e["event_type"] == "GROUND_OFFLINE" for e in eng.rehearsal_log)
    reconn = next(e for e in eng.rehearsal_log if e["event_type"] == "GROUND_RECONNECTED")
    assert reconn["payload"]["duplicate_count"] == 0


def test_camera_failure_scenario(tmp_path: Path) -> None:
    """D20.10: Rehearsal #5 — Camera failure pauses verification."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_05_CAMERA_FAILURE",
        mode=RehearsalMode.HIL,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    fault = next(e for e in eng.rehearsal_log if e["event_type"] == "CAMERA_FAILED")
    assert fault["payload"]["allow_step_verification"] is False
    assert any(e["event_type"] == "CAMERA_RESTORED" for e in eng.rehearsal_log)


def test_model_failure_scenario(tmp_path: Path) -> None:
    """D20.11: Rehearsal #6 — Inference failure engages rule-based fallback."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_06_MODEL_FAILURE",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    err = next(e for e in eng.rehearsal_log if e["event_type"] == "MODEL_FAILURE")
    assert err["payload"]["fallback_engaged"] == "RULE_BASED_HEURISTIC"


def test_storage_warning_scenario(tmp_path: Path) -> None:
    """D20.12: Rehearsal #7 — Storage capacity warning and retention policy."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_07_STORAGE_WARNING",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    warn = next(e for e in eng.rehearsal_log if e["event_type"] == "STORAGE_WARNING")
    assert warn["payload"]["critical_evidence_preserved"] is True


def test_ground_failure_scenario(tmp_path: Path) -> None:
    """D20.13: Rehearsal #8 — Ground monitor process termination and state recovery."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_08_GROUND_FAILURE",
        mode=RehearsalMode.HIL,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    crash = next(e for e in eng.rehearsal_log if e["event_type"] == "GROUND_CRASHED")
    assert crash["payload"]["onboard_unaffected"] is True


def test_voice_failure_scenario(tmp_path: Path) -> None:
    """D20.14: Rehearsal #9 — Audio TTS failure with visual HUD continuity."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_09_VOICE_FAILURE",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    err = next(e for e in eng.rehearsal_log if e["event_type"] == "VOICE_FAILED")
    assert err["payload"]["visual_guidance"] == "ACTIVE"


def test_combined_fault_scenario(tmp_path: Path) -> None:
    """D20.15: Rehearsal #10 — Dual fault: wrong apparatus + ground loss."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_10_COMBINED_FAULT",
        mode=RehearsalMode.HIL,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    assert res.deviations_count == 1
    assert res.recoveries_count == 1
    assert any(e["event_type"] == "GROUND_OFFLINE" for e in eng.rehearsal_log)
    assert any(e["event_type"] == "GROUND_RECONNECTED" for e in eng.rehearsal_log)


def test_viewpoint_scenario(tmp_path: Path) -> None:
    """D20.16: Rehearsal #11 — Multi-view consistency across LEFT/CENTER/RIGHT."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_11_VIEWPOINT",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    assert any(e.get("payload", {}).get("view") == "VIEW_LEFT" for e in eng.rehearsal_log)
    assert any(e.get("payload", {}).get("view") == "VIEW_CENTER" for e in eng.rehearsal_log)
    assert any(e.get("payload", {}).get("view") == "VIEW_RIGHT" for e in eng.rehearsal_log)


def test_operator_independence_scenario(tmp_path: Path) -> None:
    """D20.17: Rehearsal #12 — New operator independent execution without developer assistance."""
    eng = MissionRehearsalEngine(
        scenario_name="REH_12_OPERATOR_INDEP",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        operator="Trainee_Astronaut_B",
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert res.status == "PASS"
    comp = next(e for e in eng.rehearsal_log if e["event_type"] == "EXPERIMENT_COMPLETED")
    assert comp["payload"]["developer_interventions"] == 0
