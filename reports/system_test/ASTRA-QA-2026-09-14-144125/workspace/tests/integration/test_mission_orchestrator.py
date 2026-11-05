"""Integration tests for MissionOrchestrator (D11.01, D11.02, D11.03, D11.04)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest

from core.camera.interface import FrameData
from core.mission.lifecycle import MissionLifecycleState
from core.mission.orchestrator import MissionOrchestrator
from core.mission.event_bus import UnifiedEventBus, CorrelationContext


def test_mission_orchestrator_lifecycle(tmp_path: Path):
    """Verify complete orchestrator lifecycle from boot to complete_mission and shutdown."""
    orchestrator = MissionOrchestrator(
        profile_name="demo",
        root_dir=str(tmp_path),
    )

    # 1. Boot
    assert orchestrator.lifecycle.state == MissionLifecycleState.BOOT
    boot_ok = orchestrator.boot()
    assert boot_ok is True
    assert orchestrator.lifecycle.state == MissionLifecycleState.SELF_TEST

    # 2. Self-Test
    test_res = orchestrator.run_self_test()
    assert test_res["storage"] == "PASS"
    assert test_res["database"] == "PASS"
    assert test_res["model"] == "PASS"
    assert orchestrator.lifecycle.state == MissionLifecycleState.READY

    # 3. Start Mission
    run_id = "TEST_RUN_001"
    start_ok = orchestrator.start_mission(
        experiment_id="DEMO_EXP_001",
        run_id=run_id,
        camera_profile="VIEW_LEFT",
    )
    assert start_ok is True
    assert orchestrator.lifecycle.state == MissionLifecycleState.RUNNING
    assert orchestrator.active_run_id == run_id

    # Check snapshots created by run manager
    run_dir = tmp_path / "data" / "runs" / run_id
    assert run_dir.exists()
    assert (run_dir / "config_snapshot.yaml").exists()
    assert (run_dir / "model_snapshot.json").exists()
    assert (run_dir / "version_metadata.json").exists()

    # 4. Process Frames
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add a colored rectangle to trigger detection
    dummy_img[100:200, 100:200] = [0, 0, 255]  # Red box in BGR

    fd = FrameData(
        frame_id=1,
        image=dummy_img,
        timestamp_mono=time.monotonic(),
        timestamp_wall=datetime.now(timezone.utc),
        source_id="TEST_SOURCE",
    )
    res = orchestrator.process_frame(fd)
    assert res["frame_id"] == 1
    assert "met" in res
    assert "decision" in res

    # 5. Complete Mission
    report = orchestrator.complete_mission()
    assert orchestrator.lifecycle.state == MissionLifecycleState.COMPLETED
    assert report is not None
    assert (run_dir / "mission_report.json").exists()
    assert (run_dir / "mission_report.html").exists()
    assert (run_dir / "events.json").exists()

    # 6. Shutdown
    orchestrator.shutdown()
    assert orchestrator.lifecycle.state == MissionLifecycleState.STOPPED


def test_mission_orchestrator_event_bus_and_correlation(tmp_path: Path):
    """Verify typed envelope events and correlation context propagation."""
    bus = UnifiedEventBus()
    received = []

    bus.subscribe(lambda ev: received.append(ev))

    context = CorrelationContext(
        mission_id="ASTRA_M01",
        run_id="RUN_101",
        experiment_id="DEMO_EXP_001",
        step_id="STEP_01",
    )

    bus.publish("StepCandidateFound", context, {"score": 0.95})
    bus.publish("StepVerified", context, {"confidence": 0.98})

    assert len(received) == 2
    assert received[0].event_type == "StepCandidateFound"
    assert received[0].context.mission_id == "ASTRA_M01"
    assert received[0].sequence == 1
    assert received[1].event_type == "StepVerified"
    assert received[1].sequence == 2

    # Verify event serialization
    d = received[1].to_dict()
    assert d["event_type"] == "StepVerified"
    assert d["sequence"] == 2
    assert d["context"]["step_id"] == "STEP_01"


def test_orchestrator_abort_mission(tmp_path: Path):
    """Verify clean abort sequence and artifact preservation."""
    orchestrator = MissionOrchestrator(
        profile_name="demo",
        root_dir=str(tmp_path),
    )
    orchestrator.boot()
    orchestrator.run_self_test()
    run_id = "ABORT_RUN_001"
    orchestrator.start_mission("DEMO_EXP_001", run_id=run_id)

    orchestrator.abort_mission("Astronaut manual emergency abort")
    assert orchestrator.lifecycle.state == MissionLifecycleState.ABORTED

    run_dir = tmp_path / "data" / "runs" / run_id
    assert (run_dir / "mission_report.json").exists()
    orchestrator.shutdown()
