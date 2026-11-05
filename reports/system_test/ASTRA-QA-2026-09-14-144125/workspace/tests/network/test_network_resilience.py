# ==============================================================================
# ASTRA-EA Network Resilience & Reconnection Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Automated end-to-end test verifying state reconciliation after network loss."""

from __future__ import annotations

import time
import pytest

from streaming.events.client import EventStreamClient
from streaming.events.schema import EventSeverity, EventType, GroundEvent
from streaming.events.server import EventStreamServer


def test_disconnect_and_reconnection_reconciliation() -> None:
    """Verify ground client receives historical events upon reconnecting."""
    test_port = 28780
    server = EventStreamServer(port=test_port, host="127.0.0.1", heartbeat_interval_seconds=1.0)
    server.start()

    received_events = []

    def on_event(event: GroundEvent, latency_ms: float) -> None:
        received_events.append(event)

    # 1. Connect client
    client = EventStreamClient(
        events_url=f"http://127.0.0.1:{test_port}/events",
        on_event_callback=on_event,
    )
    client.connect()
    time.sleep(0.3)

    # 2. Emit Event 1 while connected
    server.publisher.create_event(
        event_type=EventType.EXPERIMENT_STARTED,
        message="Mission Started",
    )
    time.sleep(0.3)
    assert len(received_events) >= 1
    assert any(e.event_type == EventType.EXPERIMENT_STARTED for e in received_events)

    # 3. Disconnect ground client (simulate network cable unplugged)
    client.disconnect()
    time.sleep(0.2)

    # 4. Onboard continues uninterrupted, generating Event 2 and Event 3
    server.publisher.create_event(
        event_type=EventType.STEP_VERIFIED,
        step_id="STEP_01",
        message="Step 01 Verified while ground was offline",
    )
    server.publisher.create_event(
        event_type=EventType.STEP_VERIFIED,
        step_id="STEP_02",
        message="Step 02 Verified while ground was offline",
    )

    # 5. Ground restores connection (reconnects)
    client.connect()
    time.sleep(0.5)

    client.disconnect()
    server.stop()

    # 6. Verify ground client reconciled and caught up with missed events
    step_ids = [e.step_id for e in received_events if e.step_id]
    assert "STEP_01" in step_ids, "Missed event STEP_01 was not recovered on reconnect"
    assert "STEP_02" in step_ids, "Missed event STEP_02 was not recovered on reconnect"
