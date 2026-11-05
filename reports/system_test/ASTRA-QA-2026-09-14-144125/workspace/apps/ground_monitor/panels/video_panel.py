# ==============================================================================
# ASTRA-EA Ground Video Panel
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Live IP video observation panel with telemetry overlays and connection placeholders."""

from __future__ import annotations

from typing import Any, Dict, Optional
import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from apps.ground_monitor.theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)


class VideoPanel(QFrame):
    """Ground observation video player displaying decoded IP frames."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setObjectName("videoPanel")
        self.setStyleSheet(f"""
            QFrame#videoPanel {{
                background-color: #080d1a;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
            }}
        """)
        self._connected = False
        self._fps: float = 0.0
        self._res: str = "-- x --"
        self._drops: int = 0
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Video viewport label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(480, 270)
        self.video_label.setStyleSheet("background-color: #040711; border-radius: 4px;")
        layout.addWidget(self.video_label, stretch=1)

        # Footer telemetry bar
        footer = QHBoxLayout()
        footer.setContentsMargins(4, 4, 4, 4)

        self.status_icon = QLabel("🔴 OFFLINE")
        self.status_icon.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
        footer.addWidget(self.status_icon)

        footer.addSpacing(15)

        self.res_label = QLabel("RES: --")
        self.res_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        footer.addWidget(self.res_label)

        footer.addSpacing(15)

        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        footer.addWidget(self.fps_label)

        footer.addStretch()

        self.proto_label = QLabel("PROTO: HTTP/MJPEG (LOCAL IP)")
        self.proto_label.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold;")
        footer.addWidget(self.proto_label)

        layout.addLayout(footer)

        self._render_placeholder("WAITING FOR ONBOARD STREAM...")

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        if connected:
            self.status_icon.setText("🟢 LIVE IP STREAM")
            self.status_icon.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            self.status_icon.setText("🔴 OFFLINE — RECONNECTING")
            self.status_icon.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
            self.fps_label.setText("FPS: 0.0")
            self._render_placeholder("LINK LOST — ATTEMPTING RECONNECT")

    def set_frame(self, frame: np.ndarray, metrics: Dict[str, float]) -> None:
        """Render received BGR frame onto viewport."""
        if frame is None or frame.size == 0:
            return

        h, w = frame.shape[:2]
        self.res_label.setText(f"RES: {w}x{h}")
        fps = metrics.get("fps", 0.0)
        self.fps_label.setText(f"FPS: {fps:.1f}")

        if not self._connected:
            self.set_connected(True)

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * w
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale to fit viewport label preserving aspect ratio
        label_w = max(1, self.video_label.width())
        label_h = max(1, self.video_label.height())
        pixmap = QPixmap.fromImage(qimg).scaled(
            label_w,
            label_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(pixmap)

    def _render_placeholder(self, message: str) -> None:
        """Draw an aerospace target reticle placeholder when stream is disconnected."""
        w = max(480, self.video_label.width())
        h = max(270, self.video_label.height())
        pix = QPixmap(w, h)
        pix.fill(QColor("#040711"))

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # Grid lines
        pen = QPen(QColor("#0f172a"))
        pen.setWidth(1)
        painter.setPen(pen)
        step = 40
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

        # Center reticle
        cx, cy = w // 2, h // 2
        pen = QPen(QColor("#1e293b"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(cx - 50, cy - 50, 100, 100)
        painter.drawEllipse(cx - 80, cy - 80, 160, 160)
        painter.drawLine(cx - 95, cy, cx + 95, cy)
        painter.drawLine(cx, cy - 95, cx, cy + 95)

        # Status text
        painter.setPen(QColor("#64748b"))
        font = QFont("monospace", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignCenter, message)

        painter.end()
        self.video_label.setPixmap(pix)
