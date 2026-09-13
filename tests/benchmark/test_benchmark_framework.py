"""Automated tests for ASTRA-EA Profiling and Benchmark Framework (D10.01 - D10.09)."""

import time
import pytest
from core.optimization.profiler import (
    PipelineProfiler,
    PercentileStats,
    calculate_percentiles,
    STAGE_NAMES,
)
from core.optimization.backend import (
    CPUBackend,
    CUDABackend,
    FutureEdgeBackend,
    PlatformInspector,
)


def test_calculate_percentiles():
    # Empty list
    empty = calculate_percentiles([])
    assert empty.samples == 0
    assert empty.p50 == 0.0

    # Single item
    single = calculate_percentiles([10.0])
    assert single.samples == 1
    assert single.p50 == 10.0
    assert single.p90 == 10.0
    assert single.p95 == 10.0
    assert single.p99 == 10.0
    assert single.mean == 10.0

    # Ordered list 1 to 100
    values = [float(i) for i in range(1, 101)]
    stats = calculate_percentiles(values)
    assert stats.samples == 100
    assert stats.min == 1.0
    assert stats.max == 100.0
    assert stats.p50 == 50.0
    assert stats.p90 == 90.0
    assert stats.p95 == 95.0
    assert stats.p99 == 99.0
    assert abs(stats.mean - 50.5) < 0.001
    assert stats.std_dev > 0.0

    d = stats.to_dict()
    assert "p50_ms" in d
    assert "p95_ms" in d
    assert d["samples"] == 100


def test_profiler_stage_timing():
    profiler = PipelineProfiler()
    profiler.start()

    # Time capture stage
    t0 = time.perf_counter()
    time.sleep(0.005)
    t1 = time.perf_counter()
    profiler.record_stage("capture", (t1 - t0) * 1000.0)
    profiler.record_frame_captured()

    # Time detection stage
    t2 = time.perf_counter()
    time.sleep(0.003)
    t3 = time.perf_counter()
    profiler.record_stage("detection", (t3 - t2) * 1000.0)

    # End to end measurement
    cap_time = time.perf_counter()
    time.sleep(0.002)
    decision_time = time.perf_counter()
    lat = profiler.record_e2e(cap_time, decision_time)
    assert lat >= 1.5

    # Queue metric
    profiler.record_queue_status("perception_queue", current_size=2, dropped=0)

    report = profiler.generate_report()
    assert "platform" in report
    assert "stages" in report
    assert "capture" in report["stages"]
    assert report["stages"]["capture"]["samples"] == 1
    assert report["stages"]["detection"]["samples"] == 1
    assert report["end_to_end_latency"]["samples"] == 1
    assert "queues" in report
    assert "perception_queue" in report["queues"]
    assert report["queues"]["perception_queue"]["max_observed_size"] == 2


def test_profiler_sample_resources():
    profiler = PipelineProfiler()
    profiler.start()
    res = profiler.sample_system_resources()
    assert "process_cpu_percent" in res
    assert "system_cpu_percent" in res
    assert "process_rss_mb" in res
    assert res["process_rss_mb"] > 0


def test_hardware_backends():
    cpu_b = CPUBackend()
    assert cpu_b.backend_type == "cpu"
    assert cpu_b.is_accelerated is False
    mem_info = cpu_b.memory_info()
    assert "process_rss_mb" in mem_info
    assert "system_total_ram_gb" in mem_info

    edge_b = FutureEdgeBackend(accelerator_name="NPU-K230", api_type="generic")
    assert edge_b.backend_type == "edge"
    assert edge_b.device_name == "NPU-K230 (generic)"
    assert edge_b.is_accelerated is True

    platform_info = PlatformInspector.get_telemetry()
    assert platform_info.cpu_model != ""
    assert platform_info.total_ram_gb > 0
    assert platform_info.os_name != ""
