"""Unit tests for the subsystem health monitoring manager."""

import pytest

from core.health.manager import HealthManager
from core.health.types import HealthComponent, HealthState


def test_health_registration_and_heartbeat():
    """Verify heartbeat updates component status and timestamp."""
    manager = HealthManager()
    cam_health = manager.get_component_health(HealthComponent.CAMERA)
    assert cam_health.state == HealthState.NORMAL

    # Send heartbeat with metrics
    event = manager.heartbeat(
        HealthComponent.CAMERA,
        state=HealthState.NORMAL,
        metrics={"fps": 30.0, "dropped_frames": 0},
        message="Running normally",
    )
    assert event.component == "CAMERA"
    assert event.metrics["fps"] == 30.0


def test_health_callback_on_state_change():
    """Verify callback is triggered when subsystem state transitions."""
    transitions = []

    def on_change(event):
        transitions.append(event)

    manager = HealthManager(on_health_changed=on_change)

    # Transition from NORMAL to DEGRADED
    manager.heartbeat(HealthComponent.CAMERA, state=HealthState.DEGRADED, message="Frame rate low")
    assert len(transitions) == 1
    assert transitions[0].state == HealthState.DEGRADED

    # Same state should not re-trigger transition callback
    manager.heartbeat(HealthComponent.CAMERA, state=HealthState.DEGRADED, message="Still low")
    assert len(transitions) == 1


def test_overall_health_aggregation():
    """Verify system-wide health evaluation rules."""
    manager = HealthManager()
    assert manager.get_overall_health() == HealthState.NORMAL

    # Non-critical auxiliary failure (VOICE) -> DEGRADED
    manager.heartbeat(HealthComponent.VOICE, state=HealthState.FAILED, message="Audio device busy")
    assert manager.get_overall_health() == HealthState.DEGRADED

    # Critical failure (CAMERA) -> FAILED
    manager.heartbeat(HealthComponent.CAMERA, state=HealthState.FAILED, message="Sensor disconnected")
    assert manager.get_overall_health() == HealthState.FAILED

    # Recover camera -> back to DEGRADED (since VOICE is still failed)
    manager.heartbeat(HealthComponent.CAMERA, state=HealthState.NORMAL, message="Reconnected")
    assert manager.get_overall_health() == HealthState.DEGRADED

    # Recover voice -> NORMAL
    manager.heartbeat(HealthComponent.VOICE, state=HealthState.NORMAL)
    assert manager.get_overall_health() == HealthState.NORMAL
