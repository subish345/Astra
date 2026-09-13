# ==============================================================================
# ASTRA-EA Dedicated Timeline View
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Full-screen chronological event timeline viewer with search and category filters."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.ui.state import TimelineEventState
from core.ui.theme import Colors


class TimelineView(QWidget):
    """Full-screen timeline audit log with search and category filtering."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._all_events: List[TimelineEventState] = []
        self._active_filter: str = "ALL"
        self._search_query: str = ""
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Bar
        hdr_frame = QFrame()
        hdr_frame.setObjectName("PanelFrame")
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(12, 8, 12, 8)

        lbl_title = QLabel("MISSION EVENT TIMELINE AUDIT")
        lbl_title.setObjectName("HeaderTitle")
        hdr_layout.addWidget(lbl_title)

        hdr_layout.addStretch()

        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filter events by text...")
        self.txt_search.setFixedWidth(200)
        self.txt_search.textChanged.connect(self._on_search_changed)
        hdr_layout.addWidget(self.txt_search)

        # Filter Buttons
        filters = ["ALL", "STEP", "ASSURANCE", "DEVIATION", "RECOVERY", "SYSTEM"]
        self.filter_buttons = {}
        for f in filters:
            btn = QPushButton(f)
            btn.setCheckable(True)
            if f == "ALL":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, cat=f: self._set_filter(cat))
            self.filter_buttons[f] = btn
            hdr_layout.addWidget(btn)

        layout.addWidget(hdr_frame)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["TIMESTAMP", "CATEGORY", "EVENT / ACTION", "AUDIT DETAILS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {Colors.BG_DARKEST}; border: 1px solid {Colors.BORDER_DEFAULT}; }} "
            f"QTableWidget::item {{ padding: 6px; font-size: 12px; }}"
        )
        layout.addWidget(self.table)

    def _set_filter(self, cat: str) -> None:
        self._active_filter = cat
        for c, btn in self.filter_buttons.items():
            btn.setChecked(c == cat)
        self._render()

    def _on_search_changed(self, text: str) -> None:
        self._search_query = text.strip().lower()
        self._render()

    def set_events(self, events: List[TimelineEventState]) -> None:
        self._all_events = list(events)
        self._render()

    def add_event(self, event: TimelineEventState) -> None:
        self._all_events.append(event)
        self._render()

    def _render(self) -> None:
        filtered = []
        for ev in self._all_events:
            # Category match
            cat_ok = True
            if self._active_filter != "ALL":
                cat_ok = (ev.event_type.upper() == self._active_filter) or (self._active_filter in ev.title.upper())

            # Search match
            search_ok = True
            if self._search_query:
                search_ok = (self._search_query in ev.title.lower()) or (self._search_query in ev.description.lower())

            if cat_ok and search_ok:
                filtered.append(ev)

        self.table.setRowCount(len(filtered))
        for row, ev in enumerate(filtered):
            item_ts = QTableWidgetItem(ev.timestamp_str)
            item_ts.setForeground(Qt.lightGray)
            self.table.setItem(row, 0, item_ts)

            item_cat = QTableWidgetItem(ev.event_type)
            item_cat.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, item_cat)

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

            item_det = QTableWidgetItem(ev.description)
            item_det.setForeground(Qt.gray)
            self.table.setItem(row, 3, item_det)
