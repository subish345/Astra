# ==============================================================================
# ASTRA-EA Dedicated Evidence Audit View
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Full-screen evidence audit viewer inspecting multimodal corroboration trees."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.ui.theme import Colors


class EvidenceView(QWidget):
    """Dedicated audit screen allowing step-by-step evidence inspection."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header with Step Selector
        hdr_frame = QFrame()
        hdr_frame.setObjectName("PanelFrame")
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(12, 8, 12, 8)

        lbl_title = QLabel("MULTIMODAL EVIDENCE AUDIT VIEWER")
        lbl_title.setObjectName("HeaderTitle")
        hdr_layout.addWidget(lbl_title)

        hdr_layout.addStretch()

        lbl_select = QLabel("INSPECT STEP:")
        lbl_select.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_MUTED};")
        hdr_layout.addWidget(lbl_select)

        self.cmb_steps = QComboBox()
        self.cmb_steps.addItems([
            "STEP_01: Approach Experiment Station",
            "STEP_02: Grasp Specimen Container",
            "STEP_03: Transfer Specimen to Work Surface",
            "STEP_04: Release Specimen",
        ])
        self.cmb_steps.setStyleSheet(
            f"background-color: {Colors.BG_SURFACE}; color: {Colors.TEXT_PRIMARY}; "
            f"border: 1px solid {Colors.BORDER_DEFAULT}; border-radius: 3px; padding: 4px 8px; font-weight: bold;"
        )
        self.cmb_steps.currentIndexChanged.connect(self._on_step_changed)
        hdr_layout.addWidget(self.cmb_steps)
        layout.addWidget(hdr_frame)

        # Top Decision Summary Card
        self.summary_card = QFrame()
        self.summary_card.setObjectName("PanelFrame")
        self.summary_card.setStyleSheet(
            f"background-color: {Colors.GREEN_BG}; border: 1px solid {Colors.GREEN}; border-radius: 6px; padding: 8px;"
        )
        sc_layout = QHBoxLayout(self.summary_card)

        self.lbl_decision = QLabel("DECISION: VERIFIED")
        self.lbl_decision.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.GREEN_BRIGHT};")
        sc_layout.addWidget(self.lbl_decision)

        self.lbl_conf = QLabel("COMPOSITE CONFIDENCE: 94.0%")
        self.lbl_conf.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        sc_layout.addWidget(self.lbl_conf)

        self.lbl_audit_id = QLabel("AUDIT ID: EVAL_A84B91D2")
        self.lbl_audit_id.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        sc_layout.addWidget(self.lbl_audit_id)

        sc_layout.addStretch()
        layout.addWidget(self.summary_card)

        # Evidence Items Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["SATISFIED", "DIMENSION", "CONFIDENCE", "SOURCE FRAME", "VERIFICATION REASONS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {Colors.BG_DARKEST}; border: 1px solid {Colors.BORDER_DEFAULT}; }} "
            f"QTableWidget::item {{ padding: 6px; font-size: 12px; }}"
        )
        layout.addWidget(self.table, stretch=2)

        # Causal Traceability Tree Readout
        lbl_trace = QLabel("CAUSAL AUDIT TRACE TREE")
        lbl_trace.setObjectName("SectionTitle")
        layout.addWidget(lbl_trace)

        self.txt_trace = QTextEdit()
        self.txt_trace.setReadOnly(True)
        self.txt_trace.setStyleSheet(
            f"background-color: {Colors.BG_DARKEST}; border: 1px solid {Colors.BORDER_DEFAULT}; "
            f"color: {Colors.TEXT_PRIMARY}; font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(self.txt_trace, stretch=1)

        # Load initial mock / state
        self._load_demo_step_evidence(0)

    def _on_step_changed(self, idx: int) -> None:
        self._load_demo_step_evidence(idx)

    def _load_demo_step_evidence(self, step_idx: int) -> None:
        """Populate audit view for selected step."""
        demo_data = [
            (
                "VERIFIED", 0.92, "EVAL_01A",
                [
                    ("✓ YES", "Spatial Proximity", "95%", "112", "Astronaut within 0.15m normalized zone"),
                    ("✓ YES", "Temporal Presence", "90%", "100-140", "Presence duration 2.4s > 2.0s threshold"),
                    ("✓ YES", "Actor Detected", "98%", "120", "Astronaut tracked with 98% detection confidence"),
                ],
                """STEP AUDIT TRACE: [STEP_01] — ✓ VERIFIED
├── Experiment: DEMO_EXP_001 (Procedure v1.0.0)
├── Observation Angle: VIEW_LEFT (azimuth: -30.0 deg)
├── Zone Definition: EXPERIMENT_STATION
└── Evidence Corroboration:
    ├── ✓ SPATIAL_PROXIMITY (conf: 0.95)
    ├── ✓ TEMPORAL_PRESENCE (duration: 2.4s)
    └── ✓ ACTOR_DETECTED (conf: 0.98)"""
            ),
            (
                "VERIFIED", 0.94, "EVAL_02B",
                [
                    ("✓ YES", "Object Detected", "95%", "240", "RED_BOX tracked with high spatial stability"),
                    ("✓ YES", "Hand-Object Contact", "92%", "245", "Contact distance < 0.08 normalized units"),
                    ("✓ YES", "Pose Consistency", "96%", "245", "Right wrist grounded to anatomical shoulder"),
                ],
                """STEP AUDIT TRACE: [STEP_02] — ✓ VERIFIED
├── Experiment: DEMO_EXP_001 (Procedure v1.0.0)
├── Action: GRASP RED_BOX
└── Evidence Corroboration:
    ├── ✓ OBJECT_DETECTED (RED_BOX: 0.95)
    ├── ✓ HAND_OBJECT_CONTACT (conf: 0.92)
    └── ✓ POSE_CONSISTENCY (RIGHT_HAND: 0.96)"""
            ),
            (
                "VERIFIED", 0.91, "EVAL_03C",
                [
                    ("✓ YES", "Destination Match", "94%", "380", "Specimen placed within WORK_SURFACE zone"),
                    ("✓ YES", "Object Stabilized", "90%", "390", "Position delta < 0.05 units over 1.2s"),
                    ("✓ YES", "Coupled Motion", "89%", "350-380", "Hand-object coupled trajectory verified"),
                ],
                """STEP AUDIT TRACE: [STEP_03] — ✓ VERIFIED
├── Action: PLACE RED_BOX
└── Evidence Corroboration:
    ├── ✓ DESTINATION_MATCH (WORK_SURFACE: 0.94)
    ├── ✓ OBJECT_STABILIZED (conf: 0.90)
    └── ✓ COUPLED_MOTION (conf: 0.89)"""
            ),
            (
                "VERIFIED", 0.95, "EVAL_04D",
                [
                    ("✓ YES", "Contact Cleared", "96%", "450", "Hand cleared contact distance > 0.12 units"),
                    ("✓ YES", "Temporal Consistency", "94%", "440-470", "Clearance sustained > 0.5s threshold"),
                    ("✓ YES", "Object Stabilized", "95%", "460", "Specimen stationary on work surface"),
                ],
                """STEP AUDIT TRACE: [STEP_04] — ✓ VERIFIED
├── Action: RELEASE RED_BOX
└── Evidence Corroboration:
    ├── ✓ CONTACT_CLEARED (clearance sustained: 0.8s)
    ├── ✓ TEMPORAL_CONSISTENCY (conf: 0.94)
    └── ✓ OBJECT_STABILIZED (conf: 0.95)"""
            ),
        ]

        if 0 <= step_idx < len(demo_data):
            dec, conf, eval_id, items, trace = demo_data[step_idx]
            self.lbl_decision.setText(f"DECISION: {dec}")
            self.lbl_conf.setText(f"COMPOSITE CONFIDENCE: {conf*100:.1f}%")
            self.lbl_audit_id.setText(f"AUDIT ID: {eval_id}")

            self.table.setRowCount(len(items))
            for row, (sat, dim, sc, fr, rea) in enumerate(items):
                item_sat = QTableWidgetItem(sat)
                item_sat.setForeground(Qt.green)
                self.table.setItem(row, 0, item_sat)

                item_dim = QTableWidgetItem(dim)
                item_dim.setForeground(Qt.white)
                self.table.setItem(row, 1, item_dim)

                item_sc = QTableWidgetItem(sc)
                item_sc.setTextAlignment(Qt.AlignCenter)
                item_sc.setForeground(Qt.yellow)
                self.table.setItem(row, 2, item_sc)

                item_fr = QTableWidgetItem(fr)
                item_fr.setTextAlignment(Qt.AlignCenter)
                item_fr.setForeground(Qt.lightGray)
                self.table.setItem(row, 3, item_fr)

                item_rea = QTableWidgetItem(rea)
                item_rea.setForeground(Qt.lightGray)
                self.table.setItem(row, 4, item_rea)

            self.txt_trace.setPlainText(trace)
