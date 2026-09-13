# ==============================================================================
# ASTRA-EA Ground Monitor Header Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Top telemetry banner displaying connection status, channel health, and simulation indicators."""

from __future__ import annotations

from typing import Any, Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from apps.ground_monitor.theme import (
    COLOR_BORDER,
    COLOR_LINK_DEGRADED,
    COLOR_LINK_OFFLINE,
    COLOR_LINK_ONLINE,
)


class HeaderPanel(QFrame):
    """Telemetry banner at top of Ground Monitor."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setObjectName("headerPanel")
        self.setFixedHeight(68)
        self.setStyleSheet(f"""
            QFrame#headerPanel {{
                background-color: #0b1322;
                border-bottom: 2px solid {COLOR_BORDER};
                padding: 4px 16px;
            }}
        """)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Left: Identity
        left_layout = QVBoxLayout()
        title = QLabel("ASTRA-EA GROUND OBSERVABILITY CONSOLE")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        subtitle = QLabel("REMOTE EXPERIMENT OBSERVATION & SITUATIONAL AWARENESS (READ-ONLY)")
        subtitle.setStyleSheet("font-size: 10px; color: #94a3b8;")
        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)
        layout.addLayout(left_layout)

        layout.addStretch()

        # Center: Simulation Badge (hidden by default)
        self.sim_badge = QLabel("SIMULATION MODE")
        self.sim_badge.setStyleSheet("""
            background-color: #7c3aed;
            color: white;
            font-weight: bold;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 4px;
            border: 1px solid #a78bfa;
        """)
        self.sim_badge.setVisible(False)
        layout.addWidget(self.sim_badge)

        layout.addSpacing(15)

        # Right: Telemetry Badges
        # Video channel badge
        self.vid_badge = QLabel("VID: OFFLINE")
        self.vid_badge.setStyleSheet(self._badge_style(COLOR_LINK_OFFLINE))
        layout.addWidget(self.vid_badge)

        # Event channel badge
        self.evt_badge = QLabel("EVT: OFFLINE")
        self.evt_badge.setStyleSheet(self._badge_style(COLOR_LINK_OFFLINE))
        layout.addWidget(self.evt_badge)

        # Heartbeat age badge
        self.hb_badge = QLabel("HB: --")
        self.hb_badge.setStyleSheet(self._badge_style("#1e293b", text_color="#94a3b8"))
        layout.addWidget(self.hb_badge)

        # Master Link Badge
        self.link_badge = QLabel("LINK: OFFLINE")
        self.link_badge.setStyleSheet(self._master_badge_style(COLOR_LINK_OFFLINE))
        layout.addWidget(self.link_badge)

    def _badge_style(self, bg_color: str, text_color: str = "#ffffff") -> str:
        return f"""
            background-color: {bg_color};
            color: {text_color};
            font-weight: bold;
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 3px;
        """

    def _master_badge_style(self, bg_color: str) -> str:
        return f"""
            background-color: {bg_color};
            color: #ffffff;
            font-weight: bold;
            font-size: 13px;
            padding: 6px 14px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        """

    def set_simulation_mode(self, is_sim: bool) -> None:
        self.sim_badge.setVisible(is_sim)

    def update_status(self, status: Dict[str, Any]) -> None:
        overall = status.get("overall", "OFFLINE")
        quality = status.get("quality", "OFFLINE")
        vid_conn = status.get("video_connected", False)
        evt_conn = status.get("events_connected", False)
        hb_age = status.get("heartbeat_age_seconds", 999.0)

        # Video badge
        if vid_conn:
            fps = status.get("stream_fps", 0.0)
            self.vid_badge.setText(f"VID: {fps:.0f} FPS" if fps > 0 else "VID: ONLINE")
            self.vid_badge.setStyleSheet(self._badge_style(COLOR_LINK_ONLINE))
        else:
            self.vid_badge.setText("VID: OFFLINE")
            self.vid_badge.setStyleSheet(self._badge_style(COLOR_LINK_OFFLINE))

        # Event badge
        if evt_conn:
            self.evt_badge.setText("EVT: ONLINE")
            self.evt_badge.setStyleSheet(self._badge_style(COLOR_LINK_ONLINE))
        else:
            self.evt_badge.setText("EVT: OFFLINE")
            self.evt_badge.setStyleSheet(self._badge_style(COLOR_LINK_OFFLINE))

        # Heartbeat age
        if hb_age < 900.0:
            self.hb_badge.setText(f"HB: {hb_age:.1f}s")
            color = COLOR_LINK_ONLINE if hb_age < 2.5 else COLOR_LINK_DEGRADED
            self.hb_badge.setStyleSheet(self._badge_style("#1e293b", text_color=color))
        else:
            self.hb_badge.setText("HB: --")
            self.hb_badge.setStyleSheet(self._badge_style("#1e293b", text_color="#94a3b8"))

        # Master link badge
        if overall == "ONLINE":
            self.link_badge.setText("LINK: 🟢 ONLINE")
            self.link_badge.setStyleSheet(self._master_badge_style(COLOR_LINK_ONLINE))
        elif overall == "PARTIAL":
            self.link_badge.setText("LINK: 🟡 PARTIAL")
            self.link_badge.setStyleSheet(self._master_badge_style(COLOR_LINK_DEGRADED))
        else:
            self.link_badge.setText("LINK: 🔴 OFFLINE")
            self.link_badge.setStyleSheet(self._master_badge_style(COLOR_LINK_OFFLINE))
