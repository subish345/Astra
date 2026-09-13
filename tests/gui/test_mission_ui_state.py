# ==============================================================================
# ASTRA-EA Mission UI State Store Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Unit tests for MissionUIState data container and BackendEventBridge."""

import pytest
from core.ui.state import MissionUIState
from core.ui.bridge import BackendEventBridge


def test_mission_ui_state_defaults():
    state = MissionUIState()
    assert state.experiment.experiment_id == "DEMO_EXP_001"
    assert state.session.status == "READY"
    assert state.current_step.step_id == "STEP_01"
    assert state.offline_mode is True
    assert len(state.step_statuses) == 4
    assert state.step_statuses["STEP_01"] == "WAITING"


def test_apply_step_progress():
    state = MissionUIState()
    state.apply_step_progress(
        current_step_id="STEP_02",
        next_step_id="STEP_03",
        completed_steps=["STEP_01"],
        status_name="MONITORING",
    )
    assert state.step_statuses["STEP_01"] == "VERIFIED"
    assert state.step_statuses["STEP_02"] == "IN_PROGRESS"
    assert state.current_step.step_id == "STEP_02"
    assert state.next_action.step_id == "STEP_03"


def test_apply_assurance_decisions():
    state = MissionUIState()

    # Verified
    state.apply_assurance_decision("VERIFIED", 0.94, ["Evidence corroborated"], step_id="STEP_02")
    assert state.assurance.decision == "VERIFIED"
    assert state.assurance.confidence == 0.94
    assert state.step_statuses["STEP_02"] == "VERIFIED"
    assert state.deviation.is_active is False

    # Uncertain
    state.apply_assurance_decision("UNCERTAIN", 0.45, ["Partial occlusion"], step_id="STEP_03")
    assert state.assurance.decision == "UNCERTAIN"
    assert state.step_statuses["STEP_03"] == "UNCERTAIN"

    # Deviation
    state.apply_assurance_decision("DEVIATION", 0.1, ["Wrong object selected"], step_id="STEP_03")
    assert state.assurance.decision == "DEVIATION"
    assert state.deviation.is_active is True
    assert state.step_statuses["STEP_03"] == "DEVIATION"


def test_apply_deviation_and_recovery():
    state = MissionUIState()
    state.apply_deviation(
        dev_type="WRONG_OBJECT",
        expected_obj="RED_BOX",
        detected_obj="YELLOW_BOX",
        reason="Wrong object selected",
        recovery_guidance="Return yellow box and acquire red box",
    )
    assert state.deviation.is_active is True
    assert state.deviation.deviation_type == "WRONG_OBJECT"
    assert state.recovery.is_recovering is True
    assert state.recovery.state_name == "RECOMMEND"

    # Successful recovery
    state.apply_recovery(state_name="RESUME", instruction="Recovery complete", verified=True)
    assert state.recovery.verified is True
    assert state.recovery.is_recovering is False
    assert state.deviation.is_active is False


def test_add_timeline_and_evidence():
    state = MissionUIState()
    ev = state.add_timeline_event("ASSURANCE", "STEP_01 Verified", "Score 0.95", severity="SUCCESS")
    assert ev.title == "STEP_01 Verified"
    assert len(state.timeline) == 1

    state.add_evidence_item("SPATIAL_PROXIMITY", 0.92, True, "Inside station zone", source_frame=110)
    assert len(state.evidence_items) == 1
    assert state.evidence_items[0].is_satisfied is True
    assert state.evidence_items[0].score == 0.92
