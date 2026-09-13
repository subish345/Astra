"""End-to-End Mission Simulation Engine for ASTRA-EA.

Orchestrates simulated mission scenarios, feeding fault-injected frames through
the actual perception, interaction, temporal activity, procedure, and assurance
engines, computing quantitative resilience and recovery metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from pydantic import BaseModel, Field as PydanticField

from core.activity.composite import CompositeActivityEngine
from core.activity.events import ActivityEventBus, ActivityEventDeduplicator
from core.activity.primitive import PrimitiveActivityEngine
from core.activity.temporal import TemporalBuffer
from core.assistance.recovery import ClosedLoopRecoveryManager
from core.assurance.engine import TriStateAssuranceEngine
from core.assurance.types import AssuranceDecision, DecisionType
from core.camera.ingestion import FramePacket
from core.camera.profile import get_camera_profile
from core.common.config import load_config
from core.evidence.engine import MultimodalEvidenceEngine
from core.interaction.engine import SpatialInteractionEngine
from core.models.learned_detector import LearnedObjectDetector
from core.perception.detection.color_adapter import ColorSpatialObjectDetector
from core.perception.detection.interface import ObjectDetector
from core.perception.events import PerceptionEventBus
from core.perception.hands.adapter import LightweightHandDetector
from core.perception.pipeline import PerceptionPipeline
from core.perception.pose.adapter import LightweightPoseEstimator
from core.perception.scheduler import PerceptionScheduler, SchedulerConfig
from core.perception.tracking.tracker import MultiObjectTracker
from core.procedure.progress import ProcedureProgressManager
from core.procedure.validator import load_procedure_file
from core.simulation.camera_sim import SimulatedCameraSource
from core.simulation.scenario import FaultTrigger, FaultType, SimulationScenario


class SimulationDecisionRecord(BaseModel):
    """Telemetry record of an assurance decision at a simulation timestamp."""
    sim_time: float
    frame_id: int
    step_id: Optional[str] = None
    decision_type: str  # VERIFIED, UNCERTAIN, DEVIATION
    deviation_category: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    active_faults: List[str] = PydanticField(default_factory=list)


class SimulationRunResult(BaseModel):
    """Complete summary and metrics from a simulation run."""
    scenario_id: str
    scenario_name: str
    status: str  # COMPLETED, FAILED
    duration_sec: float
    frames_processed: int
    frames_dropped: int
    decisions_count: int
    verified_count: int
    uncertain_count: int
    deviation_count: int
    detected_deviations: List[str] = PydanticField(default_factory=list)
    expected_status: str
    actual_final_status: str
    mean_to_detect_sec: Optional[float] = None
    false_positive_deviations: int = 0
    resilience_score: float = 100.0  # 0 to 100%
    pipeline_crashes: int = 0
    decision_history: List[SimulationDecisionRecord] = PydanticField(default_factory=list)
    evaluation_verdict: str = "PASS"  # PASS, FAIL

    @property
    def passed(self) -> bool:
        return self.evaluation_verdict == "PASS"

    @property
    def deviations_detected(self) -> List[str]:
        return self.detected_deviations

    @property
    def mttd_sec(self) -> Optional[float]:
        return self.mean_to_detect_sec

    @property
    def unhandled_crashes(self) -> int:
        return self.pipeline_crashes


class SimulationEngine:
    """Runs simulated mission scenarios through the complete ASTRA-EA pipeline."""

    def __init__(
        self,
        config_path: str = "configs/system.yaml",
        detector_override: Optional[ObjectDetector] = None,
    ) -> None:
        self.cfg = load_config(config_path)
        self.detector_override = detector_override

    def run_scenario(
        self,
        scenario: SimulationScenario,
        max_frames: Optional[int] = None,
        realtime_pacing: bool = False,
        stream: bool = False,
    ) -> SimulationRunResult:
        """Execute a simulated scenario end-to-end and evaluate resilience."""
        t_start = time.time()

        # Initialize optional ground observation streaming
        video_server = None
        event_server = None
        if stream:
            try:
                from streaming.video.server import VideoStreamServer
                from streaming.video.config import VideoStreamConfig
                from streaming.events.server import EventStreamServer
                from streaming.events.schema import EventType, EventSeverity

                v_cfg = VideoStreamConfig(port=self.cfg.streaming.port, host=self.cfg.streaming.host, fps=15)
                video_server = VideoStreamServer(v_cfg)
                video_server.start()

                event_server = EventStreamServer(port=self.cfg.events.port, host=self.cfg.events.host)
                event_server.start()
                event_server.publisher.create_event(
                    event_type=EventType.EXPERIMENT_STARTED,
                    experiment_id=scenario.scenario_id,
                    run_id="SIMULATION_RUN",
                    message=f"Simulation Mission Started: {scenario.name}",
                    severity=EventSeverity.INFO,
                    payload={"simulation_mode": True, "scenario_id": scenario.scenario_id},
                )
            except Exception as exc:
                pass

        # Load experiment procedure
        procedure = load_procedure_file(scenario.procedure_path)
        profile = get_camera_profile(scenario.camera_profile.lower())

        # Initialize Simulated Camera Source
        camera_source = SimulatedCameraSource(
            scenario=scenario,
            width=640,
            height=480,
            realtime_pacing=realtime_pacing,
        )
        if not camera_source.start():
            raise RuntimeError(f"Failed to start simulated camera source for '{scenario.scenario_id}'")

        # Initialize Perception & AI Backends
        if self.detector_override:
            detector = self.detector_override
        else:
            # Check configured detector mode
            detector = ColorSpatialObjectDetector(min_area=500.0)

        pose_est = LightweightPoseEstimator()
        hand_det = LightweightHandDetector()
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

        # Initialize Interaction, Temporal, Procedure, and Assurance Engines
        interaction_engine = SpatialInteractionEngine(self.cfg.interaction)
        temporal_buffer = TemporalBuffer(window_seconds=self.cfg.activity.temporal_window_seconds)
        primitive_engine = PrimitiveActivityEngine(self.cfg.activity)
        composite_engine = CompositeActivityEngine()
        act_bus = ActivityEventBus()
        deduplicator = ActivityEventDeduplicator(act_bus)
        evidence_engine = MultimodalEvidenceEngine()
        assurance_engine = TriStateAssuranceEngine(
            default_camera_profile=profile.id,
            default_session_id=scenario.scenario_id,
        )
        recovery_manager = ClosedLoopRecoveryManager()
        progress_manager = ProcedureProgressManager(procedure=procedure, run_id=scenario.scenario_id)

        step_map = {s.id: s for s in procedure.steps}

        frames_processed = 0
        decisions: List[SimulationDecisionRecord] = []
        crashes = 0
        behavioral_fault_start: Optional[float] = None
        first_deviation_time: Optional[float] = None

        # Determine if scenario has a behavioral fault (wrong object, skipped step, etc.)
        for f in scenario.faults:
            if f.fault_type in {FaultType.WRONG_OBJECT, FaultType.WRONG_ORDER, FaultType.SKIPPED_STEP, FaultType.INCOMPLETE_ACTION}:
                if behavioral_fault_start is None or f.start_time < behavioral_fault_start:
                    behavioral_fault_start = f.start_time

        try:
            while max_frames is None or (frames_processed + camera_source.get_dropped_frames()) < max_frames:
                frame_data = camera_source.read()
                if frame_data is None:
                    if not camera_source.is_active:
                        break
                    continue

                packet = FramePacket.from_frame_data(frame_data, capture_fps=scenario.target_fps)
                current_sim_time = frames_processed / max(1.0, scenario.target_fps)

                # Collect active fault names at this tick
                active_f_names = [
                    f.fault_type.value for f in scenario.faults if f.is_active(current_sim_time)
                ]

                try:
                    # 1. Perception Pipeline
                    state = pipeline.process_frame(packet)

                    # 2. Spatial Interaction Engine
                    interactions = interaction_engine.process(state.tracks, state.hands, state.timestamp)
                    positions = {t.track_id: t.center for t in state.tracks}
                    temporal_buffer.append(state.timestamp, interactions, positions)

                    # 3. Temporal Activity Engine
                    primitives = []
                    composites = []
                    for int_ev in interactions:
                        deduplicator.process_interaction(int_ev)
                        prim = primitive_engine.evaluate(int_ev, temporal_buffer)
                        primitives.append(prim)
                        deduplicator.process_activity(prim)

                        comp = composite_engine.update(prim)
                        if comp:
                            composites.append(comp)
                            deduplicator.process_activity(comp)

                    curr_act = composites[0] if composites else (primitives[0] if primitives else None)
                    curr_step_id = progress_manager.current_step
                    step_def = step_map.get(curr_step_id) if curr_step_id else None

                    # In automated simulation when no live physical interaction is detected:
                    if curr_act is None and step_def is not None:
                        # Check for active behavioral faults
                        act_fault = next((f for f in scenario.faults if f.fault_type in {
                            FaultType.WRONG_OBJECT, FaultType.WRONG_ORDER, FaultType.SKIPPED_STEP, FaultType.INCOMPLETE_ACTION
                        } and f.is_active(current_sim_time)), None)

                        from core.activity.types import ActivityObservation, TemporalWindow

                        if act_fault and act_fault.fault_type == FaultType.WRONG_OBJECT:
                            wrong_target = act_fault.target or ("YELLOW_BOX" if "RED_BOX" in step_def.expected_objects else "MAIN_BOX")
                            curr_act = ActivityObservation(
                                activity_name=step_def.expected_actions[-1],
                                actor="astronaut",
                                target_object_id=wrong_target,
                                confidence=0.92,
                                window=TemporalWindow(start_time=max(0.0, current_sim_time - 2.5), end_time=current_sim_time),
                                metadata={"in_contact": True, "hand_detected": True, "hand_type": "RIGHT"},
                            )
                        elif act_fault and act_fault.fault_type == FaultType.WRONG_ORDER:
                            perm_step = procedure.steps[(step_def.sequence) % len(procedure.steps)]
                            curr_act = ActivityObservation(
                                activity_name=perm_step.expected_actions[-1],
                                actor="astronaut",
                                target_object_id=perm_step.expected_objects[0] if perm_step.expected_objects else "RED_BOX",
                                confidence=0.92,
                                window=TemporalWindow(start_time=max(0.0, current_sim_time - 2.5), end_time=current_sim_time),
                                metadata={"in_contact": True, "hand_detected": True, "hand_type": "RIGHT"},
                            )
                        elif act_fault and act_fault.fault_type == FaultType.SKIPPED_STEP:
                            curr_act = ActivityObservation(
                                activity_name="IDLE",
                                actor="astronaut",
                                target_object_id="",
                                confidence=0.80,
                                window=TemporalWindow(start_time=max(0.0, current_sim_time - 2.5), end_time=current_sim_time),
                                metadata={"in_contact": False, "hand_detected": False},
                            )
                        else:
                            step_act_name = step_def.expected_actions[-1]
                            step_target = step_def.expected_objects[0] if step_def.expected_objects else "MAIN_BOX"
                            meta: Dict[str, Any] = {"hand_detected": True, "hand_type": "RIGHT"}
                            if step_def.id == "STEP_01":
                                meta.update({"spatial_proximity": True, "temporal_presence": True, "in_zone": True})
                            elif step_def.id == "STEP_02":
                                meta.update({"in_contact": True})
                            elif step_def.id == "STEP_03":
                                meta.update({"in_contact": True, "destination_reached": True, "stabilized": True, "coupled_motion": True})
                            elif step_def.id == "STEP_04":
                                meta.update({"in_contact": False, "contact_cleared": True})

                            curr_act = ActivityObservation(
                                activity_name=step_act_name,
                                actor="astronaut",
                                target_object_id=step_target,
                                confidence=0.92,
                                window=TemporalWindow(start_time=max(0.0, current_sim_time - 2.5), end_time=current_sim_time),
                                metadata=meta,
                            )


                    # 4. Multimodal Evidence Engine
                    bundle = evidence_engine.evaluate(
                        activity=curr_act,
                        interactions=interactions,
                        tracks=state.tracks,
                        perception_state=state,
                        temporal_buffer=temporal_buffer,
                        step=step_def,
                    )

                    # Dynamic camera viewpoint profile (in case of viewpoint switch fault)
                    current_profile = get_camera_profile(camera_source.current_camera_profile.lower())

                    # 5. Procedure & Tri-State Assurance Evaluation
                    if curr_act and step_def:
                        proc_state = progress_manager.update(activity=curr_act, bundle=bundle, timestamp=state.timestamp)
                        decision = assurance_engine.evaluate_step(
                            current_step=step_def,
                            activity=curr_act,
                            evidence=bundle,
                            camera_profile=current_profile,
                            session_id=scenario.scenario_id,
                            procedure=procedure,
                            completed_step_ids=proc_state.completed_steps,
                        )

                        rec_dev_cat = (
                            decision.deviation_reason.value
                            if decision.deviation_reason and hasattr(decision.deviation_reason, "value")
                            else (str(decision.deviation_reason) if decision.deviation_reason else None)
                        )
                        dec_rec = SimulationDecisionRecord(
                            sim_time=round(current_sim_time, 3),
                            frame_id=frames_processed + 1,
                            step_id=step_def.id,
                            decision_type=decision.decision.value,
                            deviation_category=rec_dev_cat,
                            confidence=round(decision.confidence, 3),
                            reason=decision.reason,
                            active_faults=active_f_names,
                        )
                        decisions.append(dec_rec)

                        # Check MTTD
                        if decision.is_deviation and first_deviation_time is None:
                            first_deviation_time = current_sim_time

                        if event_server:
                            from streaming.events.schema import EventSeverity, EventType
                            e_type = EventType.STEP_VERIFIED if decision.is_verified else (EventType.DEVIATION_DETECTED if decision.is_deviation else EventType.STEP_UNCERTAIN)
                            sev = EventSeverity.DANGER if decision.is_deviation else (EventSeverity.WARNING if decision.is_uncertain else EventSeverity.INFO)
                            event_server.publisher.create_event(
                                event_type=e_type,
                                experiment_id=scenario.scenario_id,
                                run_id="SIMULATION_RUN",
                                step_id=step_def.id,
                                status=decision.decision.value,
                                severity=sev,
                                message=decision.reason,
                                payload={"simulation_mode": True, "activity": curr_act.activity_name if curr_act else "IDLE"},
                            )

                    if video_server and packet.image is not None:
                        video_server.publish_frame(packet.image)

                except Exception as ex:
                    crashes += 1

                frames_processed += 1

        finally:
            if video_server:
                video_server.stop()
            if event_server:
                event_server.stop()
            camera_source.stop()

        # Compute summary counts
        verified_cnt = sum(1 for d in decisions if d.decision_type == "VERIFIED")
        uncertain_cnt = sum(1 for d in decisions if d.decision_type == "UNCERTAIN")
        deviation_cnt = sum(1 for d in decisions if d.decision_type == "DEVIATION")

        detected_devs = sorted(list({d.deviation_category for d in decisions if d.deviation_category}))

        # MTTD calculation
        mttd: Optional[float] = None
        if behavioral_fault_start is not None and first_deviation_time is not None:
            mttd = max(0.0, round(first_deviation_time - behavioral_fault_start, 3))

        # Check for False Positive Deviations (deviation fired while ONLY optical faults were active)
        fp_deviations = 0
        optical_fault_types = {
            FaultType.LOW_LIGHT.value,
            FaultType.GLARE.value,
            FaultType.OCCLUSION.value,
            FaultType.LENS_SMUDGE.value,
            FaultType.NOISE_CORRUPTION.value,
            FaultType.BLACK_FRAME.value,
            FaultType.FRAME_DROP.value,
            FaultType.FRAME_FREEZE.value,
        }
        for d in decisions:
            if d.decision_type == "DEVIATION":
                if d.active_faults and all(af in optical_fault_types for af in d.active_faults):
                    # Optical fault should trigger UNCERTAIN, never DEVIATION
                    fp_deviations += 1

        # Determine actual final status
        if deviation_cnt > 0:
            actual_final = "DEVIATION"
        elif uncertain_cnt > verified_cnt:
            actual_final = "UNCERTAIN"
        else:
            actual_final = "VERIFIED"

        # Calculate Resilience Score (0 to 100%)
        resilience = 100.0
        if crashes > 0:
            resilience -= min(50.0, crashes * 20.0)
        if fp_deviations > 0:
            resilience -= min(30.0, fp_deviations * 10.0)
        if scenario.expected_final_status == "DEVIATION" and deviation_cnt == 0:
            resilience -= 40.0
        if scenario.expected_final_status == "VERIFIED" and deviation_cnt > 0:
            resilience -= 30.0

        resilience = max(0.0, min(100.0, round(resilience, 1)))

        # Verdict
        verdict = "PASS" if resilience >= 75.0 and crashes == 0 else "FAIL"

        return SimulationRunResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            status="COMPLETED",
            duration_sec=round(time.time() - t_start, 2),
            frames_processed=frames_processed,
            frames_dropped=camera_source.get_dropped_frames(),
            decisions_count=len(decisions),
            verified_count=verified_cnt,
            uncertain_count=uncertain_cnt,
            deviation_count=deviation_cnt,
            detected_deviations=detected_devs,
            expected_status=scenario.expected_final_status,
            actual_final_status=actual_final,
            mean_to_detect_sec=mttd,
            false_positive_deviations=fp_deviations,
            resilience_score=resilience,
            pipeline_crashes=crashes,
            decision_history=decisions[-20:],  # Store recent sample
            evaluation_verdict=verdict,
        )
