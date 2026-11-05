# ==============================================================================
# ASTRA-EA Mission Console End-to-End GUI Integration Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Integration tests verifying full typed event propagation through MissionConsoleWindow."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtWidgets import QApplication

from core.assurance.types import AssuranceDecision, DecisionType, DeviationReason
from core.assistance.recovery import RecoveryContext, RecoveryState
from core.procedure.types import ProcedureState, ProcedureStatus
from core.procedure.schema import ExperimentStep
from core.ui.main_window import MissionConsoleWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def console_window(qapp):
    win = MissionConsoleWindow()
    win.show()
    yield win
    win.close()


def test_integration_step_progress_event(console_window):
    """Verify sig_step_progress propagates into UI state and progress panel."""
    progress_state = ProcedureState(
        run_id="SESSION_001",
        experiment_id="DEMO_EXP_001",
        procedure_status=ProcedureStatus.MONITORING,
        current_step="STEP_02",
        next_expected_step="STEP_03",
        completed_steps=["STEP_01"],
    )

    console_window.bridge.sig_step_progress.emit(progress_state)

    assert console_window.state.step_statuses["STEP_01"] == "VERIFIED"
    assert console_window.state.step_statuses["STEP_02"] == "IN_PROGRESS"
    assert "STEP 02" in console_window.console_view.step_panel.lbl_step_num.text()


def test_integration_step_verified_event(console_window):
    """Verify StepVerified decision renders VERIFIED on status panel."""
    step = ExperimentStep(
        id="STEP_02",
        sequence=2,
        name="Grasp Specimen Container",
        expected_actions=["GRASP"],
        expected_objects=["RED_BOX"],
    )
    decision = AssuranceDecision(
        experiment_id="DEMO_EXP_001",
        step_id="STEP_02",
        sequence=2,
        decision=DecisionType.VERIFIED,
        confidence=0.96,
        reasons=["All required corroborating evidence satisfied"],
    )

    console_window.bridge.sig_assurance_decision.emit(decision, step)

    assert "VERIFIED" in console_window.console_view.status_panel.lbl_alert_title.text()
    assert "96.0%" in console_window.console_view.status_panel.lbl_confidence.text()


def test_integration_step_uncertain_event(console_window):
    """Verify StepUncertain decision renders UNCERTAIN without calling it ERROR."""
    step = ExperimentStep(
        id="STEP_03",
        sequence=3,
        name="Transfer Specimen",
        expected_actions=["PLACE"],
        expected_objects=["RED_BOX"],
    )
    decision = AssuranceDecision(
        experiment_id="DEMO_EXP_001",
        step_id="STEP_03",
        sequence=3,
        decision=DecisionType.UNCERTAIN,
        confidence=0.40,
        reasons=["Hand partially occluded; insufficient visual evidence"],
    )

    console_window.bridge.sig_assurance_decision.emit(decision, step)

    title_text = console_window.console_view.status_panel.lbl_alert_title.text()
    assert "UNCERTAIN" in title_text
    assert "ERROR" not in title_text


def test_integration_deviation_detected_event(console_window):
    """Verify DeviationDetected renders red banner and explicit recovery instruction."""
    step = ExperimentStep(
        id="STEP_02",
        sequence=2,
        name="Grasp Specimen Container",
        expected_actions=["GRASP"],
        expected_objects=["RED_BOX"],
    )
    decision = AssuranceDecision(
        experiment_id="DEMO_EXP_001",
        step_id="STEP_02",
        sequence=2,
        decision=DecisionType.DEVIATION,
        deviation_reason=DeviationReason.WRONG_OBJECT,
        confidence=0.05,
        reasons=["Astronaut interacted with YELLOW_BOX; expected RED_BOX"],
    )

    console_window.bridge.sig_deviation.emit(decision, step)

    assert "DEVIATION" in console_window.console_view.status_panel.lbl_alert_title.text()
    assert "RED_BOX" in console_window.console_view.status_panel.lbl_dev_expected.text()


def test_integration_recovery_lifecycle(console_window):
    """Verify recovery states: RECOMMEND -> RESUME (verified)."""
    # 1. Recovery recommendation
    ctx = RecoveryContext(
        context_id="REC_001",
        session_id="SESSION_001",
        step_id="STEP_02",
        deviation_reason=DeviationReason.WRONG_OBJECT,
        state=RecoveryState.RECOMMENDING,
        explanation="Wrong object selected",
        recommendation="Acquire RED_BOX to restore experiment integrity.",
        target_step_id="STEP_02",
    )
    console_window.bridge.sig_recovery.emit(ctx)
    assert "RECOVERY" in console_window.console_view.status_panel.lbl_alert_title.text()
    assert "Acquire RED_BOX" in console_window.console_view.status_panel.lbl_dev_recovery.text()

    # 2. Recovery verified
    ctx_res = RecoveryContext(
        context_id="REC_001",
        session_id="SESSION_001",
        step_id="STEP_02",
        deviation_reason=DeviationReason.WRONG_OBJECT,
        state=RecoveryState.RESUMED,
        explanation="Resolved",
        recommendation="Corrective action confirmed. Resuming Step 02.",
        target_step_id="STEP_02",
        verified_corrective_action=True,
    )
    console_window.bridge.sig_recovery.emit(ctx_res)
    assert "VERIFIED" in console_window.console_view.status_panel.lbl_alert_title.text()


def test_navigation_stack_views(console_window):
    """Verify switching views across all 5 main window screens."""
    views = [
        ("MISSION", 0),
        ("EVIDENCE", 1),
        ("TIMELINE", 2),
        ("HEALTH", 3),
        ("SETTINGS", 4),
    ]
    for label, idx in views:
        console_window.stack.setCurrentIndex(idx)
        assert console_window.stack.currentIndex() == idx

    # Test pixel-perfect window grab
    pix = console_window.grab()
    assert not pix.isNull()
    assert pix.width() >= 1200
    assert pix.height() >= 680
