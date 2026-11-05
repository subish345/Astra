# ==============================================================================
# ASTRA-EA Mission Console Component Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Headless unit tests for individual Mission Console Qt panels and widgets."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.ui.panels.evidence_panel import EvidencePanel
from core.ui.panels.health_panel import HealthPanel
from core.ui.panels.progress_panel import ProgressPanel
from core.ui.panels.session_bar import SessionBar
from core.ui.panels.status_panel import StatusPanel
from core.ui.panels.step_panel import StepPanel
from core.ui.panels.timeline_panel import TimelinePanel
from core.ui.panels.video_panel import VideoPanel
from core.ui.state import EvidenceItemState, TimelineEventState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_video_panel(qapp):
    panel = VideoPanel()
    assert panel.show_pose is True
    assert panel.show_hands is True
    assert panel.show_debug is False

    # Toggle layers
    panel.btn_debug.setChecked(True)
    assert panel.show_debug is True

    # Render dummy black image
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    panel.update_frame(dummy_frame)
    assert panel.video_surface.pixmap() is not None


def test_step_panel(qapp):
    panel = StepPanel()
    panel.update_step(
        step_number=2,
        total_steps=4,
        step_name="Grasp Specimen Container",
        expected_action="GRASP RED_BOX",
        status="VERIFYING",
        time_in_step=5.2,
    )
    assert "STEP 02 / 04" in panel.lbl_step_num.text()
    assert "Grasp Specimen Container" in panel.lbl_step_title.text()
    assert "GRASP RED_BOX" in panel.lbl_expected.text()

    panel.update_next_action("Transfer specimen to work surface")
    assert "Transfer specimen" in panel.lbl_next_text.text()


def test_status_panel_lifecycle(qapp):
    panel = StatusPanel()
    panel.reset_to_ready()
    assert "READY" in panel.lbl_alert_title.text()

    # Verified
    panel.show_verified("Grasp Specimen", 0.95, ["All required evidence present"])
    assert "VERIFIED" in panel.lbl_alert_title.text()
    assert "95.0%" in panel.lbl_confidence.text()

    # Uncertain (never called error)
    panel.show_uncertain("Object partially occluded")
    assert "UNCERTAIN" in panel.lbl_alert_title.text()
    assert "ERROR" not in panel.lbl_alert_title.text()

    # Deviation
    panel.show()
    panel.show_deviation(
        deviation_type="WRONG_OBJECT",
        expected_obj="RED_BOX",
        detected_obj="YELLOW_BOX",
        reason="Wrong object selected",
        recovery_instruction="Select RED_BOX",
    )
    assert "DEVIATION" in panel.lbl_alert_title.text()
    assert not panel.dev_frame.isHidden()
    assert "RED_BOX" in panel.lbl_dev_expected.text()
    assert "YELLOW_BOX" in panel.lbl_dev_detected.text()

    # Recovery
    panel.show_recovery("RECOMMEND", "Select RED_BOX", verified=False)
    assert "RECOVERY" in panel.lbl_alert_title.text()


def test_progress_panel(qapp):
    panel = ProgressPanel()
    panel.update_steps({
        "STEP_01": "VERIFIED",
        "STEP_02": "IN_PROGRESS",
        "STEP_03": "WAITING",
        "STEP_04": "WAITING",
    }, current_step_id="STEP_02")
    assert panel.step_rows["STEP_01"].status == "VERIFIED"
    assert panel.step_rows["STEP_02"].status == "IN_PROGRESS"
    assert "1 / 4 VERIFIED" in panel.lbl_summary.text()


def test_evidence_panel(qapp):
    panel = EvidencePanel()
    items = [
        EvidenceItemState(
            evidence_type="OBJECT_DETECTED",
            score=0.96,
            is_satisfied=True,
            details="RED_BOX tracked with high confidence",
            timestamp=100.0,
            source_frame=245,
        ),
        EvidenceItemState(
            evidence_type="HAND_OBJECT_CONTACT",
            score=0.91,
            is_satisfied=True,
            details="Contact distance < 0.08 normalized units",
            timestamp=100.0,
            source_frame=245,
        ),
    ]
    panel.update_evidence(items, bundle_score=0.93)
    assert panel.table.rowCount() == 2
    assert "93.0%" in panel.lbl_score.text()


def test_timeline_panel(qapp):
    panel = TimelinePanel()
    panel.add_event(TimelineEventState("12:00:01", "STEP", "Step 01 Active", "Desc", "INFO"))
    panel.add_event(TimelineEventState("12:00:05", "DEVIATION", "Wrong Object", "Yellow box selected", "DANGER"))
    assert panel.table.rowCount() == 2

    # Filter by deviation
    panel._set_filter("DEVIATION")
    assert panel.table.rowCount() == 1
    assert "Wrong Object" in panel.table.item(0, 2).text()


def test_health_panel(qapp):
    panel = HealthPanel()
    panel.set_subsystem_status("Camera", "ONLINE")
    panel.set_subsystem_status("Network", "OFFLINE")
    # Network offline is normal air-gapped status, not failure
    assert "ONLINE" in panel.badges["Camera"].lbl_status.text()
    assert "OFFLINE" in panel.badges["Network"].lbl_status.text()

    panel.update_telemetry(fps=29.8, latency_ms=14.2, cpu_pct=25.0, ram_mb=512.0)
    assert "29.8" in panel.lbl_fps.text()
    assert "14.2" in panel.lbl_lat.text()


def test_session_bar(qapp):
    bar = SessionBar()
    bar.set_session_state("RUNNING", "RUN_TEST_001")
    assert bar.btn_start.isEnabled() is False
    assert bar.btn_stop.isEnabled() is True
    assert "RUN_TEST_001" in bar.lbl_run_id.text()

    bar.set_camera_profile("VIEW_RIGHT")
    assert "VIEW_RIGHT" in bar.lbl_cam_profile.text()
