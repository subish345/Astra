# ==============================================================================
# ASTRA-EA Ground Monitor UI Panels Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Automated tests for Ground Monitor UI panels and components in headless mode."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from apps.ground_monitor.panels.alert_panel import AlertPanel
from apps.ground_monitor.panels.header_panel import HeaderPanel
from apps.ground_monitor.panels.health_panel import HealthPanel
from apps.ground_monitor.panels.mission_panel import MissionPanel
from apps.ground_monitor.panels.timeline_panel import TimelinePanel
from apps.ground_monitor.panels.video_panel import VideoPanel
from streaming.events.schema import EventFilter, EventSeverity, EventType, GroundEvent


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_header_panel(qapp: QApplication) -> None:
    header = HeaderPanel()
    assert header is not None

    header.set_simulation_mode(True)
    assert not header.sim_badge.isHidden()

    header.update_status({
        "overall": "ONLINE",
        "quality": "GOOD",
        "video_connected": True,
        "events_connected": True,
        "stream_fps": 15.0,
        "heartbeat_age_seconds": 0.4,
    })
    assert "ONLINE" in header.link_badge.text()


def test_video_panel(qapp: QApplication) -> None:
    panel = VideoPanel()
    panel.resize(640, 480)

    # Render frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    panel.set_frame(test_frame, {"fps": 14.8})
    assert "14.8" in panel.fps_label.text()
    assert "640x480" in panel.res_label.text()

    # Disconnect
    panel.set_connected(False)
    assert "OFFLINE" in panel.status_icon.text()


def test_mission_panel(qapp: QApplication) -> None:
    panel = MissionPanel()
    panel.set_mission("EXP_999", "RUN_0002", "STEP_03", "Test Step", 2, 4)
    assert panel.step_id_label.text() == "STEP_03"
    assert panel.progress_bar.value() == 75

    panel.set_assurance("DEVIATION", "Wrong object manipulated")
    assert "DEVIATION" in panel.assurance_banner.text()


def test_alert_panel(qapp: QApplication) -> None:
    panel = AlertPanel()
    # Nominal
    panel.set_alert("", "INFO", "")
    assert "NOMINAL" in panel.alert_badge.text()

    # Deviation
    panel.set_alert("WRONG_OBJECT", "DANGER", "Swap to RED_BOX")
    assert "DEVIATION" in panel.alert_badge.text()
    assert "Swap to RED_BOX" in panel.recovery_label.text()


def test_timeline_panel(qapp: QApplication) -> None:
    panel = TimelinePanel()
    event = GroundEvent(
        event_id="E100",
        sequence_num=1,
        event_type=EventType.STEP_VERIFIED,
        message="Step completed",
    )
    panel.add_event(event, latency_ms=14.5)
    assert panel.list_widget.count() == 1


def test_health_panel(qapp: QApplication) -> None:
    panel = HealthPanel()
    panel.update_link({"stream_fps": 15.0, "quality": "GOOD", "heartbeat_age_seconds": 0.5, "reconnect_count": 0})
    assert "15.0 FPS" in panel.lbl_fps_val.text()
    assert "GOOD" in panel.lbl_quality_val.text()
