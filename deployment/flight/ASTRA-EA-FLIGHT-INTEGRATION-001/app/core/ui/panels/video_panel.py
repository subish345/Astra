# ==============================================================================
# ASTRA-EA Live Video Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Live camera visualization panel with operational overlays and developer toggles."""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.ui.theme import Colors, MAIN_STYLESHEET


class VideoPanel(QFrame):
    """Panel rendering the live video feed with camera telemetry and layer toggles."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")

        self.show_pose = True
        self.show_hands = True
        self.show_objects = True
        self.show_tracking = True
        self.show_interaction = True
        self.show_debug = False

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header bar with Camera Info & Status
        hdr_layout = QHBoxLayout()
        self.lbl_title = QLabel("OPTICAL TELEMETRY — LIVE EXPERIMENT FEED")
        self.lbl_title.setObjectName("SectionTitle")
        hdr_layout.addWidget(self.lbl_title)

        hdr_layout.addStretch()

        self.lbl_camera_info = QLabel("CAMERA: camera_0 | PROFILE: VIEW_LEFT | 1280x720")
        self.lbl_camera_info.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; font-weight: bold;")
        hdr_layout.addWidget(self.lbl_camera_info)

        self.lbl_cam_status = QLabel("🟢 ONLINE")
        self.lbl_cam_status.setStyleSheet(
            f"background-color: {Colors.GREEN_BG}; color: {Colors.GREEN_BRIGHT}; "
            f"border: 1px solid {Colors.GREEN}; border-radius: 3px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        )
        hdr_layout.addWidget(self.lbl_cam_status)
        layout.addLayout(hdr_layout)

        # Video Frame Surface
        self.video_surface = QLabel()
        self.video_surface.setAlignment(Qt.AlignCenter)
        self.video_surface.setStyleSheet(f"background-color: #000000; border: 1px solid {Colors.BORDER_MUTED}; border-radius: 4px;")
        self.video_surface.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_surface.setMinimumSize(480, 270)
        self.video_surface.setText("AWAITING VIDEO STREAM...")
        layout.addWidget(self.video_surface, stretch=1)

        # Controls & Overlay Toggles
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(4)

        lbl_layers = QLabel("OVERLAYS:")
        lbl_layers.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED}; font-weight: bold;")
        ctrl_layout.addWidget(lbl_layers)

        self.btn_pose = QPushButton("Pose")
        self.btn_pose.setCheckable(True)
        self.btn_pose.setChecked(True)
        self.btn_pose.toggled.connect(self._toggle_pose)
        ctrl_layout.addWidget(self.btn_pose)

        self.btn_hands = QPushButton("Hands")
        self.btn_hands.setCheckable(True)
        self.btn_hands.setChecked(True)
        self.btn_hands.toggled.connect(self._toggle_hands)
        ctrl_layout.addWidget(self.btn_hands)

        self.btn_objects = QPushButton("Objects")
        self.btn_objects.setCheckable(True)
        self.btn_objects.setChecked(True)
        self.btn_objects.toggled.connect(self._toggle_objects)
        ctrl_layout.addWidget(self.btn_objects)

        self.btn_tracking = QPushButton("Tracking")
        self.btn_tracking.setCheckable(True)
        self.btn_tracking.setChecked(True)
        self.btn_tracking.toggled.connect(self._toggle_tracking)
        ctrl_layout.addWidget(self.btn_tracking)

        self.btn_interaction = QPushButton("Interaction")
        self.btn_interaction.setCheckable(True)
        self.btn_interaction.setChecked(True)
        self.btn_interaction.toggled.connect(self._toggle_interaction)
        ctrl_layout.addWidget(self.btn_interaction)

        ctrl_layout.addStretch()

        self.btn_debug = QPushButton("Debug Mode")
        self.btn_debug.setCheckable(True)
        self.btn_debug.setChecked(False)
        self.btn_debug.toggled.connect(self._toggle_debug)
        self.btn_debug.setStyleSheet(f"font-size: 11px; font-weight: bold; border-color: {Colors.BLUE};")
        ctrl_layout.addWidget(self.btn_debug)

        layout.addLayout(ctrl_layout)

        # Perception summary entity indicators
        ent_layout = QHBoxLayout()
        ent_layout.setSpacing(8)
        self.lbl_ent_astro = QLabel("Astronaut: —")
        self.lbl_ent_red = QLabel("Red Box: —")
        self.lbl_ent_yellow = QLabel("Yellow Box: —")
        self.lbl_ent_main = QLabel("Work Station: —")

        for lbl in (self.lbl_ent_astro, self.lbl_ent_red, self.lbl_ent_yellow, self.lbl_ent_main):
            lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
            ent_layout.addWidget(lbl)
        ent_layout.addStretch()
        layout.addLayout(ent_layout)

    def _toggle_pose(self, checked: bool) -> None:
        self.show_pose = checked

    def _toggle_hands(self, checked: bool) -> None:
        self.show_hands = checked

    def _toggle_objects(self, checked: bool) -> None:
        self.show_objects = checked

    def _toggle_tracking(self, checked: bool) -> None:
        self.show_tracking = checked

    def _toggle_interaction(self, checked: bool) -> None:
        self.show_interaction = checked

    def _toggle_debug(self, checked: bool) -> None:
        self.show_debug = checked

    def update_frame(self, frame: np.ndarray, perception_state: Optional[object] = None) -> None:
        """Render new video frame onto the video surface."""
        if frame is None or frame.size == 0:
            return

        h, w, ch = frame.shape
        bytes_per_line = ch * w

        # OpenCV BGR to RGB conversion
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.video_surface.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_surface.setPixmap(scaled_pixmap)

        # Update perception entity statuses if state provided
        if perception_state and hasattr(perception_state, "tracks"):
            tracked_labels = {t.label.upper() for t in perception_state.tracks}
            has_person = bool(hasattr(perception_state, "pose") and perception_state.pose)

            self.lbl_ent_astro.setText(f"Astronaut: {'✓' if has_person else '—'}")
            self.lbl_ent_astro.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_person else Colors.TEXT_MUTED}; font-weight: bold;")

            has_red = any("RED" in l for l in tracked_labels)
            self.lbl_ent_red.setText(f"Red Box: {'✓' if has_red else '—'}")
            self.lbl_ent_red.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_red else Colors.TEXT_MUTED}; font-weight: bold;")

            has_yellow = any("YELLOW" in l for l in tracked_labels)
            self.lbl_ent_yellow.setText(f"Yellow Box: {'✓' if has_yellow else '—'}")
            self.lbl_ent_yellow.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_yellow else Colors.TEXT_MUTED}; font-weight: bold;")

            has_main = any("MAIN" in l or "BOX" in l for l in tracked_labels)
            self.lbl_ent_main.setText(f"Work Station: {'✓' if has_main else '—'}")
            self.lbl_ent_main.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_main else Colors.TEXT_MUTED}; font-weight: bold;")

    def set_camera_profile(self, profile_name: str, source_name: str = "0") -> None:
        """Update camera telemetry header."""
        self.lbl_camera_info.setText(f"CAMERA: camera_{source_name} | PROFILE: {profile_name.upper()} | 1280x720")
