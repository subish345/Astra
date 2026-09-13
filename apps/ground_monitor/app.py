# ==============================================================================
# ASTRA-EA Ground Monitor Main Window
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Main window for the standalone read-only Ground Monitor application."""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, Optional
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from apps.ground_monitor.panels.alert_panel import AlertPanel
from apps.ground_monitor.panels.evidence_viewer import EvidenceViewerDialog
from apps.ground_monitor.panels.header_panel import HeaderPanel
from apps.ground_monitor.panels.health_panel import HealthPanel
from apps.ground_monitor.panels.mission_panel import MissionPanel
from apps.ground_monitor.panels.timeline_panel import TimelinePanel
from apps.ground_monitor.panels.video_panel import VideoPanel
from apps.ground_monitor.state import GroundMonitorState
from apps.ground_monitor.theme import GROUND_MONITOR_QSS
from streaming.connection.manager import ConnectionManager
from streaming.events.schema import GroundEvent

logger = logging.getLogger("ground_monitor_app")


class GroundMonitorWindow(QMainWindow):
    """Main application window for remote ground observability and experiment monitoring."""

    def __init__(
        self,
        stream_url: str = "http://127.0.0.1:8554/video",
        events_url: str = "http://127.0.0.1:8765/events",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ASTRA-EA Ground Observability Console (Read-Only)")
        self.resize(1366, 850)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(GROUND_MONITOR_QSS)

        self.stream_url = stream_url
        self.events_url = events_url

        # Reactive presentation state
        self.state = GroundMonitorState(self)

        # Build UI
        self._init_ui()

        # Connect state signals to UI panel slots
        self._connect_signals()

        # Initialize network connection manager
        self.conn_mgr = ConnectionManager(
            stream_url=self.stream_url,
            events_url=self.events_url,
            on_frame_callback=self._on_video_frame,
            on_event_callback=self._on_telemetry_event,
            on_link_status_callback=self._on_link_status,
        )
        self.conn_mgr.connect_all()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("rootWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # 1. Top Header Banner
        self.header_panel = HeaderPanel(self)
        root_layout.addWidget(self.header_panel)

        # 2. Main Horizontal Splitter (Left: Video + Timeline; Right: Mission + Alerts + Health)
        h_splitter = QSplitter(Qt.Horizontal)

        # Left Column Container
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        v_splitter = QSplitter(Qt.Vertical)
        self.video_panel = VideoPanel(self)
        self.timeline_panel = TimelinePanel(self)
        v_splitter.addWidget(self.video_panel)
        v_splitter.addWidget(self.timeline_panel)
        v_splitter.setStretchFactor(0, 3)
        v_splitter.setStretchFactor(1, 2)
        left_layout.addWidget(v_splitter)

        # Right Column Container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.mission_panel = MissionPanel(self)
        self.alert_panel = AlertPanel(self)
        self.health_panel = HealthPanel(self)

        right_layout.addWidget(self.mission_panel)
        right_layout.addWidget(self.alert_panel)
        right_layout.addWidget(self.health_panel)
        right_layout.addStretch()

        h_splitter.addWidget(left_container)
        h_splitter.addWidget(right_container)
        h_splitter.setStretchFactor(0, 7)
        h_splitter.setStretchFactor(1, 3)

        root_layout.addWidget(h_splitter, stretch=1)

    def _connect_signals(self) -> None:
        """Connect state signals to panel methods."""
        self.state.sig_link_changed.connect(self._handle_link_update)
        self.state.sig_mission_changed.connect(self.mission_panel.set_mission)
        self.state.sig_activity_changed.connect(self.mission_panel.set_activity)
        self.state.sig_assurance_changed.connect(self.mission_panel.set_assurance)
        self.state.sig_alert_changed.connect(self.alert_panel.set_alert)
        self.state.sig_timeline_added.connect(self.timeline_panel.add_event)
        self.state.sig_health_changed.connect(self.health_panel.update_health)

    @Slot(dict)
    def _handle_link_update(self, status: Dict[str, Any]) -> None:
        self.header_panel.update_status(status)
        self.health_panel.update_link(status)
        self.video_panel.set_connected(status.get("video_connected", False))
        if self.state.is_simulation:
            self.header_panel.set_simulation_mode(True)

    # Callbacks from ConnectionManager threads (invoked safely via state or direct UI updates)
    def _on_video_frame(self, frame: np.ndarray, metrics: Dict[str, float]) -> None:
        self.video_panel.set_frame(frame, metrics)

    def _on_telemetry_event(self, event: GroundEvent, latency_ms: float) -> None:
        self.state.process_event(event, latency_ms)

    def _on_link_status(self, status: Dict[str, Any]) -> None:
        self.state.update_link(status)

    def show_evidence_dialog(self, evidence_id: str) -> None:
        """Display modal evidence bundle viewer."""
        dialog = EvidenceViewerDialog(evidence_id, parent=self)
        dialog.exec()

    def closeEvent(self, event: Any) -> None:
        """Clean shutdown of background connections."""
        logger.info("Closing Ground Monitor window...")
        self.conn_mgr.disconnect_all()
        super().closeEvent(event)
