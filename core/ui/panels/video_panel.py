# ==============================================================================
# Pramman Live Video Panel
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
        self.live_observe = False
        self.mirror_camera = False

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

        self.lbl_cam_status = QLabel("NO FRAMES")
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

        self.btn_mirror = QPushButton("🪞 Mirror")
        self.btn_mirror.setCheckable(True)
        self.btn_mirror.setChecked(False)
        self.btn_mirror.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.BG_SURFACE}; color: {Colors.TEXT_PRIMARY}; "
            f"border: 1px solid {Colors.BORDER_DEFAULT}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {Colors.BG_HOVER}; }} "
            f"QPushButton:checked {{ background-color: #1e3a5f; color: #93c5fd; border: 1px solid #3b82f6; }}"
        )
        self.btn_mirror.setToolTip("Mirror camera view horizontally (natural selfie / mirror view)")
        self.btn_mirror.toggled.connect(self._toggle_mirror)
        ctrl_layout.addWidget(self.btn_mirror)

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
        self.lbl_ent_specimen = QLabel("Specimen Container: —")

        for lbl in (self.lbl_ent_astro, self.lbl_ent_red, self.lbl_ent_yellow, self.lbl_ent_main, self.lbl_ent_specimen):
            lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
            ent_layout.addWidget(lbl)
        ent_layout.addStretch()
        layout.addLayout(ent_layout)
        self.lbl_live_objects = QLabel("Recognized objects: waiting for frames")
        self.lbl_live_objects.setWordWrap(True)
        self.lbl_live_objects.hide()
        layout.addWidget(self.lbl_live_objects)
        self.lbl_live_activity = QLabel("")
        self.lbl_live_activity.setWordWrap(True)
        self.lbl_live_activity.hide()
        layout.addWidget(self.lbl_live_activity)

    def set_live_observe(self, enabled):
        self.live_observe = enabled
        for label in (self.lbl_ent_red, self.lbl_ent_yellow, self.lbl_ent_main, self.lbl_ent_specimen):
            label.setVisible(not enabled)
        self.lbl_live_objects.setVisible(enabled)
        self.lbl_live_activity.setVisible(enabled)

    def set_source_status(self, status):
        self.lbl_cam_status.setText(status)
        color = Colors.GREEN_BRIGHT if status == "ONLINE" else Colors.TEXT_MUTED
        self.lbl_cam_status.setStyleSheet(f"color: {color}; font-weight: bold;")
        if status not in {"ONLINE", "PAUSED"}:
            self.video_surface.clear()
            if status == "COMPLETED":
                self.video_surface.setText("✔ VIDEO REPLAY & VERIFICATION COMPLETED\n\nClick ▶ START to replay again or ⏹ STOP to reset to camera")
            else:
                self.video_surface.setText(status)
            self.lbl_live_objects.setText("Recognized objects: waiting for fresh frames")
            self.lbl_live_activity.setText("")

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

    def _toggle_mirror(self, checked: bool) -> None:
        self.mirror_camera = checked

    def set_mirrored(self, mirrored: bool) -> None:
        self.mirror_camera = mirrored
        if hasattr(self, "btn_mirror"):
            self.btn_mirror.blockSignals(True)
            self.btn_mirror.setChecked(mirrored)
            self.btn_mirror.blockSignals(False)

    def update_frame(self, frame: np.ndarray, perception_state: Optional[object] = None) -> None:
        """Render new video frame onto the video surface."""
        if frame is None or frame.size == 0:
            return
        self.set_source_status("ONLINE")

        h, w, ch = frame.shape
        if perception_state:
            self.lbl_camera_info.setText(f"CAMERA: {perception_state.source_id} | {w}x{h}")
            if self.live_observe:
                objects = getattr(perception_state, "objects", [])
                names = sorted({f"{obj.class_name} ({obj.confidence:.0%})" for obj in objects
                                if obj.class_name.lower() not in {"person", "astronaut"}})
                self.lbl_live_objects.setText("Recognized objects: " + (", ".join(names) if names else "none confidently recognized"))
                metadata = getattr(perception_state, "metadata", {})
                self.lbl_live_activity.setText(metadata.get("live_observation", "Waiting for hand observations"))
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
            tracked_labels = {t.class_name.upper() for t in perception_state.tracks if t.is_active and t.lost_frames == 0}
            has_person = bool(getattr(perception_state, "poses", []))

            self.lbl_ent_astro.setText(f"Astronaut: {'✓' if has_person else '—'}")
            self.lbl_ent_astro.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_person else Colors.TEXT_MUTED}; font-weight: bold;")

            has_red = any("RED" in l for l in tracked_labels)
            self.lbl_ent_red.setText(f"Red Box: {'✓' if has_red else '—'}")
            self.lbl_ent_red.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_red else Colors.TEXT_MUTED}; font-weight: bold;")

            has_yellow = any("YELLOW" in l for l in tracked_labels)
            self.lbl_ent_yellow.setText(f"Yellow Box: {'✓' if has_yellow else '—'}")
            self.lbl_ent_yellow.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_yellow else Colors.TEXT_MUTED}; font-weight: bold;")

            has_main = "MAIN_BOX" in tracked_labels
            self.lbl_ent_main.setText(f"Work Station: {'✓' if has_main else '—'}")
            self.lbl_ent_main.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_main else Colors.TEXT_MUTED}; font-weight: bold;")

            has_specimen = bool(tracked_labels & {"RED_BOX", "YELLOW_BOX", "MAIN_BOX"})
            self.lbl_ent_specimen.setText(f"Specimen Container: {'✓' if has_specimen else '—'}")
            self.lbl_ent_specimen.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN_BRIGHT if has_specimen else Colors.TEXT_MUTED}; font-weight: bold;")

    def set_camera_profile(self, profile_name: str, source_name: str = "0") -> None:
        """Update camera telemetry header."""
        self.lbl_camera_info.setText(f"CAMERA: camera_{source_name} | PROFILE: {profile_name.upper()} | 1280x720")
