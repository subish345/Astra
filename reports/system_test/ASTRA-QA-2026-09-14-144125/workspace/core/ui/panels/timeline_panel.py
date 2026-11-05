# ==============================================================================
# ASTRA-EA Mission Timeline Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Panel presenting chronological mission events with multi-category filtering."""

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

from core.ui.state import TimelineEventState
from core.ui.theme import Colors


class TimelinePanel(QFrame):
    """Presents filterable chronological mission log events."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")

        self._all_events: List[TimelineEventState] = []
        self._active_filter: str = "ALL"

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        hdr_layout = QHBoxLayout()
        self.lbl_title = QLabel("MISSION EVENT TIMELINE")
        self.lbl_title.setObjectName("SectionTitle")
        hdr_layout.addWidget(self.lbl_title)

        hdr_layout.addStretch()

        # Category Filter Chips
        filters = ["ALL", "VERIFIED", "UNCERTAIN", "DEVIATION", "RECOVERY", "SYSTEM"]
        self.filter_buttons = {}
        for f in filters:
            btn = QPushButton(f)
            btn.setCheckable(True)
            if f == "ALL":
                btn.setChecked(True)
            btn.setStyleSheet("padding: 2px 8px; font-size: 10px;")
            btn.clicked.connect(lambda checked, cat=f: self._set_filter(cat))
            self.filter_buttons[f] = btn
            hdr_layout.addWidget(btn)

        layout.addLayout(hdr_layout)

        # Timeline Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["TIME", "CATEGORY", "EVENT", "DETAILS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {Colors.BG_DARKEST}; border: 1px solid {Colors.BORDER_DEFAULT}; }} "
            f"QTableWidget::item {{ padding: 3px 6px; font-size: 11px; }}"
        )
        layout.addWidget(self.table)

    def _set_filter(self, category: str) -> None:
        self._active_filter = category
        for cat, btn in self.filter_buttons.items():
            btn.setChecked(cat == category)
        self._render_filtered_events()

    def add_event(self, event: TimelineEventState) -> None:
        """Append a new event and update the view."""
        self._all_events.append(event)
        self._render_filtered_events()

    def set_events(self, events: List[TimelineEventState]) -> None:
        """Replace all events."""
        self._all_events = list(events)
        self._render_filtered_events()

    def _render_filtered_events(self) -> None:
        filtered = []
        for ev in self._all_events:
            if self._active_filter == "ALL":
                filtered.append(ev)
            elif self._active_filter == "VERIFIED" and "VERIFIED" in ev.title.upper():
                filtered.append(ev)
            elif self._active_filter == "UNCERTAIN" and "UNCERTAIN" in ev.title.upper():
                filtered.append(ev)
            elif self._active_filter == "DEVIATION" and (ev.event_type == "DEVIATION" or "DEVIATION" in ev.title.upper()):
                filtered.append(ev)
            elif self._active_filter == "RECOVERY" and (ev.event_type == "RECOVERY" or "RECOVERY" in ev.title.upper()):
                filtered.append(ev)
            elif self._active_filter == "SYSTEM" and ev.event_type == "SYSTEM":
                filtered.append(ev)

        self.table.setRowCount(len(filtered))
        for row, ev in enumerate(filtered):
            # Time
            item_time = QTableWidgetItem(ev.timestamp_str)
            item_time.setForeground(Qt.lightGray)
            self.table.setItem(row, 0, item_time)

            # Category
            item_cat = QTableWidgetItem(ev.event_type)
            item_cat.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, item_cat)

            # Title
            item_title = QTableWidgetItem(ev.title)
            if ev.severity == "SUCCESS":
                item_title.setForeground(Qt.green)
            elif ev.severity == "WARNING":
                item_title.setForeground(Qt.yellow)
            elif ev.severity == "DANGER":
                item_title.setForeground(Qt.red)
            else:
                item_title.setForeground(Qt.white)
            self.table.setItem(row, 2, item_title)

            # Details
            item_det = QTableWidgetItem(ev.description)
            item_det.setForeground(Qt.gray)
            self.table.setItem(row, 3, item_det)

        # Scroll to bottom on new event
        self.table.scrollToBottom()
