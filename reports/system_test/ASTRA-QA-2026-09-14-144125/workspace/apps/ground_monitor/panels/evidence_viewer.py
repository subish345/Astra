# ==============================================================================
# ASTRA-EA Ground Evidence Viewer
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Read-only viewer for corroborating multimodal evidence bundles and causal trees."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from apps.ground_monitor.theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)

logger = logging.getLogger("evidence_viewer")


class EvidenceViewerDialog(QDialog):
    """Modal dialog displaying corroborating evidence bundle and causal reasoning tree."""

    def __init__(
        self,
        evidence_id: str,
        base_url: str = "http://127.0.0.1:8765",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.evidence_id = evidence_id
        self.base_url = base_url
        self.setWindowTitle(f"ASTRA-EA Evidence Audit — {evidence_id}")
        self.setMinimumSize(640, 480)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0b1322;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self._init_ui()
        self._load_evidence()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"CORROBORATING EVIDENCE AUDIT: {self.evidence_id}")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8;")
        header.addWidget(title)
        header.addStretch()

        read_only_badge = QLabel("READ-ONLY ONBOARD AUDIT")
        read_only_badge.setStyleSheet("background-color: #1e3a5f; color: #38bdf8; font-size: 10px; font-weight: bold; padding: 3px 6px; border-radius: 3px;")
        header.addWidget(read_only_badge)
        layout.addLayout(header)

        # Content Text Area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet(f"""
            background-color: {COLOR_BG_CARD};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            color: {COLOR_TEXT_PRIMARY};
            font-family: monospace;
            font-size: 11px;
            padding: 8px;
        """)
        layout.addWidget(self.text_area, stretch=1)

        # Footer close button
        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("CLOSE")
        close_btn.setStyleSheet("padding: 6px 16px; background-color: #1e3a5f; color: #38bdf8; font-weight: bold;")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def _load_evidence(self) -> None:
        """Fetch evidence JSON from remote event server."""
        url = f"{self.base_url}/evidence/{self.evidence_id}"
        self.text_area.setText(f"Connecting to {url} to fetch corroborating evidence bundle...")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ASTRA-EA-GroundMonitor/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    raw_data = resp.read().decode("utf-8")
                    try:
                        parsed = json.loads(raw_data)
                        formatted = json.dumps(parsed, indent=2)
                        self.text_area.setText(formatted)
                    except Exception:
                        self.text_area.setText(raw_data)
                else:
                    self.text_area.setText(f"Failed to fetch evidence bundle (HTTP {resp.status})")
        except Exception as exc:
            self.text_area.setText(
                f"Evidence Retrieval Notice:\n"
                f"Remote fetch from {url} returned: {exc}\n\n"
                f"Evidence ID: {self.evidence_id}\n"
                f"Status: Recorded onboard in SQLite audit store."
            )
