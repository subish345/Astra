"""Comprehensive Multi-Dimensional Profiler for ASTRA-EA.

Tracks per-stage latency, end-to-end decision latency (capture -> assurance),
throughput (camera FPS, compute FPS, effective E2E FPS), CPU/GPU resource utilization,
memory RSS, queue backpressure, and calculates statistical percentiles (P50, P90, P95, P99).
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import psutil

from core.common.logging import get_logger
from core.optimization.backend import ComputeBackend, PlatformInspector

logger = get_logger("OPTIMIZATION")

STAGE_NAMES = [
    "capture",
    "detection",
    "pose",
    "hands",
    "tracking",
    "interaction",
    "activity",
    "evidence",
    "procedure",
    "assurance",
    "ui_publish",
    "stream",
    "recording",
]


@dataclass
class PercentileStats:
    """Statistical summary of latency distribution in milliseconds."""
    p50: float
    p90: float
    p95: float
    p99: float
    mean: float
    min: float
    max: float
    std_dev: float
    samples: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "p50_ms": round(self.p50, 3),
            "p90_ms": round(self.p90, 3),
            "p95_ms": round(self.p95, 3),
            "p99_ms": round(self.p99, 3),
            "mean_ms": round(self.mean, 3),
            "min_ms": round(self.min, 3),
            "max_ms": round(self.max, 3),
            "std_dev_ms": round(self.std_dev, 3),
            "samples": self.samples,
        }


def calculate_percentiles(values: List[float]) -> PercentileStats:
    """Compute exact statistical percentiles for a list of floating-point measurements."""
    if not values:
        return PercentileStats(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def _get_p(p: float) -> float:
        idx = int(math.ceil((p / 100.0) * n)) - 1
        return sorted_vals[max(0, min(idx, n - 1))]

    mean_val = sum(sorted_vals) / n
    variance = sum((x - mean_val) ** 2 for x in sorted_vals) / n
    std_dev = math.sqrt(variance)

    return PercentileStats(
        p50=_get_p(50),
        p90=_get_p(90),
        p95=_get_p(95),
        p99=_get_p(99),
        mean=mean_val,
        min=sorted_vals[0],
        max=sorted_vals[-1],
        std_dev=std_dev,
        samples=n,
    )


class PipelineProfiler:
    """Measures fine-grained timing and resource usage across pipeline execution."""

    def __init__(self, backend: Optional[ComputeBackend] = None) -> None:
        self.backend = backend or PlatformInspector.create_backend()
        self.process = psutil.Process(os.getpid())

        # Per-stage latency buffers (in ms)
        self.stage_latencies: Dict[str, List[float]] = {stage: [] for stage in STAGE_NAMES}
        # End-to-end latency buffer (capture_timestamp -> assurance_timestamp)
        self.e2e_latencies: List[float] = []

        # Queue tracking
        self.queue_sizes: Dict[str, List[int]] = {}
        self.max_queue_sizes: Dict[str, int] = {}
        self.dropped_frames: Dict[str, int] = {}

        # Resource samples
        self.cpu_samples: List[float] = []
        self.system_cpu_samples: List[float] = []
        self.ram_samples_mb: List[float] = []
        self.vram_samples_mb: List[float] = []

        # Temporal anchors
        self._start_time: Optional[float] = None
        self._total_frames_captured: int = 0
        self._total_frames_processed: int = 0

    def start(self) -> None:
        """Mark the beginning of a profiling session."""
        self._start_time = time.perf_counter()
        # Prime psutil cpu_percent
        self.process.cpu_percent()
        psutil.cpu_percent()

    def record_stage(self, stage_name: str, duration_ms: float) -> None:
        """Record the execution duration of a specific pipeline component."""
        if stage_name in self.stage_latencies:
            self.stage_latencies[stage_name].append(duration_ms)

    def record_e2e(self, capture_ts: float, decision_ts: Optional[float] = None) -> float:
        """Record end-to-end decision latency from frame capture to assurance decision."""
        end_ts = decision_ts if decision_ts is not None else time.perf_counter()
        latency_ms = (end_ts - capture_ts) * 1000.0
        self.e2e_latencies.append(latency_ms)
        self._total_frames_processed += 1
        return latency_ms

    def record_frame_captured(self) -> None:
        """Increment count of raw camera/source frames ingested."""
        self._total_frames_captured += 1

    def record_queue_status(self, queue_name: str, current_size: int, dropped: int = 0) -> None:
        """Record queue depth and frame drops for backpressure profiling."""
        if queue_name not in self.queue_sizes:
            self.queue_sizes[queue_name] = []
            self.max_queue_sizes[queue_name] = 0
            self.dropped_frames[queue_name] = 0

        self.queue_sizes[queue_name].append(current_size)
        if current_size > self.max_queue_sizes[queue_name]:
            self.max_queue_sizes[queue_name] = current_size
        self.dropped_frames[queue_name] += dropped

    def sample_system_resources(self) -> Dict[str, Any]:
        """Sample current CPU, RAM, and GPU resource utilization."""
        proc_cpu = self.process.cpu_percent()
        sys_cpu = psutil.cpu_percent()
        rss_mb = self.process.memory_info().rss / (1024 * 1024)

        self.cpu_samples.append(proc_cpu)
        self.system_cpu_samples.append(sys_cpu)
        self.ram_samples_mb.append(rss_mb)

        mem_info = self.backend.memory_info()
        vram_used = mem_info.get("vram_used_mb")
        if vram_used is not None:
            self.vram_samples_mb.append(float(vram_used))

        return {
            "process_cpu_percent": round(proc_cpu, 1),
            "system_cpu_percent": round(sys_cpu, 1),
            "process_rss_mb": round(rss_mb, 2),
            "backend_info": mem_info,
        }

    def generate_report(self) -> Dict[str, Any]:
        """Compile comprehensive benchmark and profiling metrics."""
        elapsed = (time.perf_counter() - self._start_time) if self._start_time else 1.0
        elapsed = max(elapsed, 0.001)

        camera_fps = self._total_frames_captured / elapsed
        effective_e2e_fps = self._total_frames_processed / elapsed

        # Compute FPS capacity based on mean compute latency (Perception + Interaction + Activity + Procedure + Assurance)
        compute_stages = ["detection", "pose", "hands", "tracking", "interaction", "activity", "evidence", "procedure", "assurance"]
        total_compute_mean = sum(
            calculate_percentiles(self.stage_latencies[s]).mean
            for s in compute_stages
            if self.stage_latencies[s]
        )
        compute_fps_capacity = (1000.0 / total_compute_mean) if total_compute_mean > 0 else 0.0

        stage_reports: Dict[str, Any] = {}
        for stage in STAGE_NAMES:
            stats = calculate_percentiles(self.stage_latencies[stage])
            stage_reports[stage] = stats.to_dict()

        e2e_stats = calculate_percentiles(self.e2e_latencies)

        # Resource summary
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0.0
        peak_cpu = max(self.cpu_samples) if self.cpu_samples else 0.0
        avg_sys_cpu = sum(self.system_cpu_samples) / len(self.system_cpu_samples) if self.system_cpu_samples else 0.0
        avg_ram = sum(self.ram_samples_mb) / len(self.ram_samples_mb) if self.ram_samples_mb else 0.0
        peak_ram = max(self.ram_samples_mb) if self.ram_samples_mb else 0.0
        avg_vram = sum(self.vram_samples_mb) / len(self.vram_samples_mb) if self.vram_samples_mb else None
        peak_vram = max(self.vram_samples_mb) if self.vram_samples_mb else None

        # Queue summary
        queue_summary: Dict[str, Any] = {}
        for q_name, sizes in self.queue_sizes.items():
            avg_sz = sum(sizes) / len(sizes) if sizes else 0.0
            queue_summary[q_name] = {
                "current_size": sizes[-1] if sizes else 0,
                "average_size": round(avg_sz, 2),
                "max_observed_size": self.max_queue_sizes.get(q_name, 0),
                "dropped_frames": self.dropped_frames.get(q_name, 0),
            }

        platform_tel = PlatformInspector.get_telemetry(self.backend.backend_type)

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "platform": platform_tel.to_dict(),
            "duration_seconds": round(elapsed, 2),
            "throughput": {
                "camera_fps": round(camera_fps, 2),
                "compute_capacity_fps": round(compute_fps_capacity, 2),
                "effective_e2e_fps": round(effective_e2e_fps, 2),
                "total_frames_captured": self._total_frames_captured,
                "total_frames_processed": self._total_frames_processed,
            },
            "end_to_end_latency": e2e_stats.to_dict(),
            "stages": stage_reports,
            "resources": {
                "avg_process_cpu_percent": round(avg_cpu, 1),
                "peak_process_cpu_percent": round(peak_cpu, 1),
                "avg_system_cpu_percent": round(avg_sys_cpu, 1),
                "avg_ram_mb": round(avg_ram, 2),
                "peak_ram_mb": round(peak_ram, 2),
                "avg_vram_mb": round(avg_vram, 2) if avg_vram is not None else "N/A",
                "peak_vram_mb": round(peak_vram, 2) if peak_vram is not None else "N/A",
            },
            "queues": queue_summary,
        }

    def print_ascii_summary(self, report: Dict[str, Any]) -> None:
        """Print clean, space-operations formatted ASCII benchmark report."""
        p = report["platform"]
        t = report["throughput"]
        e = report["end_to_end_latency"]
        r = report["resources"]
        s = report["stages"]

        print("=" * 80)
        print(" ASTRA-EA SYSTEM BENCHMARK & PERFORMANCE PROFILE")
        print("=" * 80)
        print(f"Platform:       {p['os_name']} {p['os_release']} ({p['architecture']}) | Python {p['python_version']}")
        print(f"Compute Target: {p['active_backend'].upper()} ({p['gpu_name'] if p['gpu_available'] else p['cpu_model']})")
        print(f"Host Memory:    {p['total_ram_gb']} GB RAM | CPU Cores: {p['cpu_cores_physical']} Phys / {p['cpu_cores_logical']} Log")
        print(f"Duration:       {report['duration_seconds']}s | Total Processed: {t['total_frames_processed']} frames")
        print("-" * 80)
        print("THROUGHPUT & LATENCY BREAKDOWN")
        print(f"Camera Ingestion:       {t['camera_fps']} FPS")
        print(f"Compute Capacity:       {t['compute_capacity_fps']} FPS")
        print(f"Effective End-to-End:   {t['effective_e2e_fps']} FPS")
        print(f"End-to-End Latency:     P50: {e['p50_ms']} ms | P90: {e['p90_ms']} ms | P95: {e['p95_ms']} ms | P99: {e['p99_ms']} ms")
        print("-" * 80)
        print(f"{'PIPELINE STAGE':<22} {'P50 (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10} {'Mean (ms)':<10} {'Max (ms)':<10}")
        print("-" * 80)
        for stage_name, st in s.items():
            if st["samples"] > 0:
                print(
                    f"{stage_name:<22} "
                    f"{st['p50_ms']:<10.3f} "
                    f"{st['p95_ms']:<10.3f} "
                    f"{st['p99_ms']:<10.3f} "
                    f"{st['mean_ms']:<10.3f} "
                    f"{st['max_ms']:<10.3f}"
                )
        print("-" * 80)
        print("HOST RESOURCE CONSUMPTION")
        print(f"Process CPU:    Avg {r['avg_process_cpu_percent']}% | Peak {r['peak_process_cpu_percent']}% (System Avg: {r['avg_system_cpu_percent']}%)")
        print(f"Process RAM:    Avg {r['avg_ram_mb']} MB | Peak {r['peak_ram_mb']} MB")
        if r['avg_vram_mb'] != "N/A":
            print(f"GPU VRAM:       Avg {r['avg_vram_mb']} MB | Peak {r['peak_vram_mb']} MB")
        else:
            print("GPU VRAM:       NOT AVAILABLE / CPU RUNTIME")

        if report.get("queues"):
            print("-" * 80)
            print("QUEUE BACKPRESSURE TELEMETRY")
            for qn, qinfo in report["queues"].items():
                print(f"Queue [{qn}]: Current {qinfo['current_size']} | Max {qinfo['max_observed_size']} | Drops {qinfo['dropped_frames']}")

        print("=" * 80)
