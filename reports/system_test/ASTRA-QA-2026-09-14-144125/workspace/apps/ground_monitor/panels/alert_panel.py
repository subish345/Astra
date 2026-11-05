# ==============================================================================
# ASTRA-EA Ground Alert Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Real-time operational deviation alerts and closed-loop recovery guidance."""

from __future__ import annotations

from typing import Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from apps.ground_monitor.theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_DEVIATION,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_VERIFIED,
)


class AlertPanel(QFrame):
    """Surfaces active mission deviations and recovery directives to ground operators."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setObjectName("alertPanel")
        self.setStyleSheet(f"""
            QFrame#alertPanel {{
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
        layout.setSpacing(6)

        title = QLabel("MISSION ALERTS & RECOVERY DIRECTIVES")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        layout.addWidget(title)

        # Alert Card Container
        self.alert_card = QFrame()
        self.alert_card.setStyleSheet(f"""
            background-color: #081a14;
            border: 1px solid {COLOR_VERIFIED};
            border-radius: 4px;
            padding: 10px;
        """)
        ac_layout = QVBoxLayout(self.alert_card)
        ac_layout.setContentsMargins(8, 8, 8, 8)
        ac_layout.setSpacing(4)

        # Badge and Acknowledgement row (Section 17, 56)
        top_row = QHBoxLayout()
        self.alert_badge = QLabel("NOMINAL")
        self.alert_badge.setStyleSheet(f"background-color: {COLOR_VERIFIED}; color: white; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
        self.alert_badge.setFixedWidth(80)
        self.alert_badge.setAlignment(Qt.AlignCenter)
        top_row.addWidget(self.alert_badge)

        self.lifecycle_badge = QLabel("RESOLVED")
        self.lifecycle_badge.setStyleSheet("background-color: #059669; color: white; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
        self.lifecycle_badge.setFixedWidth(100)
        self.lifecycle_badge.setAlignment(Qt.AlignCenter)
        top_row.addWidget(self.lifecycle_badge)

        top_row.addStretch()

        self.ack_btn = QPushButton("ACKNOWLEDGE")
        self.ack_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                font-size: 10px;
                padding: 4px 10px;
                border-radius: 3px;
                border: none;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #334155; color: #64748b; }
        """)
        self.ack_btn.setEnabled(False)
        self.ack_btn.clicked.connect(self._handle_ack_clicked)
        top_row.addWidget(self.ack_btn)
        ac_layout.addLayout(top_row)

        self.alert_title = QLabel("No active deviations. Procedure execution nominal.")
        self.alert_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_PRIMARY};")
        self.alert_title.setWordWrap(True)
        ac_layout.addWidget(self.alert_title)

        self.recovery_label = QLabel("Recovery guidance: None required.")
        self.recovery_label.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        self.recovery_label.setWordWrap(True)
        ac_layout.addWidget(self.recovery_label)

        layout.addWidget(self.alert_card)

    def set_ack_callback(self, callback: Any) -> None:
        self._ack_callback = callback

    def _handle_ack_clicked(self) -> None:
        if hasattr(self, "_ack_callback") and self._ack_callback:
            self._ack_callback()
        self.set_lifecycle("ACKNOWLEDGED")

    def set_lifecycle(self, lifecycle: str) -> None:
        """Update acknowledgement lifecycle state (Section 17: ACKNOWLEDGED does not mean RESOLVED)."""
        lc = lifecycle.upper()
        if lc == "RECEIVED":
            self.lifecycle_badge.setText("RECEIVED")
            self.lifecycle_badge.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
            self.ack_btn.setEnabled(True)
        elif lc == "ACKNOWLEDGED":
            self.lifecycle_badge.setText("ACKNOWLEDGED")
            self.lifecycle_badge.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
            self.ack_btn.setEnabled(False)
        elif lc == "RESOLVED":
            self.lifecycle_badge.setText("RESOLVED")
            self.lifecycle_badge.setStyleSheet("background-color: #059669; color: white; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
            self.ack_btn.setEnabled(False)

    def set_alert(self, deviation: str, severity: str, recovery: str) -> None:
        """Update active alert card."""
        if not deviation:
            self.alert_card.setStyleSheet(f"background-color: #081a14; border: 1px solid {COLOR_VERIFIED}; border-radius: 4px; padding: 10px;")
            self.alert_badge.setText("NOMINAL")
            self.alert_badge.setStyleSheet(f"background-color: {COLOR_VERIFIED}; color: white; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
            self.alert_title.setText("No active deviations. Procedure execution nominal.")
            self.recovery_label.setText("Recovery guidance: None required.")
            return

        sev = severity.upper()
        if sev == "DANGER":
            bg = "#230e12"
            border = COLOR_DEVIATION
            badge_bg = COLOR_DEVIATION
            badge_text = "DEVIATION"
        elif sev == "WARNING":
            bg = "#231a0e"
            border = "#f59e0b"
            badge_bg = "#f59e0b"
            badge_text = "WARNING"
        else:
            bg = "#0e1828"
            border = "#38bdf8"
            badge_bg = "#0284c7"
            badge_text = "INFO"

        self.alert_card.setStyleSheet(f"background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 10px;")
        self.alert_badge.setText(badge_text)
        self.alert_badge.setStyleSheet(f"background-color: {badge_bg}; color: white; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 3px;")
        self.alert_title.setText(deviation)
        self.recovery_label.setText(f"Recovery Directive: {recovery}" if recovery else "Awaiting recovery action.")
