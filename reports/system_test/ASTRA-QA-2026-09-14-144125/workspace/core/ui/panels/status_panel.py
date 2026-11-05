# ==============================================================================
# ASTRA-EA Mission Status & Assurance Alert Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Priority status panel rendering VERIFIED, UNCERTAIN, DEVIATION, and RECOVERY alerts."""

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

from core.ui.theme import Colors


class StatusPanel(QFrame):
    """Visual alert card representing high-priority assurance outcomes."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self._init_ui()

    def _init_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(6)

        # Header with Decision Title
        top_layout = QHBoxLayout()
        self.lbl_alert_title = QLabel("SYSTEM ASSURANCE: READY")
        self.lbl_alert_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        top_layout.addWidget(self.lbl_alert_title)

        top_layout.addStretch()

        self.lbl_confidence = QLabel("CONFIDENCE: —")
        self.lbl_confidence.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_SECONDARY};")
        top_layout.addWidget(self.lbl_confidence)
        self.layout.addLayout(top_layout)

        # Primary Message Label
        self.lbl_primary_msg = QLabel("Awaiting initial experiment activity.")
        self.lbl_primary_msg.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")
        self.lbl_primary_msg.setWordWrap(True)
        self.layout.addWidget(self.lbl_primary_msg)

        # Deviation Details Container (Visible only during deviation/recovery)
        self.dev_frame = QFrame()
        self.dev_frame.setStyleSheet(
            f"background-color: {Colors.RED_BG}; border: 1px solid {Colors.RED}; border-radius: 4px; padding: 6px;"
        )
        dev_layout = QVBoxLayout(self.dev_frame)
        dev_layout.setContentsMargins(8, 6, 8, 6)
        dev_layout.setSpacing(4)

        self.lbl_dev_expected = QLabel("EXPECTED: —")
        self.lbl_dev_expected.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_WHITE};")
        dev_layout.addWidget(self.lbl_dev_expected)

        self.lbl_dev_detected = QLabel("DETECTED: —")
        self.lbl_dev_detected.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.RED_BRIGHT};")
        dev_layout.addWidget(self.lbl_dev_detected)

        self.lbl_dev_reason = QLabel("REASON: —")
        self.lbl_dev_reason.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_PRIMARY};")
        self.lbl_dev_reason.setWordWrap(True)
        dev_layout.addWidget(self.lbl_dev_reason)

        self.lbl_dev_recovery = QLabel("RECOVERY: —")
        self.lbl_dev_recovery.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {Colors.BLUE_BRIGHT};")
        self.lbl_dev_recovery.setWordWrap(True)
        dev_layout.addWidget(self.lbl_dev_recovery)

        self.layout.addWidget(self.dev_frame)
        self.dev_frame.hide()

    def show_verified(self, step_name: str, confidence: float, reasons: list[str]) -> None:
        """Render VERIFIED assurance state."""
        self.dev_frame.hide()
        self.setStyleSheet(
            f"QFrame#PanelFrame {{ background-color: {Colors.GREEN_BG}; border: 1px solid {Colors.GREEN}; border-radius: 6px; }}"
        )
        self.lbl_alert_title.setText(f"🟢 STEP VERIFIED: {step_name.upper()}")
        self.lbl_alert_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.GREEN_BRIGHT};")
        self.lbl_confidence.setText(f"CONFIDENCE: {confidence*100:.1f}%")
        self.lbl_confidence.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.GREEN_BRIGHT};")

        reason_str = "; ".join(reasons) if reasons else "All required corroborating evidence satisfied."
        self.lbl_primary_msg.setText(f"Verification corroborated. {reason_str}")
        self.lbl_primary_msg.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_PRIMARY};")

    def show_uncertain(self, message: str = "Object partially hidden. Keep the experiment area visible.") -> None:
        """Render UNCERTAIN verification paused state. Strictly avoid calling it an error."""
        self.dev_frame.hide()
        self.setStyleSheet(
            f"QFrame#PanelFrame {{ background-color: {Colors.AMBER_BG}; border: 1px solid {Colors.AMBER}; border-radius: 6px; }}"
        )
        self.lbl_alert_title.setText("🟡 VERIFICATION PAUSED — UNCERTAIN")
        self.lbl_alert_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.AMBER_BRIGHT};")
        self.lbl_confidence.setText("CONFIDENCE: LOW")
        self.lbl_confidence.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.AMBER_BRIGHT};")

        self.lbl_primary_msg.setText(message)
        self.lbl_primary_msg.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_PRIMARY};")

    def show_deviation(
        self,
        deviation_type: str,
        expected_obj: str,
        detected_obj: str,
        reason: str,
        recovery_instruction: str,
    ) -> None:
        """Render PROCEDURE DEVIATION alert with explicit recovery instructions."""
        self.setStyleSheet(
            f"QFrame#PanelFrame {{ background-color: {Colors.BG_PANEL}; border: 2px solid {Colors.RED_BRIGHT}; border-radius: 6px; }}"
        )
        self.lbl_alert_title.setText(f"🔴 PROCEDURE DEVIATION: {deviation_type.upper()}")
        self.lbl_alert_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.RED_BRIGHT};")
        self.lbl_confidence.setText("STATE: ATTENTION REQUIRED")
        self.lbl_confidence.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.RED_BRIGHT};")

        self.lbl_primary_msg.setText("Immediate astronaut corrective action required to maintain experiment validity:")
        self.lbl_primary_msg.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_PRIMARY}; font-weight: 600;")

        self.lbl_dev_expected.setText(f"EXPECTED: {expected_obj}")
        self.lbl_dev_detected.setText(f"DETECTED: {detected_obj}")
        self.lbl_dev_reason.setText(f"REASON: {reason}")
        self.lbl_dev_recovery.setText(f"RECOVERY: {recovery_instruction}")

        self.dev_frame.show()

    def show_recovery(self, state_name: str, instruction: str, verified: bool = False) -> None:
        """Render closed-loop recovery state."""
        if verified:
            self.show_verified("RECOVERY COMPLETE", 1.0, [instruction])
        else:
            self.dev_frame.show()
            self.setStyleSheet(
                f"QFrame#PanelFrame {{ background-color: {Colors.BLUE_BG}; border: 1px solid {Colors.BLUE}; border-radius: 6px; }}"
            )
            self.lbl_alert_title.setText(f"🔵 RECOVERY IN PROGRESS: {state_name.upper()}")
            self.lbl_alert_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.BLUE_BRIGHT};")
            self.lbl_dev_recovery.setText(f"RECOVERY INSTRUCTION: {instruction}")

    def reset_to_ready(self) -> None:
        """Reset panel to ready state."""
        self.dev_frame.hide()
        self.setStyleSheet("")
        self.lbl_alert_title.setText("SYSTEM ASSURANCE: READY")
        self.lbl_alert_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        self.lbl_confidence.setText("CONFIDENCE: —")
        self.lbl_primary_msg.setText("Awaiting initial experiment activity.")
