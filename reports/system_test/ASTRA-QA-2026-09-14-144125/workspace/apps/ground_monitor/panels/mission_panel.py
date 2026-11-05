# ==============================================================================
# ASTRA-EA Ground Mission Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Mission metadata, active step progress, and Tri-State Assurance decision display."""

from __future__ import annotations

from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from apps.ground_monitor.theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_DEVIATION,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_UNCERTAIN,
    COLOR_VERIFIED,
)


class MissionPanel(QFrame):
    """Panel displaying experiment status, step progress, and tri-state assurance."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionPanel")
        self.setStyleSheet(f"""
            QFrame#missionPanel {{
                background-color: #0d1527;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # 1. Mission Header Card
        header_card = QFrame()
        header_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 6px;")
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel("MISSION STATUS")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        h_layout.addWidget(title)

        meta_row = QHBoxLayout()
        self.exp_label = QLabel("EXP: DEMO_EXP_001")
        self.exp_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {COLOR_TEXT_PRIMARY};")
        self.run_label = QLabel("RUN: RUN_0001")
        self.run_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        meta_row.addWidget(self.exp_label)
        meta_row.addStretch()
        meta_row.addWidget(self.run_label)
        h_layout.addLayout(meta_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(25)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        h_layout.addWidget(self.progress_bar)

        self.progress_text = QLabel("Step 1 of 4 (25%)")
        self.progress_text.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_MUTED};")
        self.progress_text.setAlignment(Qt.AlignRight)
        h_layout.addWidget(self.progress_text)

        layout.addWidget(header_card)

        # 2. Active Step Card
        step_card = QFrame()
        step_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 6px;")
        s_layout = QVBoxLayout(step_card)
        s_layout.setContentsMargins(8, 6, 8, 6)

        s_title = QLabel("CURRENT EXPERIMENT STEP")
        s_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8;")
        s_layout.addWidget(s_title)

        self.step_id_label = QLabel("STEP_01")
        self.step_id_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        s_layout.addWidget(self.step_id_label)

        self.step_desc_label = QLabel("Approach Experiment Workstation")
        self.step_desc_label.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_PRIMARY};")
        self.step_desc_label.setWordWrap(True)
        s_layout.addWidget(self.step_desc_label)

        layout.addWidget(step_card)

        # 3. Current Activity Card
        act_card = QFrame()
        act_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 6px;")
        a_layout = QVBoxLayout(act_card)
        a_layout.setContentsMargins(8, 6, 8, 6)

        a_title = QLabel("CURRENT DETECTED ACTIVITY")
        a_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8;")
        a_layout.addWidget(a_title)

        self.act_label = QLabel("IDLE")
        self.act_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc;")
        a_layout.addWidget(self.act_label)

        layout.addWidget(act_card)

        # 4. Large Tri-State Assurance Decision Banner
        self.assurance_banner = QLabel("UNCERTAIN")
        self.assurance_banner.setAlignment(Qt.AlignCenter)
        self.assurance_banner.setFixedHeight(48)
        self.assurance_banner.setStyleSheet(self._decision_style(COLOR_UNCERTAIN))
        layout.addWidget(self.assurance_banner)

        self.assurance_reason_label = QLabel("Awaiting verification evidence")
        self.assurance_reason_label.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED}; text-align: center;")
        self.assurance_reason_label.setAlignment(Qt.AlignCenter)
        self.assurance_reason_label.setWordWrap(True)
        layout.addWidget(self.assurance_reason_label)

        layout.addStretch()

    def _decision_style(self, bg_color: str) -> str:
        return f"""
            background-color: {bg_color};
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 2px;
            border-radius: 4px;
        """

    def set_mission(self, exp_id: str, run_id: str, step_id: str, title: str, step_idx: int, total_steps: int) -> None:
        self.exp_label.setText(f"EXP: {exp_id}")
        self.run_label.setText(f"RUN: {run_id}")
        self.step_id_label.setText(step_id)
        self.step_desc_label.setText(title)

        total = max(1, total_steps)
        pct = int(min(100, max(0, ((step_idx + 1) / total) * 100)))
        self.progress_bar.setValue(pct)
        self.progress_text.setText(f"Step {step_idx + 1} of {total} ({pct}%)")

    def set_activity(self, activity_str: str) -> None:
        self.act_label.setText(activity_str or "IDLE")

    def set_assurance(self, decision: str, reason: str) -> None:
        dec = decision.upper()
        self.assurance_reason_label.setText(reason or "")

        if dec == "VERIFIED":
            self.assurance_banner.setText("🟢 VERIFIED")
            self.assurance_banner.setStyleSheet(self._decision_style(COLOR_VERIFIED))
        elif dec == "DEVIATION":
            self.assurance_banner.setText("🔴 DEVIATION")
            self.assurance_banner.setStyleSheet(self._decision_style(COLOR_DEVIATION))
        else:
            self.assurance_banner.setText("🟡 UNCERTAIN")
            self.assurance_banner.setStyleSheet(self._decision_style(COLOR_UNCERTAIN))
