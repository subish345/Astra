# ==============================================================================
# ASTRA-EA Primary Mission Console View
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Primary operational console view integrating video, status, steps, evidence, and timeline."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.ui.panels.evidence_panel import EvidencePanel
from core.ui.panels.health_panel import HealthPanel
from core.ui.panels.progress_panel import ProgressPanel
from core.ui.panels.status_panel import StatusPanel
from core.ui.panels.step_panel import StepPanel
from core.ui.panels.timeline_panel import TimelinePanel
from core.ui.panels.video_panel import VideoPanel


class ConsoleView(QWidget):
    """Primary operational console screen for astronaut experiment execution."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(8)

        # Top Splitter: Left (Video + Health) / Right (Status + Step + Progress)
        top_splitter = QSplitter(Qt.Horizontal)

        # Left Column
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.video_panel = VideoPanel(self)
        left_layout.addWidget(self.video_panel, stretch=3)

        self.health_panel = HealthPanel(self)
        left_layout.addWidget(self.health_panel, stretch=1)

        top_splitter.addWidget(left_container)

        # Right Column
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        self.status_panel = StatusPanel(self)
        right_layout.addWidget(self.status_panel)

        self.step_panel = StepPanel(self)
        right_layout.addWidget(self.step_panel)

        self.progress_panel = ProgressPanel(self)
        right_layout.addWidget(self.progress_panel, stretch=1)

        top_splitter.addWidget(right_container)
        top_splitter.setStretchFactor(0, 6)
        top_splitter.setStretchFactor(1, 4)

        # Bottom Splitter: Left (Evidence) / Right (Timeline)
        bottom_splitter = QSplitter(Qt.Horizontal)

        self.evidence_panel = EvidencePanel(self)
        bottom_splitter.addWidget(self.evidence_panel)

        self.timeline_panel = TimelinePanel(self)
        bottom_splitter.addWidget(self.timeline_panel)

        bottom_splitter.setStretchFactor(0, 5)
        bottom_splitter.setStretchFactor(1, 5)

        # Master Vertical Splitter
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.addWidget(top_splitter)
        v_splitter.addWidget(bottom_splitter)
        v_splitter.setStretchFactor(0, 7)
        v_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(v_splitter)
