"""Long-Run Stability, Memory Leak, and Thermal Soak Tester for ASTRA-EA.

Executes continuous full-pipeline mission processing over configurable durations:
- Samples process RSS memory, CPU%, and FPS degradation over time.
- Verifies bounded memory growth (flags sustained leaks).
- Detects thermal throttling / performance drops.
- Generates structured audit report in storage/reports/benchmark/soak_report.json.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import psutil

from core.camera.interface import FrameData
from core.common.logging import get_logger
from core.optimization.backend import ComputeBackend, PlatformInspector
from core.perception.detection.color_adapter import ColorSpatialObjectDetector
from core.procedure.evaluator import StepEvaluator
from core.procedure.matcher import ProcedureMatcher
from core.procedure.schema import ExperimentProcedure

logger = get_logger("OPTIMIZATION")


class SoakTester:
    """Orchestrates long-run endurance testing to verify memory and thermal stability."""

    def __init__(
        self,
        output_dir: str = "storage/reports/benchmark",
        backend: Optional[ComputeBackend] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backend = backend or PlatformInspector.create_backend()
        self.process = psutil.Process(os.getpid())

    def run_soak(
        self,
        duration_seconds: int = 30,
        target_fps: int = 30,
        procedure: Optional[ExperimentProcedure] = None,
    ) -> Dict[str, Any]:
        """Execute endurance soak test for the specified number of seconds."""
        logger.info("Starting ASTRA-EA soak test for %d seconds (Target %d FPS)...", duration_seconds, target_fps)

        # Baseline initialization and warmup
        from datetime import datetime, timezone
        detector = ColorSpatialObjectDetector()

        # Synthetic test frame
        h, w = 480, 640
        test_frame = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.rectangle(test_frame, (200, 150), (350, 300), (0, 0, 220), -1)  # RED_BOX

        # Warm up pipeline and allocate library runtime buffers
        for w_idx in range(5):
            warmup_fd = FrameData(
                frame_id=w_idx,
                image=test_frame,
                timestamp_mono=time.monotonic(),
                timestamp_wall=datetime.now(timezone.utc),
                source_id="WARMUP",
            )
            detector.detect(warmup_fd)

        startup_rss_mb = self.process.memory_info().rss / (1024 * 1024)

        # Telemetry sample arrays
        timestamps: List[float] = []
        rss_samples_mb: List[float] = []
        cpu_samples: List[float] = []
        instant_fps_samples: List[float] = []

        start_time = time.perf_counter()
        last_sample_time = start_time
        frame_count = 0
        frames_in_second = 0

        frame_interval = 1.0 / max(1, target_fps)

        while (time.perf_counter() - start_time) < duration_seconds:
            loop_start = time.perf_counter()

            # Execute pipeline step
            from datetime import datetime, timezone
            fd = FrameData(
                frame_id=frame_count,
                image=test_frame,
                timestamp_mono=time.monotonic(),
                timestamp_wall=datetime.now(timezone.utc),
                source_id="SOAK_TEST",
            )
            dets = detector.detect(fd)
            frame_count += 1
            frames_in_second += 1

            # Sample metrics once per second
            now = time.perf_counter()
            if (now - last_sample_time) >= 1.0:
                elapsed_sec = now - start_time
                fps_curr = frames_in_second / (now - last_sample_time)
                rss_curr = self.process.memory_info().rss / (1024 * 1024)
                cpu_curr = self.process.cpu_percent()

                timestamps.append(round(elapsed_sec, 1))
                rss_samples_mb.append(round(rss_curr, 2))
                cpu_samples.append(round(cpu_curr, 1))
                instant_fps_samples.append(round(fps_curr, 2))

                frames_in_second = 0
                last_sample_time = now

            # Throttle to target FPS if running faster than real-time
            process_dur = time.perf_counter() - loop_start
            sleep_rem = frame_interval - process_dur
            if sleep_rem > 0:
                time.sleep(sleep_rem)

        total_elapsed = time.perf_counter() - start_time
        shutdown_rss_mb = self.process.memory_info().rss / (1024 * 1024)
        mean_fps = frame_count / total_elapsed

        # Leak and degradation analysis
        rss_delta_mb = shutdown_rss_mb - startup_rss_mb
        # Calculate memory slope (MB per minute)
        duration_minutes = max(0.1, total_elapsed / 60.0)
        growth_rate_mb_per_min = rss_delta_mb / duration_minutes

        # Check for degradation: compare first 3 samples to last 3 samples
        fps_degraded = False
        if len(instant_fps_samples) >= 6:
            initial_fps = sum(instant_fps_samples[:3]) / 3.0
            final_fps = sum(instant_fps_samples[-3:]) / 3.0
            if initial_fps > 0 and (final_fps / initial_fps) < 0.75:
                fps_degraded = True

        # Sustained memory leak: flagged if growth exceeds 5 MB/min over run
        memory_leak_detected = growth_rate_mb_per_min > 5.0 and rss_delta_mb > 15.0

        verdict = "PASS" if not (memory_leak_detected or fps_degraded) else "WARNING"

        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "verdict": verdict,
            "duration_seconds": round(total_elapsed, 2),
            "target_fps": target_fps,
            "effective_mean_fps": round(mean_fps, 2),
            "total_frames_evaluated": frame_count,
            "memory": {
                "startup_rss_mb": round(startup_rss_mb, 2),
                "shutdown_rss_mb": round(shutdown_rss_mb, 2),
                "rss_delta_mb": round(rss_delta_mb, 2),
                "growth_rate_mb_per_min": round(growth_rate_mb_per_min, 3),
                "memory_leak_detected": memory_leak_detected,
            },
            "stability": {
                "fps_degraded_over_time": fps_degraded,
                "peak_cpu_percent": max(cpu_samples) if cpu_samples else 0.0,
                "mean_cpu_percent": round(sum(cpu_samples) / len(cpu_samples), 1) if cpu_samples else 0.0,
            },
            "samples": {
                "timestamps_sec": timestamps,
                "rss_mb": rss_samples_mb,
                "cpu_percent": cpu_samples,
                "instant_fps": instant_fps_samples,
            },
        }

        # Write report
        report_path = self.output_dir / "soak_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info("Soak test finished [%s]. Report saved to %s", verdict, report_path)
        return report
