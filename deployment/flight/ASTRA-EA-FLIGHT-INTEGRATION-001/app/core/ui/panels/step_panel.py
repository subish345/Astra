# ==============================================================================
# ASTRA-EA Current Step & Next Action Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Panel presenting current procedural step details and prominent next action guidance."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.ui.theme import Colors, get_status_colors


class StepPanel(QFrame):
    """Presents active procedural step information and high-visibility next action direction."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header: Step index & Status badge
        top_layout = QHBoxLayout()
        self.lbl_step_num = QLabel("STEP 01 / 04")
        self.lbl_step_num.setObjectName("SectionTitle")
        top_layout.addWidget(self.lbl_step_num)

        top_layout.addStretch()

        self.lbl_status_badge = QLabel("WAITING")
        self.lbl_status_badge.setStyleSheet(
            f"background-color: {Colors.BG_SURFACE}; color: {Colors.TEXT_SECONDARY}; "
            f"border: 1px solid {Colors.BORDER_DEFAULT}; border-radius: 3px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )
        top_layout.addWidget(self.lbl_status_badge)
        layout.addLayout(top_layout)

        # Step Title
        self.lbl_step_title = QLabel("Approach Experiment Station")
        self.lbl_step_title.setObjectName("StepTitle")
        layout.addWidget(self.lbl_step_title)

        # Step Metrics & Expected Action
        meta_layout = QHBoxLayout()
        self.lbl_expected = QLabel("EXPECTED: APPROACH EXPERIMENT_STATION")
        self.lbl_expected.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; font-weight: 600;")
        meta_layout.addWidget(self.lbl_expected)

        meta_layout.addStretch()

        self.lbl_time_in_step = QLabel("TIME: 0.0s")
        self.lbl_time_in_step.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-weight: 600;")
        meta_layout.addWidget(self.lbl_time_in_step)
        layout.addLayout(meta_layout)

        # Prominent Next Action Card
        self.next_action_card = QFrame()
        self.next_action_card.setObjectName("CardFrame")
        self.next_action_card.setStyleSheet(
            f"background-color: {Colors.BLUE_BG}; border: 1px solid {Colors.BLUE}; border-radius: 6px; padding: 8px;"
        )
        card_layout = QVBoxLayout(self.next_action_card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(4)

        lbl_next_hdr = QLabel("NEXT ACTION GUIDANCE")
        lbl_next_hdr.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {Colors.BLUE_BRIGHT}; letter-spacing: 0.8px;")
        card_layout.addWidget(lbl_next_hdr)

        self.lbl_next_text = QLabel("Approach the experiment work surface to initiate protocol.")
        self.lbl_next_text.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_WHITE};")
        self.lbl_next_text.setWordWrap(True)
        card_layout.addWidget(self.lbl_next_text)

        layout.addWidget(self.next_action_card)

    def update_step(
        self,
        step_number: int,
        total_steps: int,
        step_name: str,
        expected_action: str,
        status: str,
        time_in_step: float = 0.0,
    ) -> None:
        """Update step presentation."""
        self.lbl_step_num.setText(f"STEP {step_number:02d} / {total_steps:02d}")
        self.lbl_step_title.setText(step_name)
        self.lbl_expected.setText(f"EXPECTED: {expected_action.upper()}")
        self.lbl_time_in_step.setText(f"TIME: {time_in_step:.1f}s")

        bg, fg, border = get_status_colors(status)
        self.lbl_status_badge.setText(status.upper())
        self.lbl_status_badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 3px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )

    def update_next_action(self, action_text: str, is_completed: bool = False) -> None:
        """Update next action guidance card."""
        self.lbl_next_text.setText(action_text)
        if is_completed:
            self.next_action_card.setStyleSheet(
                f"background-color: {Colors.GREEN_BG}; border: 1px solid {Colors.GREEN}; border-radius: 6px; padding: 8px;"
            )
        else:
            self.next_action_card.setStyleSheet(
                f"background-color: {Colors.BLUE_BG}; border: 1px solid {Colors.BLUE}; border-radius: 6px; padding: 8px;"
            )
