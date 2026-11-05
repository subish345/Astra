# ==============================================================================
# ASTRA-EA Mission Session & Header Bar
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Top mission header bar providing session lifecycle controls and offline indicators."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from core.ui.theme import Colors


class SessionBar(QFrame):
    """Top operational bar presenting identity, experiment selector, and lifecycle buttons."""

    def __init__(
        self,
        on_start: Optional[Callable[[], None]] = None,
        on_pause: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self.on_start = on_start
        self.on_pause = on_pause
        self.on_stop = on_stop

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Brand / App Title
        self.lbl_brand = QLabel("ASTRA-EA")
        self.lbl_brand.setObjectName("HeaderTitle")
        self.lbl_brand.setStyleSheet(f"font-size: 16px; font-weight: 900; color: {Colors.BLUE_BRIGHT}; letter-spacing: 1px;")
        layout.addWidget(self.lbl_brand)

        # System Status Badge
        self.lbl_sys_status = QLabel("🟢 SYSTEM: NORMAL")
        self.lbl_sys_status.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {Colors.GREEN_BRIGHT}; "
            f"background-color: {Colors.GREEN_BG}; border: 1px solid {Colors.GREEN}; "
            f"border-radius: 3px; padding: 3px 8px;"
        )
        layout.addWidget(self.lbl_sys_status)

        # Offline Mode Indicator (Prominent judge-demo moment)
        self.lbl_offline = QLabel("📶 LOCAL / OFFLINE (AIR-GAPPED)")
        self.lbl_offline.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {Colors.AMBER_BRIGHT}; "
            f"background-color: {Colors.BG_SURFACE}; border: 1px solid {Colors.BORDER_DEFAULT}; "
            f"border-radius: 3px; padding: 3px 8px;"
        )
        layout.addWidget(self.lbl_offline)

        # Camera Profile Badge
        self.lbl_cam_profile = QLabel("📷 VIEW_LEFT")
        self.lbl_cam_profile.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {Colors.TEXT_PRIMARY}; "
            f"background-color: {Colors.BG_SURFACE}; border: 1px solid {Colors.BORDER_DEFAULT}; "
            f"border-radius: 3px; padding: 3px 8px;"
        )
        layout.addWidget(self.lbl_cam_profile)

        layout.addStretch()

        # Experiment Selector Dropdown
        lbl_exp = QLabel("EXPERIMENT:")
        lbl_exp.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {Colors.TEXT_MUTED};")
        layout.addWidget(lbl_exp)

        self.cmb_exp = QComboBox()
        self.cmb_exp.addItem("DEMO_EXP_001 (Material Handling v1.0.0)")
        self.cmb_exp.setStyleSheet(
            f"background-color: {Colors.BG_SURFACE}; color: {Colors.TEXT_PRIMARY}; "
            f"border: 1px solid {Colors.BORDER_DEFAULT}; border-radius: 3px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(self.cmb_exp)

        # Run ID Badge
        self.lbl_run_id = QLabel("RUN: RUN_001")
        self.lbl_run_id.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.lbl_run_id)

        # Session Lifecycle Controls
        self.btn_start = QPushButton("▶ START")
        self.btn_start.setObjectName("PrimaryButton")
        if self.on_start:
            self.btn_start.clicked.connect(self.on_start)
        layout.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸ PAUSE")
        if self.on_pause:
            self.btn_pause.clicked.connect(self.on_pause)
        layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setObjectName("DangerButton")
        if self.on_stop:
            self.btn_stop.clicked.connect(self.on_stop)
        layout.addWidget(self.btn_stop)

    def set_session_state(self, status: str, run_id: Optional[str] = None) -> None:
        """Update buttons and badges based on session state."""
        if run_id:
            self.lbl_run_id.setText(f"RUN: {run_id}")

        status_upper = status.upper()
        if status_upper in ("RUNNING", "ACTIVE"):
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.lbl_sys_status.setText("🟢 ACTIVE RUN")
            self.lbl_sys_status.setStyleSheet(
                f"font-size: 10px; font-weight: bold; color: {Colors.GREEN_BRIGHT}; "
                f"background-color: {Colors.GREEN_BG}; border: 1px solid {Colors.GREEN}; "
                f"border-radius: 3px; padding: 3px 8px;"
            )
        elif status_upper == "PAUSED":
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.lbl_sys_status.setText("🟡 PAUSED")
            self.lbl_sys_status.setStyleSheet(
                f"font-size: 10px; font-weight: bold; color: {Colors.AMBER_BRIGHT}; "
                f"background-color: {Colors.AMBER_BG}; border: 1px solid {Colors.AMBER}; "
                f"border-radius: 3px; padding: 3px 8px;"
            )
        else:  # READY, COMPLETED, FAILED
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.lbl_sys_status.setText("🟢 SYSTEM: NORMAL")
            self.lbl_sys_status.setStyleSheet(
                f"font-size: 10px; font-weight: bold; color: {Colors.GREEN_BRIGHT}; "
                f"background-color: {Colors.GREEN_BG}; border: 1px solid {Colors.GREEN}; "
                f"border-radius: 3px; padding: 3px 8px;"
            )

    def set_camera_profile(self, profile_name: str) -> None:
        """Update camera profile badge."""
        self.lbl_cam_profile.setText(f"📷 {profile_name.upper()}")
