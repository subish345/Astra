# ==============================================================================
# ASTRA-EA Streaming Impact & Security Profiler
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Measures onboard AI performance delta (AI-only vs AI+Streaming) and validates security."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict
import numpy as np

from core.common.config import load_config
from core.simulation.engine import SimulationEngine
from core.simulation.scenario import SimulationScenario
from streaming.security.access import is_safe_bind_address, sanitize_evidence_id
from streaming.security.rate_limit import ConnectionRateLimiter
from streaming.video.config import StreamQuality, VideoStreamConfig
from streaming.video.encoder import StreamEncoder


def run_stream_impact_benchmark(iterations: int = 40) -> Dict[str, Any]:
    """Empirically measure pipeline performance with and without streaming."""
    reports_dir = Path("storage/reports/streaming")
    reports_dir.mkdir(parents=True, exist_ok=True)

    scenario = SimulationScenario.load_yaml("configs/simulations/nominal_mission.yaml")
    engine = SimulationEngine("configs/system.yaml")

    # 1. Baseline: AI only (no streaming)
    t0 = time.perf_counter()
    res_baseline = engine.run_scenario(scenario, max_frames=iterations, realtime_pacing=False, stream=False)
    baseline_duration = time.perf_counter() - t0
    baseline_fps = iterations / baseline_duration if baseline_duration > 0 else 0.0

    # 2. AI + Video Stream + Event Telemetry
    t1 = time.perf_counter()
    res_streaming = engine.run_scenario(scenario, max_frames=iterations, realtime_pacing=False, stream=True)
    streaming_duration = time.perf_counter() - t1
    streaming_fps = iterations / streaming_duration if streaming_duration > 0 else 0.0

    # 3. Quality Mode Benchmarks
    test_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    quality_benchmarks = {}
    for q_mode in (StreamQuality.LOW, StreamQuality.MEDIUM, StreamQuality.HIGH):
        cfg = VideoStreamConfig(quality=q_mode)
        cfg.apply_quality_preset(q_mode)
        enc = StreamEncoder(cfg)

        latencies = []
        sizes = []
        for _ in range(15):
            t_enc = time.perf_counter()
            data = enc.encode(test_frame)
            lat = (time.perf_counter() - t_enc) * 1000.0
            if data:
                latencies.append(lat)
                sizes.append(len(data))

        quality_benchmarks[q_mode.value] = {
            "resolution": f"{cfg.width}x{cfg.height}",
            "target_fps": cfg.fps,
            "jpeg_quality": cfg.jpeg_quality,
            "avg_encode_ms": round(float(np.mean(latencies)), 2) if latencies else 0.0,
            "p95_encode_ms": round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0,
            "avg_frame_kb": round(float(np.mean(sizes)) / 1024.0, 1) if sizes else 0.0,
        }

    # Overhead computation
    fps_delta = baseline_fps - streaming_fps
    overhead_pct = round((fps_delta / baseline_fps * 100.0) if baseline_fps > 0 else 0.0, 1)

    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "iterations": iterations,
        "baseline_ai_only": {
            "fps": round(baseline_fps, 1),
            "total_duration_sec": round(baseline_duration, 3),
            "crashes": res_baseline.unhandled_crashes,
        },
        "ai_plus_streaming": {
            "fps": round(streaming_fps, 1),
            "total_duration_sec": round(streaming_duration, 3),
            "crashes": res_streaming.unhandled_crashes,
        },
        "impact_summary": {
            "throughput_overhead_pct": max(0.0, overhead_pct),
            "non_blocking_verified": res_streaming.unhandled_crashes == 0,
            "meets_spacecraft_budget": overhead_pct < 15.0,
        },
        "quality_modes": quality_benchmarks,
    }

    report_path = reports_dir / "stream_impact_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    return report_data


def run_security_audit() -> Dict[str, Any]:
    """Execute automated security policy checks for local network streaming."""
    reports_dir = Path("storage/reports/streaming")
    reports_dir.mkdir(parents=True, exist_ok=True)

    checks = []

    # 1. Path traversal sanitization
    malicious_inputs = [
        ("../../etc/passwd", False),
        ("..\\..\\windows\\system32", False),
        ("EVT_00124/../../secret", False),
        ("EVT_00124", True),
        ("EVT_00124.json", True),
        ("VALID_STEP_AUDIT_01", True),
    ]
    path_traversal_passed = True
    for inp, should_pass in malicious_inputs:
        res = sanitize_evidence_id(inp)
        passed = (res is not None) == should_pass
        if not passed:
            path_traversal_passed = False
        checks.append({
            "test": "path_traversal_sanitization",
            "input": inp,
            "sanitized_output": res,
            "passed": passed,
        })

    # 2. Air-gap bind address validation
    bind_inputs = [
        ("127.0.0.1", True),
        ("localhost", True),
        ("192.168.1.50", True),  # Private LAN allowed
        ("10.0.0.5", True),       # Private LAN allowed
        ("8.8.8.8", False),       # Public IP rejected
        ("1.1.1.1", False),       # Public IP rejected
    ]
    bind_policy_passed = True
    for host, should_pass in bind_inputs:
        allowed = is_safe_bind_address(host, allow_lan=True)
        passed = allowed == should_pass
        if not passed:
            bind_policy_passed = False
        checks.append({
            "test": "bind_address_policy",
            "host": host,
            "allowed": allowed,
            "passed": passed,
        })

    # 3. Connection Rate Limiter
    limiter = ConnectionRateLimiter(max_requests_per_window=5, window_seconds=1.0)
    client_ip = "127.0.0.1"
    rate_results = [limiter.is_allowed(client_ip) for _ in range(7)]
    rate_limit_passed = (rate_results[:5] == [True] * 5) and (rate_results[5:] == [False, False])
    checks.append({
        "test": "rate_limiter_flood_prevention",
        "requests_evaluated": 7,
        "expected_first_5_pass_last_2_block": rate_limit_passed,
        "passed": rate_limit_passed,
    })

    overall_passed = path_traversal_passed and bind_policy_passed and rate_limit_passed

    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_status": "PASS" if overall_passed else "FAIL",
        "path_traversal_protection": "VERIFIED" if path_traversal_passed else "FAILED",
        "air_gap_bind_policy": "VERIFIED" if bind_policy_passed else "FAILED",
        "rate_limiting_defense": "VERIFIED" if rate_limit_passed else "FAILED",
        "checks": checks,
    }

    report_path = reports_dir / "security_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    return report_data


if __name__ == "__main__":
    print("Running Streaming Impact Benchmark...")
    imp = run_stream_impact_benchmark(iterations=30)
    print(f"Impact Result: Baseline FPS={imp['baseline_ai_only']['fps']}, Stream FPS={imp['ai_plus_streaming']['fps']}, Overhead={imp['impact_summary']['throughput_overhead_pct']}%")

    print("\nRunning Security Audit...")
    sec = run_security_audit()
    print(f"Security Audit Result: {sec['overall_status']}")
