# ==============================================================================
# ASTRA-EA Ground Monitor Theme & Styling
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Aerospace mission operations color palette and QSS styling for Ground Monitor."""

from __future__ import annotations

# Mission palette
COLOR_BG_PRIMARY = "#070b14"
COLOR_BG_PANEL = "#0d1527"
COLOR_BG_CARD = "#131f38"
COLOR_BG_CARD_ALT = "#192847"

COLOR_BORDER = "#1e3a5f"
COLOR_BORDER_FOCUS = "#38bdf8"

COLOR_TEXT_PRIMARY = "#f8fafc"
COLOR_TEXT_MUTED = "#94a3b8"
COLOR_TEXT_DIM = "#64748b"

# Telemetry status colors
COLOR_VERIFIED = "#10b981"   # Emerald green
COLOR_UNCERTAIN = "#f59e0b"  # Amber
COLOR_DEVIATION = "#ef4444"  # Crimson red

COLOR_LINK_ONLINE = "#10b981"
COLOR_LINK_DEGRADED = "#f59e0b"
COLOR_LINK_OFFLINE = "#64748b"

GROUND_MONITOR_QSS = f"""
QMainWindow, QWidget#rootWidget {{
    background-color: {COLOR_BG_PRIMARY};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Ubuntu', 'DejaVu Sans', sans-serif;
}}

QFrame.panel {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px;
}}

QFrame.card {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 8px;
}}

QLabel {{
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.title {{
    font-size: 14px;
    font-weight: bold;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QLabel.muted {{
    color: {COLOR_TEXT_MUTED};
    font-size: 11px;
}}

QLabel.badge {{
    font-weight: bold;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 3px;
}}

QPushButton {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 11px;
}}

QPushButton:hover {{
    background-color: {COLOR_BG_CARD_ALT};
    border-color: {COLOR_BORDER_FOCUS};
    color: #38bdf8;
}}

QPushButton:pressed {{
    background-color: #0c1829;
}}

QPushButton:checked {{
    background-color: #0284c7;
    border-color: #38bdf8;
    color: white;
}}

QProgressBar {{
    background-color: #0b1322;
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    text-align: center;
    color: {COLOR_TEXT_PRIMARY};
    font-weight: bold;
    font-size: 10px;
}}

QProgressBar::chunk {{
    background-color: #0284c7;
    border-radius: 2px;
}}

QListWidget {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    color: {COLOR_TEXT_PRIMARY};
    font-family: monospace;
    font-size: 11px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 4px 6px;
    border-bottom: 1px solid #182845;
}}

QListWidget::item:selected {{
    background-color: #1e3a5f;
    color: #38bdf8;
}}

QScrollBar:vertical {{
    background: {COLOR_BG_PANEL};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #2a4365;
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
