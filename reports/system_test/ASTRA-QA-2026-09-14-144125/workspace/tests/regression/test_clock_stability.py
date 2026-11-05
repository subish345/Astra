"""Regression Test for FINDING-005 / CAPA-005: Clock display formatting stability."""

import pytest
from PySide6.QtWidgets import QApplication

from apps.ground_monitor.panels.header_panel import HeaderPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_clock_formatting_stability(qapp) -> None:
    """Verify quantized HH:MM:SS format preserves stable layout width across seconds."""
    header = HeaderPanel()

    # Zero seconds
    header.set_clocks(0.0, "2026-09-13T12:00:00Z")
    assert "MET: 00:00:00" in header.clock_badge.text()

    # Fractional seconds: 75.8492s -> 00:01:15
    header.set_clocks(75.8492, "2026-09-13T12:01:15Z")
    assert "MET: 00:01:15" in header.clock_badge.text()

    # Multi-hour seconds: 3665.123s -> 01:01:05
    header.set_clocks(3665.123, "2026-09-13T13:01:05Z")
    assert "MET: 01:01:05" in header.clock_badge.text()
