# ==============================================================================
# ASTRA-EA Ground Timeline Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Filterable mission event timeline displaying onboard timestamps, latency, and event categories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
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
from streaming.events.schema import EventFilter, EventSeverity, EventType, GroundEvent, categorize_event


class TimelinePanel(QFrame):
    """Chronological event log with filter buttons and network transit latency indicators."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setObjectName("timelinePanel")
        self.setStyleSheet(f"""
            QFrame#timelinePanel {{
                background-color: #0d1527;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        self._all_events: List[tuple[GroundEvent, float]] = []
        self._current_filter = EventFilter.ALL
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header with title and filter buttons
        header = QHBoxLayout()
        title = QLabel("MISSION TIMELINE")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        header.addWidget(title)

        header.addStretch()

        # Filter buttons
        self.filter_buttons = {}
        for f in (EventFilter.ALL, EventFilter.STEPS, EventFilter.DEVIATIONS, EventFilter.RECOVERY, EventFilter.SYSTEM):
            btn = QPushButton(f.value)
            btn.setCheckable(True)
            btn.setFixedHeight(24)
            btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
            if f == EventFilter.ALL:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, filter_val=f: self._on_filter_clicked(filter_val))
            self.filter_buttons[f] = btn
            header.addWidget(btn)

        # Export button
        export_btn = QPushButton("EXPORT")
        export_btn.setFixedHeight(24)
        export_btn.setStyleSheet("font-size: 10px; padding: 2px 8px; background-color: #1e3a5f; color: #38bdf8;")
        export_btn.clicked.connect(self._export_timeline)
        header.addWidget(export_btn)

        layout.addLayout(header)

        # Event List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            background-color: {COLOR_BG_CARD};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            color: {COLOR_TEXT_PRIMARY};
            font-family: monospace;
            font-size: 11px;
        """)
        layout.addWidget(self.list_widget)

    def _on_filter_clicked(self, selected_filter: EventFilter) -> None:
        self._current_filter = selected_filter
        for f, btn in self.filter_buttons.items():
            btn.setChecked(f == selected_filter)
        self._refresh_list()

    def add_event(self, event: GroundEvent, latency_ms: float) -> None:
        """Append event and refresh list if it passes current filter."""
        self._all_events.append((event, latency_ms))
        if self._matches_filter(event, self._current_filter):
            self._insert_item(event, latency_ms)

    def _matches_filter(self, event: GroundEvent, f: EventFilter) -> bool:
        if f == EventFilter.ALL:
            return True
        return categorize_event(event.event_type) == f

    def _refresh_list(self) -> None:
        self.list_widget.clear()
        for event, latency in self._all_events:
            if self._matches_filter(event, self._current_filter):
                self._insert_item(event, latency)
        self.list_widget.scrollToBottom()

    def _insert_item(self, event: GroundEvent, latency_ms: float) -> None:
        # Extract local time portion
        time_str = event.timestamp.split("T")[-1][:12] if "T" in event.timestamp else event.timestamp[:12]
        delta_str = f"+{latency_ms:.0f}ms" if latency_ms > 0 else "<1ms"

        line = f"[{time_str}] ({delta_str}) [{event.event_type.value}] {event.message or event.status}"
        item = QListWidgetItem(line)

        # Color-code by severity
        if event.severity == EventSeverity.DANGER or event.event_type == EventType.DEVIATION_DETECTED:
            item.setForeground(QColor(COLOR_DEVIATION))
        elif event.severity == EventSeverity.WARNING or event.event_type == EventType.STEP_UNCERTAIN:
            item.setForeground(QColor(COLOR_UNCERTAIN))
        elif event.event_type == EventType.STEP_VERIFIED:
            item.setForeground(QColor(COLOR_VERIFIED))
        else:
            item.setForeground(QColor(COLOR_TEXT_PRIMARY))

        self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()

    def _export_timeline(self) -> None:
        """Export timeline to JSON report file."""
        export_dir = Path("storage/reports/streaming")
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "ground_timeline.json"

        data = [
            {"event": e.model_dump(), "latency_ms": lat}
            for e, lat in self._all_events
        ]
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
