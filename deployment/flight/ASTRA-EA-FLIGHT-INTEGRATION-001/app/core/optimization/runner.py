"""Unified Benchmark Runner for ASTRA-EA.

Orchestrates full end-to-end pipeline benchmarking, per-stage latency profiling,
and system resource monitoring across camera, perception, interaction, activity,
procedure, and assurance engines.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from core.camera.interface import CameraSource, FrameData
from core.camera.webcam import WebcamSource
from core.common.logging import get_logger
from core.evidence.engine import MultimodalEvidenceEngine
from core.interaction.engine import SpatialInteractionEngine
from core.optimization.backend import ComputeBackend, PlatformInspector
from core.optimization.profiler import PipelineProfiler
from core.perception.detection.color_adapter import ColorSpatialObjectDetector
from core.perception.hands.adapter import LightweightHandDetector
from core.perception.pose.adapter import LightweightPoseEstimator
from core.perception.tracking.tracker import MultiObjectTracker
from core.procedure.evaluator import StepEvaluator
from core.procedure.matcher import ProcedureMatcher
from core.procedure.progress import ProcedureProgressManager
from core.procedure.schema import ExperimentProcedure
from core.assurance.engine import TriStateAssuranceEngine

logger = get_logger("OPTIMIZATION")


class BenchmarkRunner:
    """Coordinates pipeline execution and collects comprehensive benchmarks."""

    def __init__(
        self,
        output_dir: str = "storage/reports/benchmark",
        backend: Optional[ComputeBackend] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backend = backend or PlatformInspector.create_backend()

    def run_benchmark(
        self,
        frames: int = 60,
        source: Optional[str] = None,
        is_baseline: bool = False,
        profile_name: str = "balanced",
        procedure_path: str = "configs/experiments/demo.yaml",
    ) -> Dict[str, Any]:
        """Execute end-to-end pipeline benchmark across specified number of frames."""
        mode_label = "BASELINE (Unoptimized)" if is_baseline else f"OPTIMIZED ({profile_name})"
        logger.info(
            "Starting ASTRA-EA %s benchmark for %d frames...",
            mode_label,
            frames,
        )

        profiler = PipelineProfiler(backend=self.backend)

        # Scheduler and profile configuration
        from core.optimization.profiles import DeploymentProfileManager
        from core.optimization.scheduler import AdaptiveInferenceScheduler, SchedulerCadence

        scheduler: Optional[AdaptiveInferenceScheduler] = None
        if not is_baseline:
            profile_cfg = DeploymentProfileManager.load_profile(profile_name)
            sched_cfg = profile_cfg.get("scheduler", {})
            cadence = SchedulerCadence(
                tracking_interval=sched_cfg.get("tracking_interval", 1),
                detection_interval=sched_cfg.get("detection_interval", 1),
                pose_interval=sched_cfg.get("pose_interval", 1),
                hand_interval=sched_cfg.get("hand_interval", 1),
                max_cache_age_frames=sched_cfg.get("max_cache_age_frames", 5),
            )
            scheduler = AdaptiveInferenceScheduler(cadence=cadence)

        # 1. Initialize pipeline components
        detector = ColorSpatialObjectDetector()
        pose_estimator = LightweightPoseEstimator()
        hand_detector = LightweightHandDetector()
        tracker = MultiObjectTracker()
        interaction_engine = SpatialInteractionEngine()
        evidence_engine = MultimodalEvidenceEngine()

        # Load experiment procedure
        import yaml
        with open(procedure_path, "r") as f:
            proc_dict = yaml.safe_load(f)
        procedure = ExperimentProcedure(**proc_dict)
        matcher = ProcedureMatcher()
        evaluator = StepEvaluator()
        progress = ProcedureProgressManager(procedure=procedure)
        assurance_engine = TriStateAssuranceEngine()

        # 2. Camera or Synthetic Source Setup
        cam_source: Optional[CameraSource] = None
        if source is not None and source.isdigit():
            try:
                cam_source = WebcamSource(device_id=int(source), width=640, height=480, fps=30)
                cam_source.start()
            except Exception as e:
                logger.warning("Failed to open hardware camera (%s). Using synthetic benchmark frames.", e)
                cam_source = None

        profiler.start()

        # Synthetic frame fallback
        h, w = 480, 640
        dummy_img = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.rectangle(dummy_img, (200, 150), (350, 300), (0, 0, 220), -1)  # RED_BOX
        cv2.rectangle(dummy_img, (100, 350), (540, 450), (120, 120, 120), -1)  # WORK_SURFACE

        for frame_idx in range(frames):
            capture_start = time.perf_counter()

            if cam_source is not None:
                frame = cam_source.read_frame()
                if frame is None:
                    # End of stream or capture failure
                    frame = FrameData(
                        frame_id=frame_idx,
                        image=dummy_img,
                        timestamp_mono=time.monotonic(),
                        timestamp_wall=datetime.now(timezone.utc),
                        source_id="BENCHMARK_SYNTH",
                    )
            else:
                frame = FrameData(
                    frame_id=frame_idx,
                    image=dummy_img,
                    timestamp_mono=time.monotonic(),
                    timestamp_wall=datetime.now(timezone.utc),
                    source_id="BENCHMARK_SYNTH",
                )

            capture_dur = (time.perf_counter() - capture_start) * 1000.0
            profiler.record_stage("capture", capture_dur)
            profiler.record_frame_captured()

            # Record timestamp for exact end-to-end latency
            e2e_start_ts = capture_start

            # Stage: Detection
            if scheduler is None or scheduler.should_run_detection(frame_idx):
                t0 = time.perf_counter()
                detections = detector.detect(frame)
                profiler.record_stage("detection", (time.perf_counter() - t0) * 1000.0)
                if scheduler is not None:
                    scheduler.update_detections(detections)
            else:
                detections = scheduler.get_detections()
                profiler.record_stage("detection", 0.0)

            # Stage: Pose
            if scheduler is None or scheduler.should_run_pose(frame_idx):
                t0 = time.perf_counter()
                poses = pose_estimator.estimate(frame)
                pose = poses[0] if poses else None
                profiler.record_stage("pose", (time.perf_counter() - t0) * 1000.0)
                if scheduler is not None:
                    scheduler.update_pose(pose)
            else:
                pose = scheduler.get_pose()
                profiler.record_stage("pose", 0.0)

            # Stage: Hands
            if scheduler is None or scheduler.should_run_hands(frame_idx):
                t0 = time.perf_counter()
                hands = hand_detector.detect(frame)
                profiler.record_stage("hands", (time.perf_counter() - t0) * 1000.0)
                if scheduler is not None:
                    scheduler.update_hands(hands)
            else:
                hands = scheduler.get_hands()
                profiler.record_stage("hands", 0.0)

            # Advance scheduler step
            if scheduler is not None:
                scheduler.step()

            # Stage: Tracking (runs every frame)
            t0 = time.perf_counter()
            tracked_objects = tracker.update(detections, frame_idx)
            profiler.record_stage("tracking", (time.perf_counter() - t0) * 1000.0)

            # Stage: Interaction
            t0 = time.perf_counter()
            interactions = interaction_engine.process(
                tracks=tracked_objects,
                hands=hands,
                timestamp=time.time(),
            )
            profiler.record_stage("interaction", (time.perf_counter() - t0) * 1000.0)

            # Stage: Activity
            t0 = time.perf_counter()
            from core.activity.types import ActivityObservation, TemporalWindow
            current_step_id = progress.current_step or "STEP_01"
            obs = ActivityObservation(
                activity_name="APPROACH",
                actor="ASTRONAUT",
                target_object_id="MAIN_BOX",
                confidence=0.90,
                window=TemporalWindow(start_time=time.time() - 1.0, end_time=time.time()),
            )
            profiler.record_stage("activity", (time.perf_counter() - t0) * 1000.0)

            # Stage: Evidence
            t0 = time.perf_counter()
            evidence_bundle = evidence_engine.evaluate(
                activity=obs,
                interactions=interactions,
                tracks=tracked_objects,
                step=procedure.steps[0] if procedure.steps else None,
            )
            profiler.record_stage("evidence", (time.perf_counter() - t0) * 1000.0)

            # Stage: Procedure
            t0 = time.perf_counter()
            candidates = matcher.match(obs, procedure, current_step_id=current_step_id)
            cand = candidates[0] if candidates else None
            step_def = next((s for s in procedure.steps if s.id == cand.step_id), procedure.steps[0] if procedure.steps else None) if cand else (procedure.steps[0] if procedure.steps else None)
            if cand and step_def:
                step_eval = evaluator.evaluate_step(cand, evidence_bundle, step_def)
            profiler.record_stage("procedure", (time.perf_counter() - t0) * 1000.0)

            # Stage: Assurance
            t0 = time.perf_counter()
            if step_def:
                assurance_decision = assurance_engine.evaluate_step(
                    current_step=step_def,
                    activity=obs,
                    evidence=evidence_bundle,
                    session_id="BENCHMARK_SESSION",
                    procedure=procedure,
                )
            assurance_dur = (time.perf_counter() - t0) * 1000.0
            profiler.record_stage("assurance", assurance_dur)

            # Complete end-to-end measurement
            decision_ts = time.perf_counter()
            # If capture timestamp was wall-clock time, normalize to perf_counter
            profiler.record_e2e(capture_start, decision_ts)

            # Stage: UI Publish & Stream (non-blocking mock / queue sample)
            t0 = time.perf_counter()
            profiler.record_stage("ui_publish", (time.perf_counter() - t0) * 1000.0)

            t0 = time.perf_counter()
            profiler.record_stage("stream", (time.perf_counter() - t0) * 1000.0)

            t0 = time.perf_counter()
            profiler.record_stage("recording", (time.perf_counter() - t0) * 1000.0)

            # Sample resources every 10 frames
            if (frame_idx % 10) == 0:
                profiler.sample_system_resources()

        if cam_source is not None:
            cam_source.stop()

        # Compile and persist report
        report = profiler.generate_report()
        report["benchmark_mode"] = "BASELINE" if is_baseline else "OPTIMIZED"

        filename = "baseline_benchmark.json" if is_baseline else "benchmark_report.json"
        out_path = self.output_dir / filename
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info("Benchmark complete. Report saved to %s", out_path)
        profiler.print_ascii_summary(report)
        return report
