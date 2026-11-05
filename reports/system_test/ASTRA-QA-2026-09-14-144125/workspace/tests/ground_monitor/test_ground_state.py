# ==============================================================================
# ASTRA-EA Ground Monitor State Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Automated tests for GroundMonitorState mutations and event processing."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication

from apps.ground_monitor.state import GroundMonitorState
from streaming.events.schema import EventFilter, EventSeverity, EventType, GroundEvent


@pytest.fixture(scope="module")
def qapp() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_ground_state_initial_values(qapp: QCoreApplication) -> None:
    state = GroundMonitorState()
    assert state.link_status == "OFFLINE"
    assert state.experiment_id == "DEMO_EXP_001"
    assert state.total_steps == 4
    assert state.assurance_decision == "UNCERTAIN"
    assert state.active_deviation is None


def test_ground_state_process_events_lifecycle(qapp: QCoreApplication) -> None:
    state = GroundMonitorState()

    # 1. Experiment Started
    evt_start = GroundEvent(
        event_id="EVT_01",
        sequence_num=1,
        experiment_id="DEMO_EXP_001",
        run_id="RUN_0007",
        event_type=EventType.EXPERIMENT_STARTED,
        message="Mission Started",
        payload={"total_steps": 4, "first_step_id": "STEP_01"},
    )
    state.process_event(evt_start, latency_ms=1.2)
    assert state.run_id == "RUN_0007"
    assert state.current_step_id == "STEP_01"

    # 2. Step 01 Verified
    evt_step1 = GroundEvent(
        event_id="EVT_02",
        sequence_num=2,
        experiment_id="DEMO_EXP_001",
        run_id="RUN_0007",
        event_type=EventType.STEP_VERIFIED,
        step_id="STEP_01",
        status="VERIFIED",
        message="Step 01 verified",
        payload={"step_index": 0, "activity": "APPROACH"},
    )
    state.process_event(evt_step1, latency_ms=2.1)
    assert state.assurance_decision == "VERIFIED"
    assert state.current_activity == "APPROACH"

    # 3. Deviation Detected on Step 02
    evt_dev = GroundEvent(
        event_id="EVT_03",
        sequence_num=3,
        experiment_id="DEMO_EXP_001",
        run_id="RUN_0007",
        event_type=EventType.DEVIATION_DETECTED,
        step_id="STEP_02",
        status="DEVIATION",
        severity=EventSeverity.DANGER,
        message="WRONG_OBJECT: Expected RED_BOX, Observed YELLOW_BOX",
        payload={"recovery_action": "Return YELLOW_BOX and grasp RED_BOX"},
    )
    state.process_event(evt_dev, latency_ms=1.8)
    assert state.assurance_decision == "DEVIATION"
    assert "WRONG_OBJECT" in (state.active_deviation or "")
    assert "RED_BOX" in (state.recovery_action or "")

    # 4. Recovery Verified
    evt_rec = GroundEvent(
        event_id="EVT_04",
        sequence_num=4,
        experiment_id="DEMO_EXP_001",
        run_id="RUN_0007",
        event_type=EventType.RECOVERY_VERIFIED,
        step_id="STEP_02",
        status="VERIFIED",
        message="Recovery Verified",
    )
    state.process_event(evt_rec, latency_ms=1.5)
    assert state.assurance_decision == "VERIFIED"
    assert state.active_deviation is None
    assert state.recovery_action is None


def test_timeline_filtering(qapp: QCoreApplication) -> None:
    state = GroundMonitorState()

    state.process_event(GroundEvent(
        event_id="E1", sequence_num=1, event_type=EventType.STEP_VERIFIED, message="Step 1"
    ))
    state.process_event(GroundEvent(
        event_id="E2", sequence_num=2, event_type=EventType.DEVIATION_DETECTED, message="Deviation"
    ))
    state.process_event(GroundEvent(
        event_id="E3", sequence_num=3, event_type=EventType.RECOVERY_VERIFIED, message="Recovery"
    ))
    state.process_event(GroundEvent(
        event_id="E4", sequence_num=4, event_type=EventType.HEARTBEAT, message="Heartbeat"
    ))

    assert len(state.get_filtered_timeline(EventFilter.ALL)) == 4
    assert len(state.get_filtered_timeline(EventFilter.STEPS)) == 1
    assert len(state.get_filtered_timeline(EventFilter.DEVIATIONS)) == 1
    assert len(state.get_filtered_timeline(EventFilter.RECOVERY)) == 1
    assert len(state.get_filtered_timeline(EventFilter.SYSTEM)) == 1
