# ==============================================================================
# ASTRA-EA Multimodal Evidence Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Panel presenting physical, spatial, and temporal evidence corroborating decisions."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.ui.state import EvidenceItemState
from core.ui.theme import Colors


class EvidencePanel(QFrame):
    """Presents active multimodal evidence items with confidence scores and details."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        hdr_layout = QHBoxLayout()
        self.lbl_title = QLabel("MULTIMODAL EVIDENCE CORROBORATION")
        self.lbl_title.setObjectName("SectionTitle")
        hdr_layout.addWidget(self.lbl_title)

        hdr_layout.addStretch()

        self.lbl_score = QLabel("EVIDENCE SCORE: —")
        self.lbl_score.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_SECONDARY};")
        hdr_layout.addWidget(self.lbl_score)
        layout.addLayout(hdr_layout)

        # Evidence Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["STATUS", "EVIDENCE DIMENSION", "CONFIDENCE", "DETAILS / CONTEXT"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {Colors.BG_DARKEST}; border: 1px solid {Colors.BORDER_DEFAULT}; }} "
            f"QTableWidget::item {{ padding: 4px; font-size: 11px; }}"
        )
        layout.addWidget(self.table)

        # Bottom detail readout
        self.lbl_detail_selected = QLabel("Select an evidence item row to view audit details.")
        self.lbl_detail_selected.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.lbl_detail_selected)

    def update_evidence(self, items: List[EvidenceItemState], bundle_score: Optional[float] = None) -> None:
        """Update table with latest evidence bundle items."""
        if bundle_score is not None:
            self.lbl_score.setText(f"EVIDENCE SCORE: {bundle_score*100:.1f}%")
            if bundle_score >= 0.8:
                self.lbl_score.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.GREEN_BRIGHT};")
            else:
                self.lbl_score.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.AMBER_BRIGHT};")

        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            # Status icon
            stat_str = "✓ SATISFIED" if it.is_satisfied else "— MISSING"
            item_stat = QTableWidgetItem(stat_str)
            item_stat.setForeground(Qt.green if it.is_satisfied else Qt.gray)
            item_stat.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_stat)

            # Dimension
            item_dim = QTableWidgetItem(it.evidence_type.replace("_", " ").title())
            item_dim.setForeground(Qt.white)
            self.table.setItem(row, 1, item_dim)

            # Score
            score_str = f"{it.score*100:.0f}%" if it.score > 0 else "N/A"
            item_sc = QTableWidgetItem(score_str)
            item_sc.setTextAlignment(Qt.AlignCenter)
            item_sc.setForeground(Qt.yellow if it.score > 0.5 else Qt.gray)
            self.table.setItem(row, 2, item_sc)

            # Details
            item_det = QTableWidgetItem(it.details)
            item_det.setForeground(Qt.lightGray)
            self.table.setItem(row, 3, item_det)

    def _on_selection_changed(self) -> None:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        dim = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        det = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
        self.lbl_detail_selected.setText(f"Audit Reference: [{dim}] — {det}")
