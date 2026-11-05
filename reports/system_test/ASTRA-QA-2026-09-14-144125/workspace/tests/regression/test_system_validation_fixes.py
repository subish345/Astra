"""Regression test suite for defects identified during Complete System Validation Campaign.

Tests:
1. BenchmarkReport.throughput_fps alias property (cmd_perception_test compatibility).
2. Track.label alias property and video panel track label extraction.
3. ProcedureState.status alias property and worker completion check compatibility.
"""

from __future__ import annotations

import pytest
from core.perception.benchmark import BenchmarkReport
from core.perception.types import Track, TrackState, BoundingBox
from core.procedure.types import ProcedureState, ProcedureStatus


def test_benchmark_report_throughput_fps_property() -> None:
    """Ensure BenchmarkReport provides throughput_fps alias."""
    report = BenchmarkReport(
        total_frames=30,
        duration_seconds=1.0,
        avg_fps=28.5,
        min_fps=25.0,
        max_fps=30.0,
        p50_latency_ms=15.0,
        p95_latency_ms=18.0,
        p99_latency_ms=20.0,
        avg_cpu_percent=12.0,
        gpu_memory_used_mb=None,
    )
    assert report.throughput_fps == 28.5


def test_track_label_property() -> None:
    """Ensure Track provides label alias matching class_name."""
    track = Track(
        track_id=1,
        class_name="RED_BOX",
        bbox=BoundingBox(0.1, 0.1, 0.3, 0.3),
        confidence=0.95,
        state=TrackState.VISIBLE,
    )
    assert track.label == "RED_BOX"
    # Ensure set comprehension in video_panel works cleanly
    labels = {getattr(track, "label", getattr(track, "class_name", "")).upper()}
    assert "RED_BOX" in labels


def test_procedure_state_status_property() -> None:
    """Ensure ProcedureState provides status alias matching procedure_status."""
    state = ProcedureState(
        experiment_id="EXP_001",
        run_id="RUN_001",
        procedure_status=ProcedureStatus.COMPLETED,
    )
    assert state.status == ProcedureStatus.COMPLETED
    assert state.status.value == "COMPLETED"
