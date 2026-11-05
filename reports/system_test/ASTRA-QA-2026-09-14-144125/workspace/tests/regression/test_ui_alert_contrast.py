"""Regression Test for FINDING-004 / CAPA-004: UI Alert acknowledge button ergonomics."""

import pytest
from PySide6.QtWidgets import QApplication

from apps.ground_monitor.panels.alert_panel import AlertPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_alert_ack_button_ergonomics(qapp) -> None:
    """Verify alert acknowledge button styling, enabling, and click callback."""
    panel = AlertPanel()
    assert panel.ack_btn is not None
    assert panel.ack_btn.text() == "ACKNOWLEDGE"
    assert not panel.ack_btn.isEnabled()  # Disabled on nominal

    # Callback tracking
    ack_called = []
    panel.set_ack_callback(lambda: ack_called.append(True))

    # Set active WARNING alert
    panel.set_alert(
        deviation="Wrong apparatus gripped: Expected Centrifuge Tube, observed Pipette Tip Box",
        severity="WARNING",
        recovery="Return pipette box to rack; retrieve centrifuge tube.",
    )
    panel.set_lifecycle("RECEIVED")

    # Button must become enabled with high-contrast active state
    assert panel.ack_btn.isEnabled()
    assert "#3b82f6" in panel.ack_btn.styleSheet()

    # Click button
    panel.ack_btn.click()
    assert len(ack_called) == 1
    assert panel.lifecycle_badge.text() == "ACKNOWLEDGED"
