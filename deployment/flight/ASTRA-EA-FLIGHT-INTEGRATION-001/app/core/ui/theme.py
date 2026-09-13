# ==============================================================================
# ASTRA-EA Mission Console Theme & Styles
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Design tokens, color palettes, and stylesheets for space-operations Mission Console."""

from __future__ import annotations

from enum import Enum, unique


@unique
class UIStatus(str, Enum):
    """Normalized UI operational status levels."""

    NORMAL = "NORMAL"
    ACTIVE = "ACTIVE"
    VERIFIED = "VERIFIED"
    UNCERTAIN = "UNCERTAIN"
    WARNING = "WARNING"
    DEVIATION = "DEVIATION"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    SYSTEM_DEGRADED = "SYSTEM_DEGRADED"
    SYSTEM_FAILED = "SYSTEM_FAILED"
    OFFLINE = "OFFLINE"


class Colors:
    """Spacecraft UI dark palette with high-contrast mission status accents."""

    # Backgrounds
    BG_DARKEST = "#0D1117"
    BG_PANEL = "#161B22"
    BG_SURFACE = "#21262D"
    BG_HOVER = "#30363D"

    # Borders
    BORDER_DEFAULT = "#30363D"
    BORDER_MUTED = "#21262D"
    BORDER_FOCUS = "#58A6FF"

    # Typography
    TEXT_PRIMARY = "#F0F6FC"
    TEXT_SECONDARY = "#8B949E"
    TEXT_MUTED = "#6E7681"
    TEXT_WHITE = "#FFFFFF"

    # Status Accents
    GREEN = "#238636"
    GREEN_BRIGHT = "#3FB950"
    GREEN_BG = "#0D2818"

    AMBER = "#D29922"
    AMBER_BRIGHT = "#F0883E"
    AMBER_BG = "#332200"

    RED = "#DA3633"
    RED_BRIGHT = "#F85149"
    RED_BG = "#3D0E0E"

    BLUE = "#1F6FEB"
    BLUE_BRIGHT = "#58A6FF"
    BLUE_BG = "#0C2D6B"

    GRAY = "#484F58"
    GRAY_LIGHT = "#8B949E"


def get_status_colors(status: UIStatus | str) -> tuple[str, str, str]:
    """Return (background_color, text_color, border_color) for a given UI status."""
    stat_str = status.value if isinstance(status, UIStatus) else str(status).upper()

    if stat_str in ("VERIFIED", "COMPLETED", "NORMAL"):
        return (Colors.GREEN_BG, Colors.GREEN_BRIGHT, Colors.GREEN)
    elif stat_str in ("UNCERTAIN", "WARNING"):
        return (Colors.AMBER_BG, Colors.AMBER_BRIGHT, Colors.AMBER)
    elif stat_str in ("DEVIATION", "SYSTEM_FAILED"):
        return (Colors.RED_BG, Colors.RED_BRIGHT, Colors.RED)
    elif stat_str in ("ACTIVE", "RECOVERY"):
        return (Colors.BLUE_BG, Colors.BLUE_BRIGHT, Colors.BLUE)
    elif stat_str == "OFFLINE":
        return (Colors.BG_SURFACE, Colors.AMBER_BRIGHT, Colors.BORDER_DEFAULT)
    else:
        return (Colors.BG_SURFACE, Colors.TEXT_SECONDARY, Colors.BORDER_DEFAULT)


MAIN_STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {Colors.BG_DARKEST};
    color: {Colors.TEXT_PRIMARY};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

QWidget {{
    color: {Colors.TEXT_PRIMARY};
}}

QFrame#PanelFrame {{
    background-color: {Colors.BG_PANEL};
    border: 1px solid {Colors.BORDER_DEFAULT};
    border-radius: 6px;
}}

QFrame#CardFrame {{
    background-color: {Colors.BG_SURFACE};
    border: 1px solid {Colors.BORDER_DEFAULT};
    border-radius: 4px;
}}

QLabel {{
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#HeaderTitle {{
    font-size: 16px;
    font-weight: bold;
    color: {Colors.TEXT_PRIMARY};
    letter-spacing: 0.5px;
}}

QLabel#SectionTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {Colors.TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 1.0px;
}}

QLabel#StepTitle {{
    font-size: 18px;
    font-weight: bold;
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#NextActionText {{
    font-size: 15px;
    font-weight: 600;
    color: {Colors.BLUE_BRIGHT};
}}

QPushButton {{
    background-color: {Colors.BG_SURFACE};
    border: 1px solid {Colors.BORDER_DEFAULT};
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
    color: {Colors.TEXT_PRIMARY};
}}

QPushButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.BORDER_FOCUS};
}}

QPushButton:pressed {{
    background-color: {Colors.BG_DARKEST};
}}

QPushButton#PrimaryButton {{
    background-color: {Colors.GREEN};
    border-color: {Colors.GREEN_BRIGHT};
    color: {Colors.TEXT_WHITE};
}}

QPushButton#PrimaryButton:hover {{
    background-color: {Colors.GREEN_BRIGHT};
}}

QPushButton#DangerButton {{
    background-color: {Colors.RED};
    border-color: {Colors.RED_BRIGHT};
    color: {Colors.TEXT_WHITE};
}}

QPushButton#NavButton {{
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    color: {Colors.TEXT_SECONDARY};
    border-radius: 4px;
}}

QPushButton#NavButton:hover {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT_PRIMARY};
}}

QPushButton#NavButton:checked {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.BLUE_BRIGHT};
    border-left: 3px solid {Colors.BLUE_BRIGHT};
}}

QProgressBar {{
    border: 1px solid {Colors.BORDER_DEFAULT};
    border-radius: 3px;
    background-color: {Colors.BG_DARKEST};
    text-align: center;
    color: {Colors.TEXT_PRIMARY};
    font-size: 10px;
}}

QProgressBar::chunk {{
    background-color: {Colors.BLUE};
    border-radius: 2px;
}}

QTableWidget {{
    background-color: {Colors.BG_DARKEST};
    border: 1px solid {Colors.BORDER_DEFAULT};
    gridline-color: {Colors.BORDER_MUTED};
    color: {Colors.TEXT_PRIMARY};
}}

QHeaderView::section {{
    background-color: {Colors.BG_PANEL};
    border: 1px solid {Colors.BORDER_MUTED};
    padding: 4px;
    font-weight: bold;
    font-size: 11px;
    color: {Colors.TEXT_SECONDARY};
}}

QScrollBar:vertical {{
    background: {Colors.BG_DARKEST};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {Colors.BORDER_DEFAULT};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Colors.TEXT_MUTED};
}}
"""
