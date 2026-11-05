# ==============================================================================
# ASTRA-EA System Health & Telemetry Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Panel presenting subsystem operational health status and empirical performance metrics."""

from __future__ import annotations

import os
from typing import Dict, Optional

import psutil
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.ui.theme import Colors


class SubsystemBadge(QFrame):
    """Visual badge for an individual subsystem health status."""

    def __init__(self, name: str, default_status: str = "ACTIVE", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.name = name
        self.status = default_status
        self.setObjectName("CardFrame")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.lbl_name = QLabel(self.name)
        self.lbl_name.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(self.lbl_name)

        layout.addStretch()

        self.lbl_status = QLabel(self.status)
        self.lbl_status.setStyleSheet(
            f"font-size: 10px; font-weight: bold; border-radius: 3px; padding: 1px 5px;"
        )
        layout.addWidget(self.lbl_status)
        self.set_status(self.status)

    def set_status(self, status: str) -> None:
        self.status = status.upper()
        if self.status in ("ONLINE", "ACTIVE", "NORMAL", "OPERATIONAL"):
            self.lbl_status.setText(f"🟢 {self.status}")
            self.lbl_status.setStyleSheet(
                f"color: {Colors.GREEN_BRIGHT}; background-color: {Colors.GREEN_BG}; "
                f"border: 1px solid {Colors.GREEN}; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;"
            )
        elif self.status == "OFFLINE":
            # For network: Expected air-gapped condition, not failure!
            self.lbl_status.setText("🔴 OFFLINE (AIR-GAPPED)")
            self.lbl_status.setStyleSheet(
                f"color: {Colors.AMBER_BRIGHT}; background-color: {Colors.BG_SURFACE}; "
                f"border: 1px solid {Colors.BORDER_DEFAULT}; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;"
            )
        elif self.status in ("DEGRADED", "WARNING"):
            self.lbl_status.setText(f"🟡 {self.status}")
            self.lbl_status.setStyleSheet(
                f"color: {Colors.AMBER_BRIGHT}; background-color: {Colors.AMBER_BG}; "
                f"border: 1px solid {Colors.AMBER}; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;"
            )
        else:
            self.lbl_status.setText(f"🔴 {self.status}")
            self.lbl_status.setStyleSheet(
                f"color: {Colors.RED_BRIGHT}; background-color: {Colors.RED_BG}; "
                f"border: 1px solid {Colors.RED}; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 2px;"
            )


class HealthPanel(QFrame):
    """Presents subsystem status grid and empirical telemetry metrics."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self.badges: Dict[str, SubsystemBadge] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header
        hdr_layout = QHBoxLayout()
        self.lbl_title = QLabel("SYSTEM HEALTH & TELEMETRY")
        self.lbl_title.setObjectName("SectionTitle")
        hdr_layout.addWidget(self.lbl_title)

        hdr_layout.addStretch()

        self.lbl_core_state = QLabel("CORE SYSTEM: OPERATIONAL")
        self.lbl_core_state.setStyleSheet(
            f"color: {Colors.GREEN_BRIGHT}; font-size: 10px; font-weight: bold; "
            f"background-color: {Colors.GREEN_BG}; border: 1px solid {Colors.GREEN}; padding: 2px 6px; border-radius: 3px;"
        )
        hdr_layout.addWidget(self.lbl_core_state)
        layout.addLayout(hdr_layout)

        # Subsystems Grid (2 columns)
        grid = QGridLayout()
        grid.setSpacing(4)

        subsystems = [
            ("Camera", "ONLINE"),
            ("Perception", "ACTIVE"),
            ("Procedure", "ACTIVE"),
            ("Assurance", "ACTIVE"),
            ("Voice", "ACTIVE"),
            ("Database", "ACTIVE"),
            ("Storage", "NORMAL"),
            ("Network", "OFFLINE"),
        ]

        for idx, (name, def_stat) in enumerate(subsystems):
            b = SubsystemBadge(name, def_stat, self)
            self.badges[name] = b
            grid.addWidget(b, idx // 2, idx % 2)

        layout.addLayout(grid)

        # Telemetry Metrics Bar
        telem_frame = QFrame()
        telem_frame.setObjectName("CardFrame")
        telem_layout = QHBoxLayout(telem_frame)
        telem_layout.setContentsMargins(6, 4, 6, 4)
        telem_layout.setSpacing(12)

        self.lbl_fps = QLabel("FPS: 30.0")
        self.lbl_lat = QLabel("LATENCY: 12.0 ms")
        self.lbl_cpu = QLabel("CPU: 18%")
        self.lbl_ram = QLabel("RAM: 420 MB")

        for lbl in (self.lbl_fps, self.lbl_lat, self.lbl_cpu, self.lbl_ram):
            lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT_SECONDARY};")
            telem_layout.addWidget(lbl)

        telem_layout.addStretch()
        layout.addWidget(telem_frame)

    def update_telemetry(self, fps: float, latency_ms: float, cpu_pct: Optional[float] = None, ram_mb: Optional[float] = None) -> None:
        """Update empirical telemetry metrics."""
        self.lbl_fps.setText(f"FPS: {fps:.1f}")
        self.lbl_lat.setText(f"LATENCY: {latency_ms:.1f} ms")

        # Read actual system metrics if not provided
        if cpu_pct is None:
            try:
                cpu_pct = psutil.cpu_percent()
            except Exception:
                cpu_pct = 15.0
        self.lbl_cpu.setText(f"CPU: {cpu_pct:.1f}%")

        if ram_mb is None:
            try:
                mem = psutil.virtual_memory()
                ram_mb = mem.used / (1024 * 1024)
            except Exception:
                ram_mb = 400.0
        self.lbl_ram.setText(f"RAM: {ram_mb:.0f} MB")

    def set_subsystem_status(self, name: str, status: str) -> None:
        """Update individual subsystem badge."""
        if name in self.badges:
            self.badges[name].set_status(status)
