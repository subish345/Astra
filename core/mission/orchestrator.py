"""Central Mission Orchestrator for ASTRA-EA.

Orchestrates the complete integrated product lifecycle:
- Startup, self-test verification, and clean shutdown
- Dependency injection across ServiceRegistry
- Global authoritative mission state management
- Run creation, config snapshots, and final report compilation
- Event bus coordination and failure containment
"""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.camera.interface import CameraSource, FrameData
from core.camera.webcam import WebcamSource
from core.common.config import AppConfig, load_config
from core.common.logging import get_logger
from core.common.version import VERSION, get_version_metadata
from core.evidence.store import UnifiedEvidenceStore
from core.health.aggregator import HealthStatus, UnifiedHealthAggregator
from core.mission.clock import MissionClock
from core.mission.database import DatabaseManager
from core.mission.event_bus import CorrelationContext, UnifiedEventBus
from core.mission.lifecycle import MissionLifecycleManager, MissionLifecycleState
from core.mission.recording import UnifiedRecordingManager
from core.mission.run_manager import MissionRunManager
from core.mission.services import ServiceRegistry
from core.mission.storage_manager import StorageManager
from core.models.learned_detector import LearnedObjectDetector
from core.optimization.backend import PlatformInspector
from core.optimization.profiles import DeploymentProfileManager
from core.optimization.scheduler import AdaptiveInferenceScheduler, SchedulerCadence
from core.perception.detection.color_adapter import ColorSpatialObjectDetector
from core.perception.hands.adapter import LightweightHandDetector
from core.perception.pose.adapter import LightweightPoseEstimator
from core.perception.factory import create_pose_and_hand_detectors
from core.perception.tracking.tracker import MultiObjectTracker
from core.procedure.evaluator import StepEvaluator
from core.procedure.matcher import ProcedureMatcher
from core.procedure.progress import ProcedureProgressManager
from core.activity.composite import CompositeActivityEngine
from core.activity.primitive import PrimitiveActivityEngine
from core.activity.temporal import TemporalBuffer
from core.activity.types import ActivityObservation, TemporalWindow
from core.procedure.registry import ExperimentRegistry
from core.procedure.schema import ExperimentProcedure
from core.assurance.engine import TriStateAssuranceEngine
from core.interaction.engine import SpatialInteractionEngine
from core.evidence.engine import MultimodalEvidenceEngine
from core.assistance.recovery import ClosedLoopRecoveryEngine
from core.voice.manager import AudioQueueManager

logger = get_logger("ORCHESTRATOR")


class MissionOrchestrator:
    """Master controller orchestrating all ASTRA-EA flight services."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        profile_name: str = "demo",
        root_dir: str = ".",
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.profile_name = profile_name
        self.config = config or load_config()

        # Core Infrastructure
        self.clock = MissionClock()
        self.lifecycle = MissionLifecycleManager()
        self.event_bus = UnifiedEventBus()
        self.health_aggregator = UnifiedHealthAggregator()
        self.storage_manager = StorageManager(root_dir=str(self.root_dir))
        self.run_manager = MissionRunManager(base_dir=str(self.root_dir / "data" / "runs"))
        self.evidence_store = UnifiedEvidenceStore(base_dir=str(self.root_dir / "data" / "evidence"))
        self.recording_manager = UnifiedRecordingManager(base_dir=str(self.root_dir / "data" / "recordings"))
        self.experiment_registry = ExperimentRegistry(search_dir=str(self.root_dir / "configs" / "experiments"))
        self.services = ServiceRegistry()

        # Database
        db_path = self.root_dir / "storage" / "database" / "astra.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseManager(db_path)
        self.db.initialize()

        # Hardware & Platform
        self.backend = PlatformInspector.create_backend()
        self.telemetry = PlatformInspector.get_telemetry()

        # Voice Manager
        self.voice_manager = AudioQueueManager()

        # Active Session State
        self.active_procedure: Optional[ExperimentProcedure] = None
        self.active_run_id: Optional[str] = None
        self._is_headless: bool = False
        self._stop_event = threading.Event()

        # Pipeline Engines
        self.detector = ColorSpatialObjectDetector()
        # Use the production MediaPipe 33-point pose/hand path when its model
        # asset is available, with an explicit degraded fallback otherwise.
        self.pose_estimator, self.hand_detector = create_pose_and_hand_detectors()
        self.tracker = MultiObjectTracker()
        self.interaction_engine = SpatialInteractionEngine()
        self.temporal_buffer = TemporalBuffer(window_seconds=2.0)
        self.primitive_engine = PrimitiveActivityEngine()
        self.composite_engine = CompositeActivityEngine()
        self.evidence_engine = MultimodalEvidenceEngine()
        self.step_evaluator = StepEvaluator()
        self.procedure_matcher = ProcedureMatcher()
        self.progress_manager: Optional[ProcedureProgressManager] = None
        self.assurance_engine = TriStateAssuranceEngine()
        self.recovery_engine = ClosedLoopRecoveryEngine()
        self.scheduler: Optional[AdaptiveInferenceScheduler] = None

        # Statistics & Audit Trail
        self._total_frames: int = 0
        self._verified_count: int = 0
        self._uncertain_count: int = 0
        self._deviation_count: int = 0
        self._recovery_count: int = 0
        self._timeline_records: List[Dict[str, Any]] = []

    def boot(self) -> bool:
        """Execute system boot sequence and advance lifecycle."""
        logger.info("ASTRA-EA Orchestrator booting (v%s)...", VERSION)
        self.lifecycle.transition_to(MissionLifecycleState.INITIALIZING, "System boot initiated")

        # Verify filesystem layout
        self.storage_manager.ensure_directories()
        self.experiment_registry.refresh()

        # Initialize profile settings
        prof = DeploymentProfileManager.load_profile(self.profile_name)
        sched_cfg = prof.get("scheduler", {})
        self.scheduler = AdaptiveInferenceScheduler(
            cadence=SchedulerCadence(
                tracking_interval=sched_cfg.get("tracking_interval", 1),
                detection_interval=sched_cfg.get("detection_interval", 1),
                pose_interval=sched_cfg.get("pose_interval", 1),
                hand_interval=sched_cfg.get("hand_interval", 1),
            )
        )

        self.lifecycle.transition_to(MissionLifecycleState.SELF_TEST, "Boot complete, starting self-test")
        return True

    def run_self_test(self, camera_source: Optional[str] = None) -> Dict[str, Any]:
        """Execute pre-flight hardware, model, and storage self-tests."""
        results: Dict[str, Any] = {}

        # 1. Storage & Database
        try:
            st_health = self.storage_manager.health_check()
            results["storage"] = "PASS" if st_health["status"] != "FAILED" else "FAIL"
            results["database"] = "PASS" if self.db.is_healthy() else "FAIL"
        except Exception as exc:
            results["storage"] = "FAIL"
            results["database"] = "FAIL"

        # 2. Experiment Registry
        experiments = self.experiment_registry.list_experiments()
        results["procedure"] = "PASS" if len(experiments) > 0 else "DEGRADED"

        # 3. Model & Inference Engine
        try:
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            fd = FrameData(frame_id=0, image=dummy, timestamp_mono=time.monotonic(), timestamp_wall=datetime.now(timezone.utc), source_id="TEST")
            self.detector.detect(fd)
            results["model"] = "PASS"
        except Exception:
            results["model"] = "FAIL"

        # 4. Camera source test
        cam_status = "PASS"
        if camera_source and camera_source.isdigit():
            try:
                cap = cv2.VideoCapture(int(camera_source))
                if cap.isOpened():
                    ret, _ = cap.read()
                    cam_status = "PASS" if ret else "DEGRADED"
                    cap.release()
                else:
                    cam_status = "DEGRADED"
            except Exception:
                cam_status = "DEGRADED"
        results["camera"] = cam_status

        # 5. Voice
        results["voice"] = "PASS" if self.voice_manager.is_enabled else "DEGRADED"

        # 6. Recording
        results["recording"] = "PASS"

        # Evaluate pass criteria
        critical_pass = (
            results.get("storage") == "PASS"
            and results.get("database") == "PASS"
            and results.get("model") == "PASS"
        )

        overall = "PASS" if critical_pass and results.get("procedure") == "PASS" else "DEGRADED" if critical_pass else "FAIL"

        if overall == "PASS":
            self.lifecycle.transition_to(MissionLifecycleState.READY, "Self-test passed")
        elif overall == "DEGRADED":
            self.lifecycle.transition_to(MissionLifecycleState.DEGRADED, "Self-test passed with non-critical warnings")
        else:
            self.lifecycle.transition_to(MissionLifecycleState.FAILED, "Critical self-test failure")

        results["overall_verdict"] = overall
        return results

    def start_mission(
        self,
        experiment_id: str = "DEMO_EXP_001",
        camera_source: str = "0",
        camera_profile: str = "view_left",
        session_id: Optional[str] = None,
        use_learned_model: bool = False,
        run_id: Optional[str] = None,
    ) -> bool:
        """Start mission execution for specified experiment."""
        logger.info("Starting mission: Exp=%s, Cam=%s, Profile=%s", experiment_id, camera_source, camera_profile)
        self.lifecycle.transition_to(MissionLifecycleState.STARTING, "Mission start initiated")

        # Load experiment procedure
        proc = self.experiment_registry.get_procedure(experiment_id)
        if not proc:
            logger.error("Experiment procedure not found: %s", experiment_id)
            self.lifecycle.transition_to(MissionLifecycleState.FAILED, f"Procedure not found: {experiment_id}")
            return False

        self.active_procedure = proc
        self.progress_manager = ProcedureProgressManager(procedure=proc)

        # Configure model selection (Baseline vs Learned)
        if use_learned_model:
            model_path = self.root_dir / "models" / "checkpoints" / "ASTRA_OBJECT_DETECTOR_v0.1.0.pt"
            if model_path.exists():
                try:
                    self.detector = LearnedObjectDetector(weights_path=str(model_path))
                    logger.info("Loaded LearnedObjectDetector (%s)", model_path)
                except Exception as exc:
                    logger.warning("Failed to load learned model (%s), falling back to baseline.", exc)
                    self.detector = ColorSpatialObjectDetector()
            else:
                self.detector = ColorSpatialObjectDetector()
        else:
            self.detector = ColorSpatialObjectDetector()

        # Create reproducible run directory
        run_id = run_id or session_id or f"RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.active_run_id = run_id
        config_snap = self.config.model_dump() if hasattr(self.config, "model_dump") else {}
        self.run_manager.create_run(
            experiment_id=proc.experiment.id,
            procedure_version=proc.experiment.version,
            config_snapshot=config_snap,
            camera_profile=camera_profile,
            run_id=run_id,
        )

        # Database Run Record
        self.db.record_experiment(
            experiment_id=proc.experiment.id,
            name=proc.experiment.name,
            version=proc.experiment.version,
            description=proc.experiment.description,
        )
        self.db.start_experiment_run(run_id=run_id, experiment_id=proc.experiment.id)

        # Start Video Recording
        self.recording_manager.start_recording(run_id=run_id, fps=30, resolution=(640, 480))

        # Start Mission Clock & Lifecycle
        self.clock.start()
        self._total_frames = 0
        self._verified_count = 0
        self._uncertain_count = 0
        self._deviation_count = 0
        self._recovery_count = 0
        self._timeline_records.clear()

        # Publish MissionStarted event
        context = CorrelationContext(mission_id="ASTRA_MISSION", run_id=run_id, experiment_id=proc.experiment.id)
        self.event_bus.publish("MissionStarted", context, {"profile": self.profile_name, "start_time": self.clock.utc_now().isoformat()})

        self.lifecycle.transition_to(MissionLifecycleState.RUNNING, "Mission actively running")
        return True

    def process_frame(self, frame: FrameData) -> Dict[str, Any]:
        """Execute single pipeline step through all integrated services."""
        if not self.lifecycle.is_active():
            return {"status": "PAUSED_OR_STOPPED"}

        self._total_frames += 1
        frame_idx = frame.frame_id
        capture_ts = frame.timestamp_mono

        # Record to video file
        self.recording_manager.record_frame(frame.image)

        # 1. Detection (Scheduled)
        if self.scheduler is None or self.scheduler.should_run_detection(frame_idx):
            detections = self.detector.detect(frame)
            if self.scheduler:
                self.scheduler.update_detections(detections)
        else:
            detections = self.scheduler.get_detections()

        # 2. Pose (Scheduled)
        if self.scheduler is None or self.scheduler.should_run_pose(frame_idx):
            poses = self.pose_estimator.estimate(frame)
            pose = poses[0] if poses else None
            if self.scheduler:
                self.scheduler.update_pose(pose)
        else:
            pose = self.scheduler.get_pose()

        # 3. Hands (Scheduled)
        if self.scheduler is None or self.scheduler.should_run_hands(frame_idx):
            hands = self.hand_detector.detect(frame)
            if self.scheduler:
                self.scheduler.update_hands(hands)
        else:
            hands = self.scheduler.get_hands()

        if self.scheduler:
            self.scheduler.step()

        # 4. Tracking (Runs every frame)
        tracked_objects = self.tracker.update(detections, frame_idx)

        # 5. Interaction
        now_ts = time.time()
        interactions = self.interaction_engine.process(
            tracks=tracked_objects,
            hands=hands,
            timestamp=now_ts,
        )

        # 6. Activity Classification
        positions = {t.track_id: t.center for t in tracked_objects}
        self.temporal_buffer.append(now_ts, interactions, positions)

        primitives = []
        composites = []
        for int_ev in interactions:
            prim_obs = self.primitive_engine.evaluate(int_ev, self.temporal_buffer)
            primitives.append(prim_obs)
            comp_obs = self.composite_engine.update(prim_obs)
            if comp_obs:
                composites.append(comp_obs)

        curr_act = composites[0] if composites else (primitives[0] if primitives else None)

        # 7. Procedure State & Step Definition
        curr_step_id = self.progress_manager.current_step if self.progress_manager else "STEP_01"
        proc = self.active_procedure
        step_def = proc.get_step(curr_step_id) if (proc and curr_step_id) else None

        if curr_act is None:
            curr_act = ActivityObservation(
                activity_name="IDLE",
                actor="ASTRONAUT",
                target_object_id=step_def.expected_objects[0] if (step_def and step_def.expected_objects) else "NONE",
                confidence=0.5,
                window=TemporalWindow(start_time=now_ts - 0.1, end_time=now_ts),
            )

        # 8. Evidence Engine
        evidence_bundle = self.evidence_engine.evaluate(
            activity=curr_act,
            interactions=interactions,
            tracks=tracked_objects,
            perception_state=None,
            temporal_buffer=self.temporal_buffer,
            step=step_def,
        )

        # 9. Assurance Decision
        completed_ids = set(self.progress_manager.completed_steps) if self.progress_manager else set()
        decision = self.assurance_engine.evaluate_step(
            current_step=step_def,
            activity=curr_act,
            evidence=evidence_bundle,
            camera_profile=self.profile_name,
            session_id=self.active_run_id,
            procedure=proc,
            completed_step_ids=completed_ids,
        )

        # 10. Correlation context for traceability
        context = CorrelationContext(
            mission_id="ASTRA_MISSION",
            run_id=self.active_run_id or "RUN_UNKNOWN",
            experiment_id=proc.experiment.id if proc else "EXP_UNKNOWN",
            step_id=curr_step_id,
        )

        # 10. Handle Decision Outcomes
        dec_val = decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision)
        if dec_val == "VERIFIED":
            self._verified_count += 1
            if self.progress_manager:
                self.progress_manager.advance(curr_step_id)
            self.event_bus.publish("StepVerified", context, {"step": curr_step_id, "confidence": decision.confidence})
            self._record_timeline("STEP_VERIFIED", f"Step {curr_step_id} verified", "SUCCESS")

        elif dec_val == "DEVIATION":
            self._deviation_count += 1
            rec_action = self.recovery_engine.generate_recovery(decision, step_def)
            self.lifecycle.transition_to(MissionLifecycleState.RECOVERY, f"Deviation on {curr_step_id}")
            self.event_bus.publish("DeviationDetected", context, {"step": curr_step_id, "reasons": decision.reasons, "recovery": rec_action.to_dict() if rec_action else None}, severity="WARNING")
            self._record_timeline("DEVIATION", f"Deviation on {curr_step_id}: {'; '.join(decision.reasons)}", "DANGER")

        elif dec_val == "UNCERTAIN":
            self._uncertain_count += 1
            self.event_bus.publish("StepUncertain", context, {"step": curr_step_id, "reasons": decision.reasons})

        # Save snapshot on verified or deviation
        if dec_val in ("VERIFIED", "DEVIATION"):
            evidence_id = f"EVD_{self._total_frames:06d}_{dec_val}"
            self.evidence_store.save_snapshot(evidence_id, frame.image, run_id=self.active_run_id)
            self.evidence_store.save_evidence_bundle(evidence_id, evidence_bundle, run_id=self.active_run_id, step_id=curr_step_id)

        # Check for experiment completion
        if self.progress_manager and self.progress_manager.is_completed():
            self.complete_mission()

        return {
            "frame_id": frame_idx,
            "decision": dec_val,
            "step_id": curr_step_id,
            "confidence": decision.confidence,
            "met": self.clock.format_met(),
            "detections_count": len(detections),
            "interactions_count": len(interactions),
        }

    def handle_camera_failure(self, reason: str = "Camera frame drop / disconnect") -> None:
        """Handle optical sensor failure, pause procedure advancement, and publish alert."""
        logger.warning("Camera failure detected: %s", reason)
        self.health_aggregator.update_component("camera", HealthStatus.FAILED, message=reason)
        if self.lifecycle.state == MissionLifecycleState.RUNNING:
            self.lifecycle.transition_to(MissionLifecycleState.PAUSED, f"Camera failure: {reason}")
        context = CorrelationContext(
            mission_id="ASTRA_MISSION",
            run_id=self.active_run_id or "RUN_UNKNOWN",
            experiment_id=self.active_procedure.id if self.active_procedure else "EXP_UNKNOWN",
        )
        self.event_bus.publish("CameraFailure", context, {"reason": reason}, severity="CRITICAL")

    def handle_camera_recovery(self) -> None:
        """Handle optical sensor recovery and resume mission."""
        logger.info("Camera recovery detected.")
        self.health_aggregator.update_component("camera", HealthStatus.NORMAL, message="Sensor recovered")
        if self.lifecycle.state == MissionLifecycleState.PAUSED:
            self.lifecycle.transition_to(MissionLifecycleState.RUNNING, "Camera sensor restored")
        context = CorrelationContext(
            mission_id="ASTRA_MISSION",
            run_id=self.active_run_id or "RUN_UNKNOWN",
            experiment_id=self.active_procedure.id if self.active_procedure else "EXP_UNKNOWN",
        )
        self.event_bus.publish("CameraRecovered", context, {"status": "RECOVERED"}, severity="INFO")


    def _record_timeline(self, event_type: str, message: str, level: str = "INFO") -> None:
        """Record entry in chronological timeline."""
        self._timeline_records.append({
            "timestamp": self.clock.utc_now().isoformat(),
            "met": self.clock.format_met(),
            "event_type": event_type,
            "message": message,
            "level": level,
        })

    def complete_mission(self) -> Dict[str, Any]:
        """Finalize and close completed mission run."""
        logger.info("Completing mission run %s...", self.active_run_id)
        self.lifecycle.transition_to(MissionLifecycleState.COMPLETING, "Finalizing experiment")

        # Stop recording
        self.recording_manager.stop_recording()

        # Compile final report
        total_steps = len(self.active_procedure.steps) if self.active_procedure else 0
        completed_steps = len(self.progress_manager.completed_steps) if self.progress_manager else 0
        events_snapshot = [e.to_dict() for e in self.event_bus.get_recent_events(limit=500)]
        health_snap = self.health_aggregator.evaluate_system_health()

        elapsed = self.clock.elapsed_seconds()
        mean_fps = (self._total_frames / elapsed) if elapsed > 0 else 0.0

        report = self.run_manager.finalize_run(
            status="COMPLETED",
            total_steps=total_steps,
            completed_steps=completed_steps,
            deviations_count=self._deviation_count,
            recoveries_count=self._recovery_count,
            uncertain_count=self._uncertain_count,
            events=events_snapshot,
            timeline=self._timeline_records,
            health_summary=health_snap,
            metrics={"effective_fps": round(mean_fps, 2), "total_frames": self._total_frames},
        )

        # Database update
        if self.active_run_id:
            self.db.end_experiment_run(run_id=self.active_run_id, status="COMPLETED")

        self.lifecycle.transition_to(MissionLifecycleState.COMPLETED, "Experiment completed successfully")
        return report

    def abort_mission(self, reason: str = "Operator abort") -> Dict[str, Any]:
        """Abort mission execution while preserving all audit records."""
        logger.warning("Aborting mission run %s: %s", self.active_run_id, reason)
        self.lifecycle.transition_to(MissionLifecycleState.ABORTING, reason)
        self.recording_manager.stop_recording()

        total_steps = len(self.active_procedure.steps) if self.active_procedure else 0
        completed_steps = len(self.progress_manager.completed_steps) if self.progress_manager else 0

        report = self.run_manager.finalize_run(
            status="ABORTED",
            total_steps=total_steps,
            completed_steps=completed_steps,
            deviations_count=self._deviation_count,
            recoveries_count=self._recovery_count,
            uncertain_count=self._uncertain_count,
            events=[e.to_dict() for e in self.event_bus.get_recent_events(limit=500)],
            timeline=self._timeline_records,
            health_summary=self.health_aggregator.evaluate_system_health(),
            metrics={"abort_reason": reason, "total_frames": self._total_frames},
        )

        if self.active_run_id:
            self.db.end_experiment_run(run_id=self.active_run_id, status="ABORTED")

        self.lifecycle.transition_to(MissionLifecycleState.ABORTED, reason)
        return report

    def shutdown(self) -> None:
        """Perform orderly, clean shutdown of all hardware and background threads."""
        logger.info("Shutting down ASTRA-EA Mission Orchestrator...")
        self.lifecycle.transition_to(MissionLifecycleState.SHUTTING_DOWN, "Clean shutdown initiated")

        # Stop active run if running
        if self.lifecycle.is_active():
            self.abort_mission("Process shutdown")

        # Stop recording
        self.recording_manager.stop_recording()

        # Stop services
        self.services.stop_all()

        # Release database
        self.db.close()

        self.lifecycle.transition_to(MissionLifecycleState.STOPPED, "Shutdown complete")
        logger.info("ASTRA-EA Mission Orchestrator stopped.")
