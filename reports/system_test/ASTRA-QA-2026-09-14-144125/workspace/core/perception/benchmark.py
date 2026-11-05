"""Perception performance benchmarking tool for ASTRA-EA.

Measures FPS throughput, percentile latency profiles (P50, P95, P99), CPU and GPU
memory utilization across continuous frame ingestion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import psutil

from core.camera.ingestion import FramePacket
from core.camera.interface import CameraSource
from core.perception.device import DeviceManager
from core.perception.pipeline import PerceptionPipeline


@dataclass
class BenchmarkReport:
    """Quantitative performance benchmarking results."""
    total_frames: int
    duration_seconds: float
    avg_fps: float
    min_fps: float
    max_fps: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_cpu_percent: float
    gpu_memory_used_mb: Optional[int]
    accuracy_status: str = "NOT EVALUATED (Requires ground-truth annotated dataset)"

    @property
    def throughput_fps(self) -> float:
        """Alias for avg_fps for CLI compatibility."""
        return self.avg_fps

    def format_text(self) -> str:
        """Format human-readable benchmark summary."""
        lines = [
            "=" * 60,
            " ASTRA-EA PERCEPTION PERFORMANCE BENCHMARK REPORT",
            "=" * 60,
            f"Frames Evaluated:    {self.total_frames}",
            f"Total Duration:      {self.duration_seconds:.2f} s",
            f"Throughput (FPS):    Avg: {self.avg_fps:.1f} | Min: {self.min_fps:.1f} | Max: {self.max_fps:.1f}",
            f"Latency (P50):       {self.p50_latency_ms:.2f} ms",
            f"Latency (P95):       {self.p95_latency_ms:.2f} ms",
            f"Latency (P99):       {self.p99_latency_ms:.2f} ms",
            f"Avg CPU Usage:       {self.avg_cpu_percent:.1f}%",
            f"GPU Memory Used:     {self.gpu_memory_used_mb} MB" if self.gpu_memory_used_mb is not None else "GPU Memory:          N/A (CPU Mode)",
            "-" * 60,
            f"Model Accuracy:      {self.accuracy_status}",
            "=" * 60,
        ]
        return "\n".join(lines)


class PerceptionBenchmark:
    """Executes deterministic latency and throughput profiling."""

    def __init__(self, pipeline: PerceptionPipeline, camera_source: CameraSource):
        self.pipeline = pipeline
        self.camera_source = camera_source

    def run(self, max_frames: int = 100) -> BenchmarkReport:
        """Execute benchmark loop across max_frames."""
        if not self.camera_source.is_active:
            self.camera_source.start()

        latencies: List[float] = []
        fps_samples: List[float] = []
        cpu_samples: List[float] = []

        dev_info = DeviceManager.get_device_info("auto")

        t_start = time.perf_counter()
        frames_processed = 0

        while frames_processed < max_frames:
            fd = self.camera_source.read()
            if fd is None:
                if not self.camera_source.is_active:
                    break
                time.sleep(0.005)
                continue

            packet = FramePacket.from_frame_data(fd, capture_fps=self.camera_source.get_fps())
            cpu_samples.append(psutil.cpu_percent(interval=None))

            state = self.pipeline.process_frame(packet)
            latencies.append(state.latency.total_ms)
            if state.fps > 0:
                fps_samples.append(state.fps)
            frames_processed += 1

        total_duration = time.perf_counter() - t_start

        avg_fps = round(frames_processed / total_duration, 1) if total_duration > 0 else 0.0
        min_fps = round(min(fps_samples), 1) if fps_samples else avg_fps
        max_fps = round(max(fps_samples), 1) if fps_samples else avg_fps

        p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
        p95 = float(np.percentile(latencies, 95)) if latencies else 0.0
        p99 = float(np.percentile(latencies, 99)) if latencies else 0.0

        avg_cpu = float(np.mean(cpu_samples)) if cpu_samples else 0.0

        return BenchmarkReport(
            total_frames=frames_processed,
            duration_seconds=round(total_duration, 2),
            avg_fps=avg_fps,
            min_fps=min_fps,
            max_fps=max_fps,
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            avg_cpu_percent=round(avg_cpu, 1),
            gpu_memory_used_mb=dev_info.vram_used_mb,
        )
