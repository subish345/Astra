"""Performance benchmarking profiler for Phase 3 Activity and Interaction subsystems.

Measures stage-by-stage latencies (Perception, Interaction, Temporal, Activity, Total),
computes P50/P95/P99 percentiles, throughput (FPS), and hardware resource consumption.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np
import psutil

from core.common.logging import get_logger

logger = get_logger("BENCHMARK")


@dataclass
class Phase3LatencyRecord:
    """Microsecond-precise latency metrics for a single end-to-end frame cycle."""
    perception_ms: float
    interaction_ms: float
    temporal_ms: float
    activity_ms: float
    total_ms: float


@dataclass
class Phase3BenchmarkReport:
    """Summary statistics for Phase 3 pipeline execution."""
    frame_count: int
    duration_seconds: float
    fps: float
    p50_total_ms: float
    p95_total_ms: float
    p99_total_ms: float
    mean_perception_ms: float
    mean_interaction_ms: float
    mean_temporal_ms: float
    mean_activity_ms: float
    cpu_percent: float
    ram_used_mb: float
    gpu_name: Optional[str] = None


class ActivityBenchmark:
    """Accumulates frame latency profiles and generates engineering benchmark reports."""

    def __init__(self):
        self.records: List[Phase3LatencyRecord] = []
        self._start_time = time.perf_counter()
        self._process = psutil.Process()

    def record_frame(
        self,
        perception_ms: float,
        interaction_ms: float,
        temporal_ms: float,
        activity_ms: float,
        total_ms: float,
    ) -> None:
        """Record the timing of an individual frame."""
        self.records.append(
            Phase3LatencyRecord(
                perception_ms=perception_ms,
                interaction_ms=interaction_ms,
                temporal_ms=temporal_ms,
                activity_ms=activity_ms,
                total_ms=total_ms,
            )
        )

    def generate_report(self) -> Phase3BenchmarkReport:
        """Compute summary statistics across all collected records."""
        duration = max(0.001, time.perf_counter() - self._start_time)
        count = len(self.records)
        fps = round(count / duration, 1) if count > 0 else 0.0

        if count > 0:
            totals = [r.total_ms for r in self.records]
            p50 = round(float(np.percentile(totals, 50)), 2)
            p95 = round(float(np.percentile(totals, 95)), 2)
            p99 = round(float(np.percentile(totals, 99)), 2)

            mean_p = round(float(np.mean([r.perception_ms for r in self.records])), 2)
            mean_i = round(float(np.mean([r.interaction_ms for r in self.records])), 2)
            mean_t = round(float(np.mean([r.temporal_ms for r in self.records])), 2)
            mean_a = round(float(np.mean([r.activity_ms for r in self.records])), 2)
        else:
            p50, p95, p99 = 0.0, 0.0, 0.0
            mean_p, mean_i, mean_t, mean_a = 0.0, 0.0, 0.0, 0.0

        cpu = self._process.cpu_percent()
        ram_mb = round(self._process.memory_info().rss / (1024 * 1024), 1)

        return Phase3BenchmarkReport(
            frame_count=count,
            duration_seconds=round(duration, 2),
            fps=fps,
            p50_total_ms=p50,
            p95_total_ms=p95,
            p99_total_ms=p99,
            mean_perception_ms=mean_p,
            mean_interaction_ms=mean_i,
            mean_temporal_ms=mean_t,
            mean_activity_ms=mean_a,
            cpu_percent=cpu,
            ram_used_mb=ram_mb,
        )

    def print_summary(self, report: Phase3BenchmarkReport) -> None:
        """Output human-readable benchmark summary."""
        print("\n============================================================")
        print(" ASTRA-EA PHASE 3 PIPELINE BENCHMARK REPORT")
        print("============================================================")
        print(f"Processed Frames:       {report.frame_count}")
        print(f"Elapsed Time:           {report.duration_seconds:.2f}s")
        print(f"Throughput:             {report.fps:.1f} FPS")
        print("-" * 60)
        print("LATENCY PERCENTILES (End-to-End Pipeline):")
        print(f"  P50 (Median):         {report.p50_total_ms:.2f} ms")
        print(f"  P95:                  {report.p95_total_ms:.2f} ms")
        print(f"  P99:                  {report.p99_total_ms:.2f} ms")
        print("-" * 60)
        print("AVERAGE LATENCY BY SUBSYSTEM:")
        print(f"  Perception Stage:     {report.mean_perception_ms:.2f} ms")
        print(f"  Interaction Stage:    {report.mean_interaction_ms:.2f} ms")
        print(f"  Temporal Buffer:      {report.mean_temporal_ms:.2f} ms")
        print(f"  Activity Engine:      {report.mean_activity_ms:.2f} ms")
        print("-" * 60)
        print("RESOURCE UTILIZATION:")
        print(f"  CPU Usage:            {report.cpu_percent:.1f}%")
        print(f"  RAM RSS:              {report.ram_used_mb:.1f} MB")
        print("============================================================\n")
