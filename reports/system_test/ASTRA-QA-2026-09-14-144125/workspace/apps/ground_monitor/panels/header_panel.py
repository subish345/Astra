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

        # Center: Dual Clocks & Operational Status (Phase 19)
        self.clock_badge = QLabel("MET: 00:00:00 | GRT: --:--:--")
        self.clock_badge.setStyleSheet("""
            background-color: #111c35;
            color: #38bdf8;
            font-family: monospace;
            font-size: 11px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #1e293b;
        """)
        layout.addWidget(self.clock_badge)

        self.op_status_badge = QLabel("NOMINAL")
        self.op_status_badge.setStyleSheet(self._badge_style("#059669"))
        layout.addWidget(self.op_status_badge)

        # Mode Badge (Section 6: FULL_REAL, HIL, SIMULATION, REPLAY)
        self.mode_badge = QLabel("MODE: FULL_REAL")
        self.mode_badge.setStyleSheet("""
            background-color: #059669;
            color: white;
            font-weight: bold;
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #10b981;
        """)
        layout.addWidget(self.mode_badge)

        # Simulation Badge (hidden by default)
        self.sim_badge = QLabel("SIMULATION")
        self.sim_badge.setStyleSheet("""
            background-color: #7c3aed;
            color: white;
            font-weight: bold;
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #a78bfa;
        """)
        self.sim_badge.setVisible(False)
        layout.addWidget(self.sim_badge)

        layout.addSpacing(10)

        # Right: Telemetry & Channel Badges (Section 55: VID, EVT, TLM, CMD separated)
        self.vid_badge = QLabel("VID: OFFLINE")
        self.vid_badge.setStyleSheet(self._badge_style(COLOR_LINK_OFFLINE))
        layout.addWidget(self.vid_badge)

        self.evt_badge = QLabel("EVT: OFFLINE")
        self.evt_badge.setStyleSheet(self._badge_style(COLOR_LINK_OFFLINE))
        layout.addWidget(self.evt_badge)

        self.tlm_badge = QLabel("TLM: ONLINE")
        self.tlm_badge.setStyleSheet(self._badge_style(COLOR_LINK_ONLINE))
        layout.addWidget(self.tlm_badge)

        self.cmd_badge = QLabel("CMD: TBD")
        self.cmd_badge.setStyleSheet(self._badge_style("#334155", text_color="#94a3b8"))
        layout.addWidget(self.cmd_badge)

        self.hb_badge = QLabel("HB: --")
        self.hb_badge.setStyleSheet(self._badge_style("#1e293b", text_color="#94a3b8"))
        layout.addWidget(self.hb_badge)

        self.sync_badge = QLabel("SYNC: OK")
        self.sync_badge.setStyleSheet(self._badge_style("#0369a1"))
        layout.addWidget(self.sync_badge)

        # Master Link Badge
        self.link_badge = QLabel("LINK: OFFLINE")
        self.link_badge.setStyleSheet(self._master_badge_style(COLOR_LINK_OFFLINE))
        layout.addWidget(self.link_badge)

    def set_operational_status(self, status: str) -> None:
        """Update high-level mission operational status (Section 14)."""
        color_map = {
            "NOMINAL": "#059669",
            "ATTENTION": "#d97706",
            "DEGRADED": "#ea580c",
            "ANOMALY": "#dc2626",
            "RECOVERY": "#2563eb",
            "COMPLETE": "#16a34a",
        }
        bg = color_map.get(status.upper(), "#475569")
        self.op_status_badge.setText(status.upper())
        self.op_status_badge.setStyleSheet(self._badge_style(bg))

    def set_reconciliation_status(self, rec_dict: Dict[str, Any]) -> None:
        """Update sequence sync & gap status (Section 43, 44)."""
        is_synced = rec_dict.get("is_synced", True)
        gaps = rec_dict.get("missing_gaps", [])
        if is_synced and not gaps:
            self.sync_badge.setText("SYNC: OK")
            self.sync_badge.setStyleSheet(self._badge_style("#0369a1"))
        else:
            self.sync_badge.setText(f"SYNC: GAP ({len(gaps)})")
            self.sync_badge.setStyleSheet(self._badge_style("#b91c1c"))

    def set_clocks(self, met_seconds: float, grt_utc: str) -> None:
        """Update dual clocks: Onboard MET and Ground Receipt Time (Section 13)."""
        mins, secs = divmod(int(met_seconds), 60)
        hrs, mins = divmod(mins, 60)
        met_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        time_part = grt_utc.split("T")[-1][:8] if "T" in grt_utc else grt_utc[:8]
        self.clock_badge.setText(f"MET: {met_str} | GRT: {time_part}")

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

    def set_mode(self, mode: str) -> None:
        """Update operational mode banner per Section 6 (FULL_REAL, HIL, SIMULATION, REPLAY)."""
        mode_upper = mode.upper()
        mode_colors = {
            "FULL_REAL": ("#059669", "#10b981"),
            "HIL": ("#2563eb", "#3b82f6"),
            "SIMULATION": ("#7c3aed", "#a78bfa"),
            "REPLAY": ("#d97706", "#f59e0b"),
        }
        bg, border = mode_colors.get(mode_upper, ("#7c3aed", "#a78bfa"))
        self.mode_badge.setText(f"MODE: {mode_upper}")
        self.mode_badge.setStyleSheet(f"""
            background-color: {bg};
            color: #ffffff;
            font-weight: bold;
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid {border};
        """)
        if mode_upper == "SIMULATION":
            self.sim_badge.setVisible(True)
        else:
            self.sim_badge.setVisible(False)

    def set_simulation_mode(self, is_sim: bool) -> None:
        self.sim_badge.setVisible(is_sim)
        if is_sim:
            self.set_mode("SIMULATION")

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
