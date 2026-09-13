# ==============================================================================
# ASTRA-EA Ground Health Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Subsystem telemetry, network health, and heartbeat latency monitor."""

from __future__ import annotations

from typing import Any, Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from apps.ground_monitor.theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_VERIFIED,
)


class HealthPanel(QFrame):
    """Subsystem telemetry and link health monitor."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setObjectName("healthPanel")
        self.setStyleSheet(f"""
            QFrame#healthPanel {{
                background-color: #0d1527;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        title = QLabel("SYSTEM HEALTH & LINK METRICS")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(6)

        # 1. Video FPS
        self.lbl_fps_val = self._create_metric_card(grid, 0, 0, "STREAM FPS", "0.0")

        # 2. Heartbeat Age
        self.lbl_hb_val = self._create_metric_card(grid, 0, 1, "HEARTBEAT AGE", "--")

        # 3. Reconnects
        self.lbl_reconn_val = self._create_metric_card(grid, 1, 0, "RECONNECTS", "0")

        # 4. Link Quality
        self.lbl_quality_val = self._create_metric_card(grid, 1, 1, "LINK QUALITY", "OFFLINE")

        layout.addLayout(grid)

        # Onboard Subsystems Section
        sub_title = QLabel("ONBOARD SUBSYSTEMS")
        sub_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; margin-top: 4px;")
        layout.addWidget(sub_title)

        sub_layout = QHBoxLayout()
        self.badge_perc = self._create_subsystem_badge("PERC: OK")
        self.badge_cam = self._create_subsystem_badge("CAM: OK")
        self.badge_ass = self._create_subsystem_badge("ASSUR: OK")
        self.badge_stor = self._create_subsystem_badge("STOR: OK")

        sub_layout.addWidget(self.badge_perc)
        sub_layout.addWidget(self.badge_cam)
        sub_layout.addWidget(self.badge_ass)
        sub_layout.addWidget(self.badge_stor)
        layout.addLayout(sub_layout)

        layout.addStretch()

    def _create_metric_card(self, grid: QGridLayout, row: int, col: int, label: str, default_val: str) -> QLabel:
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 4px;")
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(6, 4, 6, 4)
        f_layout.setSpacing(2)

        lbl_title = QLabel(label)
        lbl_title.setStyleSheet("font-size: 9px; font-weight: bold; color: #94a3b8;")
        f_layout.addWidget(lbl_title)

        lbl_val = QLabel(default_val)
        lbl_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLOR_TEXT_PRIMARY};")
        f_layout.addWidget(lbl_val)

        grid.addWidget(frame, row, col)
        return lbl_val

    def _create_subsystem_badge(self, text: str) -> QLabel:
        badge = QLabel(text)
        badge.setStyleSheet("""
            background-color: #0f231c;
            color: #10b981;
            font-size: 10px;
            font-weight: bold;
            padding: 3px 6px;
            border-radius: 3px;
            border: 1px solid #10b981;
        """)
        badge.setAlignment(Qt.AlignCenter)
        return badge

    def update_link(self, status: Dict[str, Any]) -> None:
        fps = status.get("stream_fps", 0.0)
        self.lbl_fps_val.setText(f"{fps:.1f} FPS")

        hb_age = status.get("heartbeat_age_seconds", 999.0)
        if hb_age < 900.0:
            self.lbl_hb_val.setText(f"{hb_age:.1f}s")
        else:
            self.lbl_hb_val.setText("--")

        reconn = status.get("reconnect_count", 0)
        self.lbl_reconn_val.setText(str(reconn))

        quality = status.get("quality", "OFFLINE")
        self.lbl_quality_val.setText(quality)
        if quality == "GOOD":
            self.lbl_quality_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLOR_VERIFIED};")
        elif quality == "DEGRADED":
            self.lbl_quality_val.setStyleSheet("font-size: 13px; font-weight: bold; color: #f59e0b;")
        else:
            self.lbl_quality_val.setStyleSheet("font-size: 13px; font-weight: bold; color: #64748b;")

    def update_health(self, metrics: Dict[str, Any]) -> None:
        # Update subsystem indicators if present
        if "perception" in metrics:
            st = str(metrics["perception"]).upper()
            self.badge_perc.setText(f"PERC: {st}")
        if "camera" in metrics:
            st = str(metrics["camera"]).upper()
            self.badge_cam.setText(f"CAM: {st}")
        if "assurance" in metrics:
            st = str(metrics["assurance"]).upper()
            self.badge_ass.setText(f"ASSUR: {st}")
        if "storage" in metrics:
            st = str(metrics["storage"]).upper()
            self.badge_stor.setText(f"STOR: {st}")
