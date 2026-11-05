# ==============================================================================
# Pramman Operational Settings View
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Safe configuration view for operators and astronauts (camera, audio, overlays)."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.ui.theme import Colors


class SettingsView(QWidget):
    """View exposing safe operational settings without altering core AI internals."""

    def __init__(self, on_test_voice: Optional[Callable[[], None]] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.on_test_voice = on_test_voice
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header Bar
        hdr_frame = QFrame()
        hdr_frame.setObjectName("PanelFrame")
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(12, 8, 12, 8)

        lbl_title = QLabel("MISSION CONSOLE CONFIGURATION")
        lbl_title.setObjectName("HeaderTitle")
        hdr_layout.addWidget(lbl_title)
        layout.addWidget(hdr_frame)

        # Settings Grid
        cfg_frame = QFrame()
        cfg_frame.setObjectName("PanelFrame")
        cfg_layout = QGridLayout(cfg_frame)
        cfg_layout.setContentsMargins(16, 14, 16, 14)
        cfg_layout.setSpacing(12)

        # Optical Source
        lbl_src = QLabel("Optical Camera Source:")
        lbl_src.setStyleSheet("font-weight: bold;")
        self.txt_source = QLineEdit("0")
        self.txt_source.setPlaceholderText("0 or video file path")
        cfg_layout.addWidget(lbl_src, 0, 0)
        cfg_layout.addWidget(self.txt_source, 0, 1)
        self.btn_video = QPushButton("Choose video…")
        self.btn_video.clicked.connect(self._choose_video)
        cfg_layout.addWidget(self.btn_video, 0, 2)

        # Camera Viewpoint Profile
        lbl_prof = QLabel("Camera Viewpoint Profile:")
        lbl_prof.setStyleSheet("font-weight: bold;")
        self.cmb_profile = QComboBox()
        self.cmb_profile.addItems(["VIEW_LEFT (Left-side experiment view)", "VIEW_RIGHT (Right-side experiment view)", "VIEW_CENTER (Centered overhead view)"])
        cfg_layout.addWidget(lbl_prof, 1, 0)
        cfg_layout.addWidget(self.cmb_profile, 1, 1)
        self.cmb_profile.setToolTip("Viewpoint calibration, not a camera selector. Use source 0, 1, etc. to choose a camera.")

        # Voice Speech Rate
        lbl_rate = QLabel("Voice Speech Rate (WPM):")
        lbl_rate.setStyleSheet("font-weight: bold;")
        self.slider_rate = QSlider(Qt.Horizontal)
        self.slider_rate.setRange(120, 220)
        self.slider_rate.setValue(165)
        cfg_layout.addWidget(lbl_rate, 2, 0)
        cfg_layout.addWidget(self.slider_rate, 2, 1)

        # Voice Volume
        lbl_vol = QLabel("Voice Output Volume:")
        lbl_vol.setStyleSheet("font-weight: bold;")
        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(90)
        cfg_layout.addWidget(lbl_vol, 3, 0)
        cfg_layout.addWidget(self.slider_vol, 3, 1)

        # Test Voice Button
        self.btn_voice_test = QPushButton("Test Audio Guidance")
        if self.on_test_voice:
            self.btn_voice_test.clicked.connect(self.on_test_voice)
        cfg_layout.addWidget(self.btn_voice_test, 4, 1)
        self.btn_apply_source = QPushButton("Apply source & restart")
        cfg_layout.addWidget(self.btn_apply_source, 5, 1)
        self.lbl_source_status = QLabel("Camera index (0, 1, …) or a local video file. STOP releases the source.")
        self.lbl_source_status.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_source_status, 6, 0, 1, 3)

        layout.addWidget(cfg_frame)
        layout.addStretch()

    def _choose_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose experiment video", "", "Videos (*.mp4 *.avi *.mkv *.webm *.mov);;All files (*)")
        if path:
            self.txt_source.setText(path)
