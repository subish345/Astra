# ==============================================================================
# ASTRA-EA Event Stream Server Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Automated tests for GroundEvent schema, EventPublisher, SSE server, and client."""

from __future__ import annotations

import json
import time
import urllib.request
import pytest

from streaming.events.client import EventStreamClient
from streaming.events.publisher import EventPublisher
from streaming.events.schema import EventFilter, EventSeverity, EventType, GroundEvent, categorize_event
from streaming.events.server import EventStreamServer


def test_ground_event_schema_and_serialization() -> None:
    """Verify GroundEvent model validation, sequence, and SSE serialization."""
    event = GroundEvent(
        event_id="EVT_000001_ABC",
        sequence_num=1,
        experiment_id="DEMO_EXP_001",
        run_id="RUN_0001",
        event_type=EventType.STEP_VERIFIED,
        step_id="STEP_01",
        status="VERIFIED",
        severity=EventSeverity.INFO,
        message="Step 01 completed",
        payload={"step_index": 0},
    )

    sse_wire = event.to_sse()
    assert "id: 1" in sse_wire
    assert "event: STEP_VERIFIED" in sse_wire
    assert "data: " in sse_wire

    # Roundtrip JSON
    json_str = event.model_dump_json()
    parsed = GroundEvent.from_json_str(json_str)
    assert parsed.event_id == event.event_id
    assert parsed.event_type == EventType.STEP_VERIFIED
    assert parsed.severity == EventSeverity.INFO


def test_categorize_event() -> None:
    """Verify event categorization for timeline filters."""
    assert categorize_event(EventType.STEP_VERIFIED) == EventFilter.STEPS
    assert categorize_event(EventType.STEP_UNCERTAIN) == EventFilter.STEPS
    assert categorize_event(EventType.DEVIATION_DETECTED) == EventFilter.DEVIATIONS
    assert categorize_event(EventType.RECOVERY_REQUIRED) == EventFilter.RECOVERY
    assert categorize_event(EventType.RECOVERY_VERIFIED) == EventFilter.RECOVERY
    assert categorize_event(EventType.HEARTBEAT) == EventFilter.SYSTEM
    assert categorize_event(EventType.SYSTEM_HEALTH_CHANGED) == EventFilter.SYSTEM


def test_event_publisher_sequence_and_replay_buffer() -> None:
    """Verify monotonic sequence ordering and replay history retention."""
    pub = EventPublisher(buffer_capacity=10)

    for i in range(5):
        pub.create_event(
            event_type=EventType.STEP_VERIFIED,
            message=f"Step event {i}",
        )

    assert pub.current_sequence == 5
    recent = pub.get_recent_events(limit=3)
    assert len(recent) == 3
    assert recent[-1].sequence_num == 5

    # Replay events since seq 2 -> should return seq 3, 4, 5
    missed = pub.get_events_since(2)
    assert len(missed) == 3
    assert [e.sequence_num for e in missed] == [3, 4, 5]


def test_event_server_endpoints_and_sse_client() -> None:
    """Verify REST endpoints (/heartbeat, /health, /events/replay) and live SSE client reception."""
    test_port = 28770
    server = EventStreamServer(port=test_port, host="127.0.0.1", heartbeat_interval_seconds=1.0)
    server.start()
    assert server.is_running

    # 1. Heartbeat GET endpoint
    req_hb = urllib.request.Request(f"http://127.0.0.1:{test_port}/heartbeat")
    with urllib.request.urlopen(req_hb, timeout=2.0) as resp:
        assert resp.status == 200
        hb_data = json.loads(resp.read().decode())
        assert hb_data["status"] == "ONLINE"

    # 2. Health GET endpoint
    server.set_health_metrics({"camera": "ONLINE", "fps": 29.5})
    req_hl = urllib.request.Request(f"http://127.0.0.1:{test_port}/health")
    with urllib.request.urlopen(req_hl, timeout=2.0) as resp:
        hl_data = json.loads(resp.read().decode())
        assert hl_data["metrics"]["camera"] == "ONLINE"

    # 3. Connect live SSE client
    received = []
    def on_event(evt, lat):
        received.append((evt, lat))

    client = EventStreamClient(
        events_url=f"http://127.0.0.1:{test_port}/events",
        on_event_callback=on_event,
    )
    client.connect()
    time.sleep(0.3)

    # Publish live event
    server.publisher.create_event(
        event_type=EventType.STEP_VERIFIED,
        step_id="STEP_02",
        message="Live step verified",
    )

    time.sleep(0.4)
    client.disconnect()
    server.stop()

    assert not server.is_running
    assert any(e.step_id == "STEP_02" for e, _ in received)
