# ==============================================================================
# ASTRA-EA Experiment Progress Timeline Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Panel presenting the vertical experiment procedure timeline and step progress."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.ui.theme import Colors, get_status_colors


class StepRowWidget(QFrame):
    """Widget representing an individual step in the procedure timeline."""

    def __init__(self, step_id: str, step_num: int, step_name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.step_id = step_id
        self.step_num = step_num
        self.step_name = step_name
        self.status = "WAITING"

        self.setObjectName("CardFrame")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Status Icon (✓, ●, ○, ⚠)
        self.lbl_icon = QLabel("○")
        self.lbl_icon.setFixedWidth(20)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.lbl_icon)

        # Step Label
        self.lbl_name = QLabel(f"{self.step_num:02d}. {self.step_name}")
        self.lbl_name.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(self.lbl_name, stretch=1)

        # Status Text Badge
        self.lbl_status = QLabel("WAITING")
        self.lbl_status.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {Colors.TEXT_MUTED}; "
            f"background-color: {Colors.BG_DARKEST}; border: 1px solid {Colors.BORDER_MUTED}; "
            f"border-radius: 3px; padding: 2px 6px;"
        )
        layout.addWidget(self.lbl_status)

    def set_status(self, status: str) -> None:
        """Update step row visual status."""
        self.status = status.upper()
        bg, fg, border = get_status_colors(self.status)

        if self.status == "VERIFIED":
            self.lbl_icon.setText("✓")
            self.lbl_icon.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.GREEN_BRIGHT};")
        elif self.status == "IN_PROGRESS":
            self.lbl_icon.setText("●")
            self.lbl_icon.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.BLUE_BRIGHT};")
        elif self.status == "DEVIATION":
            self.lbl_icon.setText("🔴")
            self.lbl_icon.setStyleSheet(f"font-size: 12px; color: {Colors.RED_BRIGHT};")
        elif self.status == "UNCERTAIN":
            self.lbl_icon.setText("🟡")
            self.lbl_icon.setStyleSheet(f"font-size: 12px; color: {Colors.AMBER_BRIGHT};")
        else:
            self.lbl_icon.setText("○")
            self.lbl_icon.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_MUTED};")

        self.lbl_status.setText(self.status)
        self.lbl_status.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {fg}; "
            f"background-color: {bg}; border: 1px solid {border}; "
            f"border-radius: 3px; padding: 2px 6px;"
        )


class ProgressPanel(QFrame):
    """Panel presenting the ordered procedure step list with real-time statuses."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self.step_rows: Dict[str, StepRowWidget] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 10, 12, 10)
        self.main_layout.setSpacing(6)

        hdr_layout = QHBoxLayout()
        self.lbl_title = QLabel("EXPERIMENT PROCEDURE STEPS")
        self.lbl_title.setObjectName("SectionTitle")
        hdr_layout.addWidget(self.lbl_title)
        hdr_layout.addStretch()

        self.lbl_summary = QLabel("0 / 4 VERIFIED")
        self.lbl_summary.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_SECONDARY};")
        hdr_layout.addWidget(self.lbl_summary)
        self.main_layout.addLayout(hdr_layout)

        # Default DEMO procedure steps
        default_steps = [
            ("STEP_01", 1, "Approach Experiment Station"),
            ("STEP_02", 2, "Grasp Specimen Container"),
            ("STEP_03", 3, "Transfer Specimen to Work Surface"),
            ("STEP_04", 4, "Release Specimen"),
        ]

        for sid, snum, sname in default_steps:
            row = StepRowWidget(sid, snum, sname, self)
            self.step_rows[sid] = row
            self.main_layout.addWidget(row)

        self.main_layout.addStretch()

    def update_steps(self, step_statuses: Dict[str, str], current_step_id: Optional[str] = None) -> None:
        """Update statuses across all procedure steps."""
        verified_count = 0
        for sid, row in self.step_rows.items():
            stat = step_statuses.get(sid, "WAITING")
            if sid == current_step_id and stat != "VERIFIED":
                stat = "IN_PROGRESS"
            row.set_status(stat)
            if stat == "VERIFIED":
                verified_count += 1

        self.lbl_summary.setText(f"{verified_count} / {len(self.step_rows)} VERIFIED")
        if verified_count == len(self.step_rows):
            self.lbl_summary.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.GREEN_BRIGHT};")
