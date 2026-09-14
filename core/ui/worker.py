# ==============================================================================
# ASTRA-EA Mission Pipeline Background Worker
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Background QThread worker executing the complete ASTRA-EA assurance pipeline.

Decouples perception, activity, evidence, procedure, assurance, and recovery
execution completely from the Qt GUI main thread.
"""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np
import psutil
from PySide6.QtCore import QThread

from core.activity.composite import CompositeActivityEngine
from core.activity.events import ActivityEventBus, ActivityEventDeduplicator
from core.activity.primitive import PrimitiveActivityEngine
from core.activity.temporal import TemporalBuffer
from core.assistance.recovery import ClosedLoopRecoveryManager
from core.assurance.engine import TriStateAssuranceEngine
from core.assurance.types import AssuranceDecision, DecisionType
from core.camera.file_source import VideoFileSource
from core.camera.ingestion import FramePacket
from core.camera.profile import get_camera_profile
from core.camera.webcam import WebcamSource
from core.common.config import get_project_root, load_config
from core.common.logging import get_logger
from core.evidence.engine import MultimodalEvidenceEngine
from core.interaction.engine import SpatialInteractionEngine
from core.mission.database import DatabaseManager
from core.perception.detection.color_adapter import ColorSpatialObjectDetector
from core.perception.events import PerceptionEventBus
from core.perception.hands.adapter import LightweightHandDetector
from core.perception.pipeline import PerceptionPipeline
from core.perception.factory import create_pose_and_hand_detectors
from core.perception.pose.adapter import LightweightPoseEstimator
from core.perception.scheduler import PerceptionScheduler, SchedulerConfig
from core.perception.tracking.tracker import MultiObjectTracker
from core.perception.visualizer import PerceptionVisualizer, OverlayConfig
from core.procedure.progress import ProcedureProgressManager
from core.procedure.validator import load_procedure_file
from core.procedure.visualizer import ProcedureVisualizer
from core.ui.bridge import BackendEventBridge
from core.voice.manager import AudioQueueManager

logger = get_logger("ui_worker")


class MissionPipelineWorker(QThread):
    """Background worker executing the complete ASTRA-EA pipeline."""

    def __init__(
        self,
        bridge: BackendEventBridge,
        procedure_path: str = "configs/experiments/demo.yaml",
        camera_source: str = "0",
        camera_profile: str = "view_left",
        session_id: str = "SESSION_001",
        voice_manager: Optional[AudioQueueManager] = None,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self.procedure_path_str = procedure_path
        self.camera_source_str = camera_source
        self.camera_profile_str = camera_profile
        self.session_id = session_id
        self.voice_manager = voice_manager

        self._is_running = False
        self._is_paused = False
        self._stop_requested = False

        self.db: Optional[DatabaseManager] = None
        self.source = None
        self.overlay_config = OverlayConfig(show_confidence=False, show_hud=False, show_laser_guides=False)

    def run(self) -> None:
        """Main execution thread loop."""
        self._is_running = True
        self._terminal_status = "ABORTED"
        try:
            self._run_pipeline()
        except Exception as exc:
            self._terminal_status = "FAILED"
            logger.exception("Mission worker initialization or execution failed")
            self.bridge.sig_timeline_event.emit("SYSTEM", "Worker Error", str(exc), "DANGER")
        finally:
            try:
                if self.source:
                    self.source.stop()
                if self.db:
                    self.db.complete_experiment_run(self.session_id, status=self._terminal_status)
            finally:
                if self.db:
                    self.db.close()
                self._is_running = False
                self.bridge.sig_session_status.emit(self._terminal_status)

    def _run_pipeline(self) -> None:
        """Execute a session; run() owns cleanup, including initialization failures."""
        self.bridge.sig_session_status.emit("INITIALIZING")

        root = get_project_root()
        proc_path = Path(self.procedure_path_str)
        if not proc_path.is_absolute():
            proc_path = root / proc_path

        try:
            procedure = load_procedure_file(proc_path)
        except Exception as exc:
            self._terminal_status = "FAILED"
            logger.error("Failed to load procedure file: %s", exc)
            self.bridge.sig_timeline_event.emit("SYSTEM", "Procedure Load Failed", str(exc), "DANGER")
            self.bridge.sig_session_status.emit("FAILED")
            return

        profile = get_camera_profile(self.camera_profile_str)
        cfg = load_config()

        db_path = root / "storage" / "astra.db"
        self.db = DatabaseManager(db_path)
        self.db.initialize()
        self.db.record_experiment(
            experiment_id=procedure.experiment.id,
            name=procedure.experiment.name,
            version=procedure.experiment.version,
            description=procedure.experiment.description,
        )
        self.db.start_experiment_run(run_id=self.session_id, experiment_id=procedure.experiment.id)

        # Initialize Camera / Source
        if self.camera_source_str.isdigit():
            self.source = WebcamSource(device_id=int(self.camera_source_str), fps=30, width=1280, height=720)
        else:
            src_path = Path(self.camera_source_str)
            if not src_path.is_absolute():
                src_path = root / src_path
            self.source = VideoFileSource(file_path=src_path)

        if not self.source.start():
            self._terminal_status = "FAILED"
            logger.error("Failed to start camera source: %s", self.camera_source_str)
            self.bridge.sig_timeline_event.emit("SYSTEM", "Camera Source Failed", f"Source {self.camera_source_str} failed to open.", "DANGER")
            self.bridge.sig_session_status.emit("FAILED")
            return

        # Initialize Pipeline Components
        # Small specimen containers must remain detectable inside the virtual zone.
        detector = ColorSpatialObjectDetector(min_area=100.0)
        pose_est, hand_det = create_pose_and_hand_detectors()
        tracker = MultiObjectTracker(iou_threshold=0.2)
        scheduler = PerceptionScheduler(SchedulerConfig())
        event_bus = PerceptionEventBus()

        pipeline = PerceptionPipeline(
            detector=detector,
            pose_estimator=pose_est,
            hand_detector=hand_det,
            tracker=tracker,
            scheduler=scheduler,
            event_bus=event_bus,
        )

        interaction_engine = SpatialInteractionEngine(cfg.interaction)
        temporal_buffer = TemporalBuffer(window_seconds=cfg.activity.temporal_window_seconds)
        primitive_engine = PrimitiveActivityEngine(cfg.activity)
        composite_engine = CompositeActivityEngine()
        act_event_bus = ActivityEventBus()
        deduplicator = ActivityEventDeduplicator(act_event_bus)
        evidence_engine = MultimodalEvidenceEngine()
        assurance_engine = TriStateAssuranceEngine(default_camera_profile=profile.id, default_session_id=self.session_id)
        recovery_manager = ClosedLoopRecoveryManager()
        progress_manager = ProcedureProgressManager(procedure=procedure, run_id=self.session_id)
        observe_only = bool(getattr(procedure, "continuous_observation", False))
        visualizer = PerceptionVisualizer(self.overlay_config)
        proc_visualizer = ProcedureVisualizer(procedure=procedure)

        step_map = {s.id: s for s in procedure.steps}

        # Initialize optional streaming servers for ground observability
        video_server = None
        event_server = None
        if getattr(cfg.streaming, "enabled", False):
            try:
                from streaming.video.server import VideoStreamServer
                from streaming.video.config import VideoStreamConfig
                v_cfg = VideoStreamConfig(
                    host=cfg.streaming.host,
                    port=cfg.streaming.port,
                    width=cfg.streaming.width,
                    height=cfg.streaming.height,
                    fps=cfg.streaming.fps,
                    jpeg_quality=cfg.streaming.jpeg_quality,
                )
                video_server = VideoStreamServer(v_cfg)
                video_server.start()
            except Exception as exc:
                logger.warning("Could not start video stream server: %s", exc)

        if getattr(cfg.events, "enabled", False):
            try:
                from streaming.events.server import EventStreamServer
                from streaming.events.schema import EventType, EventSeverity
                event_server = EventStreamServer(
                    host=cfg.events.host,
                    port=cfg.events.port,
                    heartbeat_interval_seconds=cfg.events.heartbeat_interval_seconds,
                )
                event_server.start()
                event_server.publisher.create_event(
                    event_type=EventType.EXPERIMENT_STARTED,
                    experiment_id=procedure.experiment.id,
                    run_id=self.session_id,
                    message=f"Mission Started: {procedure.experiment.name}",
                    severity=EventSeverity.INFO,
                    payload={"total_steps": len(procedure.steps), "first_step_id": procedure.steps[0].id if procedure.steps else None},
                )
            except Exception as exc:
                logger.warning("Could not start event stream server: %s", exc)

        self.bridge.sig_session_status.emit("RUNNING")
        self.bridge.sig_timeline_event.emit("SYSTEM", "Mission Started", f"Run {self.session_id} initialized with {procedure.experiment.name}", "INFO")

        # Announce first step, unless this is the continuous Always Observe mode.
        if not observe_only:
            first_step = procedure.steps[0]
            first_msg = recovery_manager.get_step_guidance(first_step)
            if self.voice_manager:
                self.voice_manager.speak(first_msg.text)
            self.bridge.sig_voice.emit(first_msg.text, "GUIDANCE")
            self.bridge.sig_timeline_event.emit("STEP", f"Step 01 Active: {first_step.name}", first_step.description or "", "INFO")

        frames_processed = 0
        latencies = deque(maxlen=120)
        process = psutil.Process()
        process.cpu_percent()
        processing_started = time.monotonic()
        camera_failed = False

        try:
            while not self._stop_requested:
                if self._is_paused:
                    time.sleep(0.05)
                    continue

                fd = self.source.read()
                if fd is None:
                    if not getattr(self.source, "is_active", True):
                        break
                    if not camera_failed:
                        camera_failed = True
                        self.bridge.sig_session_status.emit("CAMERA_FAILURE")
                        self.bridge.sig_timeline_event.emit("SYSTEM", "Camera Failure", "Verification paused: no valid frame.", "DANGER")
                    time.sleep(0.005)
                    continue

                if camera_failed:
                    camera_failed = False
                    pipeline.reset()
                    temporal_buffer = TemporalBuffer(window_seconds=cfg.activity.temporal_window_seconds)
                    interaction_engine = SpatialInteractionEngine(cfg.interaction)
                    evidence_engine = MultimodalEvidenceEngine()
                    primitive_engine = PrimitiveActivityEngine(cfg.activity)
                    composite_engine = CompositeActivityEngine()
                    self.bridge.sig_session_status.emit("RUNNING")

                packet = FramePacket.from_frame_data(fd, capture_fps=self.source.get_fps())
                t0 = time.perf_counter()

                state = pipeline.process_frame(packet)
                interactions = interaction_engine.process(state.tracks, state.hands, state.timestamp)
                positions = {t.track_id: t.center for t in state.tracks}
                temporal_buffer.append(state.timestamp, interactions, positions)

                primitives = []
                composites = []
                for int_ev in interactions:
                    deduplicator.process_interaction(int_ev)
                    prim_obs = primitive_engine.evaluate(int_ev, temporal_buffer)
                    primitives.append(prim_obs)
                    deduplicator.process_activity(prim_obs)

                    comp_obs = composite_engine.update(prim_obs)
                    if comp_obs:
                        composites.append(comp_obs)
                        deduplicator.process_activity(comp_obs)

                curr_act = composites[0] if composites else (primitives[0] if primitives else None)
                curr_step_id = progress_manager.current_step
                step_def = step_map.get(curr_step_id) if curr_step_id else None

                if observe_only and curr_act:
                    self.bridge.sig_timeline_event.emit(
                        "OBSERVATION",
                        curr_act.activity_name,
                        f"Detected action on {curr_act.target_object_id or 'NONE'}",
                        "INFO",
                    )

                bundle = evidence_engine.evaluate(
                    activity=curr_act,
                    interactions=interactions,
                    tracks=state.tracks,
                    perception_state=state,
                    temporal_buffer=temporal_buffer,
                    step=step_def,
                )
                self.bridge.sig_evidence_bundle.emit(bundle)

                if curr_act and step_def:
                    proc_state = progress_manager.update(activity=curr_act, bundle=bundle, timestamp=state.timestamp)
                    self.bridge.sig_step_progress.emit(proc_state)

                    decision = assurance_engine.evaluate_step(
                        current_step=step_def,
                        activity=curr_act,
                        evidence=bundle,
                        camera_profile=profile,
                        session_id=self.session_id,
                        procedure=procedure,
                        completed_step_ids=proc_state.completed_steps,
                    )
                    self.db.record_assurance_decision(decision)
                    self.bridge.sig_assurance_decision.emit(decision, step_def)

                    if decision.is_verified:
                        self.bridge.sig_timeline_event.emit("ASSURANCE", f"{step_def.id} Verified", f"Verified with {decision.confidence*100:.0f}% confidence", "SUCCESS")
                        if event_server:
                            from streaming.events.schema import EventSeverity, EventType
                            event_server.publisher.create_event(
                                event_type=EventType.STEP_VERIFIED,
                                experiment_id=procedure.experiment.id,
                                run_id=self.session_id,
                                step_id=step_def.id,
                                status="VERIFIED",
                                severity=EventSeverity.INFO,
                                message=f"Step {step_def.id} Verified",
                                payload={"step_index": len(proc_state.completed_steps), "activity": curr_act.activity_name if curr_act else "IDLE"},
                            )
                    elif decision.is_uncertain:
                        self.bridge.sig_timeline_event.emit("ASSURANCE", f"{step_def.id} Uncertain", "Verification paused due to low visibility or partial occlusion", "WARNING")
                        if event_server:
                            from streaming.events.schema import EventSeverity, EventType
                            event_server.publisher.create_event(
                                event_type=EventType.STEP_UNCERTAIN,
                                experiment_id=procedure.experiment.id,
                                run_id=self.session_id,
                                step_id=step_def.id,
                                status="UNCERTAIN",
                                severity=EventSeverity.WARNING,
                                message=f"Step {step_def.id} Uncertain",
                                payload={"activity": curr_act.activity_name if curr_act else "IDLE"},
                            )
                    elif decision.is_deviation:
                        self.bridge.sig_deviation.emit(decision, step_def)
                        # AssuranceDecision exposes deviation_reason (the UI used to
                        # read the non-existent deviation_type attribute here, which
                        # crashed the worker exactly when a wrong object was found).
                        deviation_reason = getattr(decision, "deviation_reason", None)
                        deviation_name = (
                            deviation_reason.name
                            if hasattr(deviation_reason, "name")
                            else (str(deviation_reason) if deviation_reason else "ERROR")
                        )
                        self.bridge.sig_timeline_event.emit(
                            "DEVIATION",
                            f"Deviation: {deviation_name}",
                            "; ".join(decision.reasons),
                            "DANGER",
                        )
                        messages = recovery_manager.handle_decision(decision, step_def)
                        for msg in messages:
                            if self.voice_manager:
                                self.voice_manager.speak(msg.text)
                            self.bridge.sig_voice.emit(msg.text, msg.priority.name)
                        if recovery_manager.active_context:
                            self.db.record_recovery_event(recovery_manager.active_context)
                            self.bridge.sig_recovery.emit(recovery_manager.active_context)
                        if event_server:
                            from streaming.events.schema import EventSeverity, EventType
                            event_server.publisher.create_event(
                                event_type=EventType.DEVIATION_DETECTED,
                                experiment_id=procedure.experiment.id,
                                run_id=self.session_id,
                                step_id=step_def.id,
                                status="DEVIATION",
                                severity=EventSeverity.DANGER,
                                message="; ".join(decision.reasons) if decision.reasons else "Deviation detected",
                                payload={
                                    "deviation_type": deviation_name,
                                    "recovery_action": messages[0].text if messages else "",
                                },
                            )

                    if recovery_manager.is_recovering and not decision.is_deviation:
                        rec_done, rec_msg = recovery_manager.observe_corrective_action(curr_act, bundle, step_def)
                        if rec_done and rec_msg:
                            if self.voice_manager:
                                self.voice_manager.speak(rec_msg.text)
                            self.bridge.sig_voice.emit(rec_msg.text, rec_msg.priority.name)
                            if recovery_manager.active_context:
                                self.bridge.sig_recovery.emit(recovery_manager.active_context)
                                self.bridge.sig_timeline_event.emit("RECOVERY", "Recovery Verified", rec_msg.text, "SUCCESS")
                            if event_server:
                                from streaming.events.schema import EventSeverity, EventType
                                event_server.publisher.create_event(
                                    event_type=EventType.RECOVERY_VERIFIED,
                                    experiment_id=procedure.experiment.id,
                                    run_id=self.session_id,
                                    step_id=step_def.id,
                                    status="VERIFIED",
                                    severity=EventSeverity.INFO,
                                    message="Recovery Verified",
                                )
                            recovery_manager.complete_recovery()
                else:
                    proc_state = progress_manager.get_state()
                    self.bridge.sig_step_progress.emit(proc_state)

                # Render annotated video frame
                vis = visualizer.render(
                    packet.image,
                    state,
                    mode="PROCEDURE",
                    target_name=interactions[0].target_object_id if interactions else "NONE",
                    interaction_state=interactions[0].state.value if interactions else "NONE",
                    activity_name=curr_act.activity_name if curr_act else "IDLE",
                    activity_confidence=curr_act.confidence if curr_act else 0.0,
                )
                # The operator placement target is operational guidance, not a
                # debug overlay: show it automatically once STEP_02 is complete.
                vis = proc_visualizer.draw_virtual_work_surface(vis, proc_state)
                if self.overlay_config.show_hud:
                    vis = proc_visualizer.draw_procedure_hud(
                        vis,
                        progress_manager.get_state(),
                        camera_profile=profile.id,
                        assurance_decision=decision if (curr_act and step_def) else None,
                        recovery_state=recovery_manager.current_state.name,
                    )

                lat_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(lat_ms)
                frames_processed += 1

                # Emit frame to Qt UI
                self.bridge.sig_frame_ready.emit(vis, state)

                # Non-blocking distribution to Ground IP Video Stream
                if video_server:
                    video_server.publish_frame(vis)

                # Periodically emit health telemetry
                if frames_processed % 15 == 0:
                    mean_lat = float(np.mean(list(latencies)[-30:])) if latencies else 0.0
                    fps_val = frames_processed / max(0.001, time.monotonic() - processing_started)
                    self.bridge.sig_health.emit({
                        "fps": fps_val,
                        "latency_ms": mean_lat,
                        "cpu_pct": process.cpu_percent(),
                        "ram_mb": process.memory_info().rss / (1024 * 1024),
                        "frames": frames_processed,
                    })
                    if event_server:
                        event_server.set_health_metrics({"fps": round(fps_val, 1), "latency_ms": round(mean_lat, 2)})

                proc_st = progress_manager.get_state()
                st_val = getattr(proc_st, "procedure_status", getattr(proc_st, "status", None))
                if getattr(st_val, "value", str(st_val)) == "COMPLETED":
                    self._terminal_status = "COMPLETED"
                    self.bridge.sig_session_status.emit("COMPLETED")
                    self.bridge.sig_timeline_event.emit("SYSTEM", "Procedure Completed", "All procedure steps verified successfully.", "SUCCESS")
                    if event_server:
                        from streaming.events.schema import EventSeverity, EventType
                        event_server.publisher.create_event(
                            event_type=EventType.EXPERIMENT_COMPLETED,
                            experiment_id=procedure.experiment.id,
                            run_id=self.session_id,
                            message="Experiment Procedure Completed",
                            severity=EventSeverity.INFO,
                        )
                    break

        except Exception as exc:
            self._terminal_status = "FAILED"
            logger.error("Exception in mission worker loop: %s", exc)
            self.bridge.sig_timeline_event.emit("SYSTEM", "Worker Error", str(exc), "DANGER")
        finally:
            if video_server:
                video_server.stop()
            if event_server:
                event_server.stop()

    def pause(self) -> None:
        """Pause worker processing."""
        self._is_paused = True

    def resume(self) -> None:
        """Resume worker processing."""
        self._is_paused = False

    def stop(self) -> bool:
        """Request worker termination."""
        self._stop_requested = True
        return self.wait(2000)
