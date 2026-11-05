"""Integrated Soak and Stability Test (D11.22, D11.25)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest

from core.camera.interface import FrameData
from core.mission.lifecycle import MissionLifecycleState
from core.mission.orchestrator import MissionOrchestrator


def test_integrated_soak_stability(tmp_path: Path):
    """Execute continuous multi-frame processing loop and verify resource stability."""
    orchestrator = MissionOrchestrator(
        profile_name="demo",
        root_dir=str(tmp_path),
    )
    orchestrator.boot()
    orchestrator.run_self_test()
    run_id = "SOAK_TEST_RUN"
    orchestrator.start_mission("DEMO_EXP_001", run_id=run_id)

    # Process 60 frames continuously
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_frame[120:180, 120:180] = [0, 0, 255]

    latencies = []
    for f_idx in range(1, 61):
        t0 = time.perf_counter()
        fd = FrameData(
            frame_id=f_idx,
            image=dummy_frame,
            timestamp_mono=time.monotonic(),
            timestamp_wall=datetime.now(timezone.utc),
            source_id="SOAK_SIM",
        )
        res = orchestrator.process_frame(fd)
        dt = time.perf_counter() - t0
        latencies.append(dt)

        assert res["frame_id"] == f_idx
        assert orchestrator.lifecycle.state in (
            MissionLifecycleState.RUNNING,
            MissionLifecycleState.RECOVERY,
            MissionLifecycleState.COMPLETED,
        )

    # Performance invariants
    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 0.250  # Must process under 250ms per frame in test environment
    assert orchestrator._total_frames == 60

    report = orchestrator.complete_mission()
    assert report is not None
    assert (tmp_path / "data" / "runs" / run_id / "mission_report.json").exists()

    orchestrator.shutdown()
    assert orchestrator.lifecycle.state == MissionLifecycleState.STOPPED
