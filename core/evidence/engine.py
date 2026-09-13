"""Corroborating multimodal evidence engine for ASTRA-EA.

Aggregates observations across perception, kinematics, temporal features, and
spatial states to produce structured, explainable EvidenceBundles for experiment steps.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from core.activity.temporal import TemporalBuffer
from core.activity.types import ActivityObservation, ActivityStatus
from core.evidence.interface import EvidenceEngine as BaseEvidenceEngine
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.interaction.types import InteractionEvent, InteractionState
from core.perception.types import PerceptionState, Track
from core.procedure.schema import EvidencePathRule, ExperimentStep


class MultimodalEvidenceEngine(BaseEvidenceEngine):
    """Gathers and evaluates multi-dimensional evidence factors to corroborate procedural activities."""

    # Weights for composite evidence scoring
    WEIGHT_REQUIRED = 0.40
    WEIGHT_CONFIDENCE = 0.25
    WEIGHT_PROCEDURE = 0.20
    WEIGHT_TEMPORAL = 0.15

    def __init__(
        self,
        contact_distance_threshold: float = 0.18,
        min_motion_velocity_px_s: float = 12.0,
        temporal_window_seconds: float = 5.0,
    ):
        self.contact_distance_threshold = contact_distance_threshold
        self.min_motion_velocity_px_s = min_motion_velocity_px_s
        self.temporal_window_seconds = temporal_window_seconds
        self._contact_history: Dict[str, Dict[str, Any]] = {}

    def reset(self) -> None:
        """Reset internal temporal contact and state history."""
        self._contact_history.clear()

    def evaluate(
        self,
        activity: Optional[ActivityObservation] = None,
        interactions: Optional[List[InteractionEvent]] = None,
        tracks: Optional[List[Track]] = None,
        perception_state: Optional[PerceptionState] = None,
        temporal_buffer: Optional[TemporalBuffer] = None,
        step: Optional[ExperimentStep] = None,
    ) -> EvidenceBundle:
        """Construct an explainable EvidenceBundle for a candidate activity against a step."""
        from core.evidence.types import normalize_evidence_name

        raw_interactions = interactions
        interactions = interactions or []
        tracks = tracks or (perception_state.tracks if perception_state else [])
        frame_id = perception_state.frame_id if perception_state else 0
        current_time = perception_state.timestamp if perception_state else 0.0
        act_start = getattr(activity, "start_time", getattr(activity, "timestamp_start", current_time)) if activity else current_time
        act_end = getattr(activity, "end_time", getattr(activity, "timestamp_end", current_time)) if activity else current_time
        if not perception_state and activity:
            current_time = act_end

        target_obj = (
            activity.target_object_id
            if activity and activity.target_object_id
            else (interactions[0].target_object_id if interactions else None)
        )
        if not target_obj and step and step.expected_objects:
            target_obj = step.expected_objects[0]

        bundle = EvidenceBundle(
            activity_id=activity.activity_id if activity else f"ACT_{frame_id}",
            activity_name=activity.activity_name if activity else (interactions[0].state.value if interactions else "IDLE"),
            target_object_id=target_obj,
            timestamp=current_time,
            step_id=step.id if step else None,
            timestamp_range=(act_start, act_end),
            source_frames=[frame_id] if frame_id > 0 else [],
        )

        # 1. OBJECT_DETECTED
        obj_track = next((t for t in tracks if t.class_name == target_obj and t.is_active), None)
        obj_conf = obj_track.confidence if obj_track else 0.0
        if not obj_track and activity and activity.metadata and activity.metadata.get("object_detected") is not None:
            obj_detected = bool(activity.metadata.get("object_detected"))
            obj_conf = 0.90 if obj_detected else 0.0
        else:
            obj_detected = obj_track is not None or (activity is not None and activity.target_object_id is not None)
            if not obj_conf and obj_detected:
                obj_conf = activity.confidence if activity else 0.85
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.OBJECT_DETECTED,
                verified=obj_detected,
                confidence=obj_conf,
                object_id=target_obj,
                start_frame=frame_id,
                end_frame=frame_id,
                start_time=current_time,
                end_time=current_time,
                details={"track_id": obj_track.track_id if obj_track else None},
            )
        )

        # 2. ACTOR_DETECTED
        person_present = False
        actor_conf = 0.0
        if perception_state and perception_state.persons:
            person_present = True
            actor_conf = 0.90
        elif activity and activity.actor:
            person_present = True
            actor_conf = 0.85
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.ACTOR_DETECTED,
                verified=person_present,
                confidence=actor_conf,
                start_frame=frame_id,
                end_frame=frame_id,
                start_time=current_time,
                end_time=current_time,
                details={"actor": activity.actor if activity else "person_01"},
            )
        )

        # 3. HAND_DETECTED
        hand_present = False
        hand_conf = 0.0
        active_hand_type = None
        if perception_state and perception_state.hands:
            hand_present = True
            hand_conf = perception_state.hands[0].confidence
            active_hand_type = perception_state.hands[0].hand_type.value
        elif activity and (
            getattr(activity, "hand_type", None)
            or (activity.metadata and (activity.metadata.get("hand_detected") or activity.metadata.get("hand_type")))
        ):
            hand_present = True
            hand_conf = 0.85
            active_hand_type = getattr(activity, "hand_type", None) or (
                activity.metadata.get("hand_type") if activity.metadata else "RIGHT"
            )
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.HAND_DETECTED,
                verified=hand_present,
                confidence=hand_conf,
                hand_id=active_hand_type,
                start_frame=frame_id,
                end_frame=frame_id,
                start_time=current_time,
                end_time=current_time,
            )
        )

        # 4. HAND_OBJECT_CONTACT
        in_contact = False
        contact_conf = 0.0
        for ev in interactions:
            if ev.state in (InteractionState.CONTACT, InteractionState.GRASPING, InteractionState.HOLDING, InteractionState.MOVING):
                in_contact = True
                contact_conf = max(contact_conf, ev.confidence)
            elif ev.spatial and ev.spatial.normalized_distance <= self.contact_distance_threshold:
                in_contact = True
                contact_conf = max(contact_conf, 0.75)

        if not in_contact and activity and activity.metadata and activity.metadata.get("in_contact") is not None:
            in_contact = bool(activity.metadata.get("in_contact"))
            contact_conf = 0.90 if in_contact else 0.10
        elif not in_contact and raw_interactions is None and perception_state is None and activity:
            if activity.activity_name in ("TOUCH", "GRASP", "HOLD", "MOVE", "LIFT", "PICKUP"):
                in_contact = True
                contact_conf = activity.confidence

        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.HAND_OBJECT_CONTACT,
                verified=in_contact,
                confidence=contact_conf,
                object_id=target_obj,
                hand_id=active_hand_type,
                start_frame=frame_id,
                end_frame=frame_id,
                start_time=current_time,
                end_time=current_time,
            )
        )

        # 5. CONTACT_CLEARED (Prompt §6, §7)
        obj_key = target_obj or "DEFAULT_OBJ"
        history = self._contact_history.setdefault(
            obj_key,
            {"had_contact": False, "last_contact_time": 0.0, "clearance_start_time": None},
        )
        if in_contact:
            history["had_contact"] = True
            history["last_contact_time"] = current_time
            history["clearance_start_time"] = None
            contact_cleared = False
            clearance_conf = 0.0
        else:
            if history["had_contact"]:
                if history["clearance_start_time"] is None:
                    history["clearance_start_time"] = current_time
                clearance_duration = max(0.0, current_time - history["clearance_start_time"])
                act_is_release = activity and activity.activity_name == "RELEASE"
                act_duration = activity.duration_seconds if activity else 0.0
                if (clearance_duration >= 0.5 or (act_is_release and act_duration >= 0.5)) and (obj_track is not None or target_obj is not None):
                    contact_cleared = True
                    clearance_conf = 0.92
                else:
                    contact_cleared = False
                    clearance_conf = 0.35
            else:
                if activity and activity.metadata and activity.metadata.get("contact_cleared") is not None:
                    contact_cleared = bool(activity.metadata.get("contact_cleared"))
                    clearance_conf = 0.90 if contact_cleared else 0.15
                elif activity and activity.activity_name == "RELEASE" and activity.duration_seconds >= 0.5:
                    contact_cleared = True
                    clearance_conf = 0.90
                else:
                    contact_cleared = False
                    clearance_conf = 0.0
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.CONTACT_CLEARED,
                verified=contact_cleared,
                confidence=clearance_conf,
                object_id=target_obj,
                details={"in_contact": in_contact, "had_prior_contact": history["had_contact"]},
            )
        )

        # 6. OBJECT_MOTION
        obj_moving = False
        motion_speed = 0.0
        if obj_track:
            vel = getattr(obj_track, "velocity", (0.0, 0.0))
            if vel and (vel[0] != 0.0 or vel[1] != 0.0):
                motion_speed = float(np.hypot(vel[0], vel[1]))
            elif temporal_buffer:
                traj = temporal_buffer.get_track_trajectory(obj_track.track_id, duration=1.0)
                if len(traj) >= 2:
                    dt = max(0.001, traj[-1][0] - traj[0][0])
                    dx = traj[-1][1][0] - traj[0][1][0]
                    dy = traj[-1][1][1] - traj[0][1][1]
                    motion_speed = float(np.hypot(dx, dy) / dt)
            obj_moving = motion_speed >= self.min_motion_velocity_px_s
        elif activity:
            if activity.activity_name in ("MOVE", "LIFT", "CARRY", "MOVE_OBJECT"):
                obj_moving = True
                motion_speed = 25.0
            elif activity.metadata and activity.metadata.get("moving") is not None:
                obj_moving = bool(activity.metadata.get("moving"))
                motion_speed = 30.0 if obj_moving else 0.0
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.OBJECT_MOTION,
                verified=obj_moving,
                confidence=min(1.0, motion_speed / 50.0) if obj_moving else 0.5,
                object_id=target_obj,
                details={"speed_px_s": round(motion_speed, 2)},
            )
        )

        # 7. COUPLED_MOTION
        coupled = in_contact and obj_moving
        if not coupled and activity:
            if activity.activity_name in ("MOVE", "LIFT", "CARRY", "MOVE_OBJECT"):
                coupled = True
            elif activity.activity_name in ("PLACE", "PLACE_OBJECT"):
                prims = getattr(activity, "primitives", []) or (activity.metadata.get("primitives", []) if activity.metadata else [])
                if any(p in ("MOVE", "LIFT", "CARRY") for p in prims) or (activity.metadata and activity.metadata.get("coupled_motion")):
                    coupled = True
            elif activity.metadata and activity.metadata.get("coupled_motion") is not None:
                coupled = bool(activity.metadata.get("coupled_motion"))
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.COUPLED_MOTION,
                verified=coupled,
                confidence=min(contact_conf, 0.95) if coupled else 0.0,
                object_id=target_obj,
                hand_id=active_hand_type,
            )
        )

        # 8. SPATIAL_PROXIMITY (Prompt §2)
        proximity_ok = False
        proximity_conf = 0.0
        proximity_dist = 1.0
        if perception_state and perception_state.persons and obj_track:
            p_box = perception_state.persons[0].bbox
            o_box = obj_track.bbox
            if p_box and o_box:
                p_center = p_box.center if hasattr(p_box, "center") else ((p_box[0] + p_box[2]) / 2.0, (p_box[1] + p_box[3]) / 2.0)
                o_center = o_box.center if hasattr(o_box, "center") else ((o_box[0] + o_box[2]) / 2.0, (o_box[1] + o_box[3]) / 2.0)
                proximity_dist = float(np.hypot(p_center[0] - o_center[0], p_center[1] - o_center[1]))
                if proximity_dist <= 0.35:
                    proximity_ok = True
                    proximity_conf = max(0.60, 1.0 - proximity_dist)
                else:
                    proximity_ok = False
                    proximity_conf = max(0.10, 1.0 - proximity_dist)
        elif activity:
            if activity.metadata and "spatial_proximity" in activity.metadata:
                proximity_ok = bool(activity.metadata["spatial_proximity"])
                proximity_conf = 0.90 if proximity_ok else 0.20
            elif activity.metadata and "in_zone" in activity.metadata:
                proximity_ok = bool(activity.metadata["in_zone"])
                proximity_conf = 0.90 if proximity_ok else 0.20
            elif activity.activity_name == "APPROACH":
                proximity_ok = True
                proximity_conf = activity.confidence
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.SPATIAL_PROXIMITY,
                verified=proximity_ok,
                confidence=proximity_conf,
                details={"normalized_distance": round(proximity_dist, 3)},
            )
        )

        # 9. TEMPORAL_PRESENCE (Prompt §2)
        presence_duration = activity.duration_seconds if activity else (current_time - act_start)
        min_presence = 2.0
        if step and step.completion and step.completion.minimum_duration_seconds:
            min_presence = step.completion.minimum_duration_seconds
        elif step and step.min_duration_seconds:
            min_presence = step.min_duration_seconds
        presence_ok = proximity_ok and (presence_duration >= min_presence)
        presence_conf = min(1.0, presence_duration / max(0.1, min_presence)) if proximity_ok else 0.0
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.TEMPORAL_PRESENCE,
                verified=presence_ok,
                confidence=presence_conf,
                details={"duration_seconds": round(presence_duration, 2), "required_min": min_presence},
            )
        )

        # 10. DESTINATION_MATCH (Prompt §3, §4)
        dest_match = False
        dest_conf = 0.0
        if step and step.destination:
            dest_rule = step.destination
            dest_obj_name = dest_rule.object
            max_d = dest_rule.max_distance
            if dest_obj_name and obj_track:
                dest_track = next((t for t in tracks if t.class_name == dest_obj_name and t.is_active), None)
                if dest_track and obj_track.bbox and dest_track.bbox:
                    o_box = obj_track.bbox
                    d_box = dest_track.bbox
                    o_center = o_box.center if hasattr(o_box, "center") else ((o_box[0] + o_box[2]) / 2.0, (o_box[1] + o_box[3]) / 2.0)
                    d_center = d_box.center if hasattr(d_box, "center") else ((d_box[0] + d_box[2]) / 2.0, (d_box[1] + d_box[3]) / 2.0)
                    d_dist = float(np.hypot(o_center[0] - d_center[0], o_center[1] - d_center[1]))
                    if d_dist <= max_d:
                        dest_match = True
                        dest_conf = 0.92
                    else:
                        dest_match = False
                        dest_conf = max(0.10, 1.0 - d_dist)
            if activity and activity.metadata and "destination_match" in activity.metadata:
                dest_match = bool(activity.metadata["destination_match"])
                dest_conf = 0.90 if dest_match else 0.15
            elif not dest_match and activity and activity.activity_name in ("PLACE", "PLACE_OBJECT"):
                dest_match = True
                dest_conf = activity.confidence
        elif activity and activity.metadata and "destination_match" in activity.metadata:
            dest_match = bool(activity.metadata["destination_match"])
            dest_conf = 0.90 if dest_match else 0.15
        else:
            dest_match = True
            dest_conf = 0.85
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.DESTINATION_MATCH,
                verified=dest_match,
                confidence=dest_conf,
                details={"destination_object": step.destination.object if (step and step.destination) else None},
            )
        )

        # 11. OBJECT_STABILIZED (Prompt §3, §5)
        stab_ok = False
        stab_conf = 0.0
        if activity and activity.metadata and "object_stabilized" in activity.metadata:
            stab_ok = bool(activity.metadata["object_stabilized"])
            stab_conf = 0.92 if stab_ok else 0.20
        elif activity and activity.metadata and "stabilized" in activity.metadata:
            stab_ok = bool(activity.metadata["stabilized"])
            stab_conf = 0.92 if stab_ok else 0.20
        else:
            if obj_moving:
                stab_ok = False
                stab_conf = 0.20
            else:
                if step and step.destination and not dest_match:
                    stab_ok = False
                    stab_conf = 0.30
                else:
                    stab_ok = True
                    stab_conf = 0.88
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.OBJECT_STABILIZED,
                verified=stab_ok,
                confidence=stab_conf,
                details={"is_moving": obj_moving, "destination_matched": dest_match},
            )
        )

        # 12. POSE_CONSISTENCY
        pose_ok = False
        if perception_state and perception_state.poses:
            pose_ok = len(perception_state.poses[0].keypoints) >= 4
        else:
            pose_ok = True  # Default permissive when running without full pose
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.POSE_CONSISTENCY,
                verified=pose_ok,
                confidence=0.88 if pose_ok else 0.0,
            )
        )

        # 13. TEMPORAL_CONSISTENCY
        duration = activity.duration_seconds if activity else (interactions[0].duration_seconds if interactions else 0.0)
        temp_ok = True
        if step:
            if duration < step.min_duration_seconds:
                temp_ok = False
            if step.timeout_seconds > 0 and duration > step.timeout_seconds:
                temp_ok = False
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.TEMPORAL_CONSISTENCY,
                verified=temp_ok,
                confidence=0.90 if temp_ok else 0.35,
                details={"duration_seconds": round(duration, 2)},
            )
        )

        # 14. ACTIVITY_CONFIRMED
        act_confirmed = activity is not None and activity.status in (ActivityStatus.CONFIRMED, ActivityStatus.IN_PROGRESS)
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.ACTIVITY_CONFIRMED,
                verified=act_confirmed,
                confidence=activity.confidence if activity else 0.5,
            )
        )

        # 15. PROCEDURE_MATCH
        proc_match = False
        proc_conf = 0.0
        if step and activity:
            action_match = activity.activity_name in step.expected_actions or any(
                p in step.expected_actions for p in activity.primitives
            )
            object_match = (
                (not step.expected_objects)
                or (activity.target_object_id in step.expected_objects)
                or (target_obj in step.expected_objects)
            )
            proc_match = action_match and object_match
            proc_conf = 0.95 if proc_match else (0.40 if action_match else 0.10)
        bundle.add_item(
            EvidenceItem(
                evidence_type=EvidenceType.PROCEDURE_MATCH,
                verified=proc_match,
                confidence=proc_conf,
            )
        )

        # Evaluate against Step Requirements
        if step:
            self._evaluate_step_compliance(bundle, step)
        else:
            bundle.required_satisfied = True
            bundle.evidence_score = float(np.mean([item.confidence for item in bundle.items.values()]))
            bundle.is_conclusive = bundle.evidence_score >= 0.70

        return bundle

    def _evaluate_step_compliance(self, bundle: EvidenceBundle, step: ExperimentStep) -> None:
        """Evaluate bundle against step's required, optional, and alternate evidence groups."""
        from core.evidence.types import normalize_evidence_name

        missing: List[str] = []

        # 1. Standard required evidence list (normalized)
        for req in step.required_evidence:
            canonical_req = normalize_evidence_name(req)
            if not bundle.check_requirement(canonical_req):
                missing.append(canonical_req)

        # 2. Structured alternate paths (ALL_OF, ANY_OF, ONE_OF)
        if step.evidence_paths:
            path_satisfied = self._evaluate_evidence_path(bundle, step.evidence_paths)
            if not path_satisfied:
                missing.append("EVIDENCE_PATHS_UNSATISFIED")

        bundle.missing_required = missing
        bundle.required_satisfied = len(missing) == 0

        # Evaluate optional evidence
        optional_passed = sum(1 for opt in step.optional_evidence if bundle.check_requirement(normalize_evidence_name(opt)))
        bundle.optional_satisfied = (
            optional_passed == len(step.optional_evidence) if step.optional_evidence else True
        )

        # Compute deterministic composite evidence score
        req_ratio = 1.0 - (len(missing) / max(1, len(step.required_evidence)))
        mean_conf = float(np.mean([it.confidence for it in bundle.items.values()])) if bundle.items else 0.5
        temp_item = bundle.items.get(EvidenceType.TEMPORAL_CONSISTENCY.value)
        temp_score = temp_item.confidence if temp_item and temp_item.verified else 0.3
        proc_item = bundle.items.get(EvidenceType.PROCEDURE_MATCH.value)
        proc_score = proc_item.confidence if proc_item and proc_item.verified else 0.3

        composite_score = (
            self.WEIGHT_REQUIRED * req_ratio
            + self.WEIGHT_CONFIDENCE * mean_conf
            + self.WEIGHT_TEMPORAL * temp_score
            + self.WEIGHT_PROCEDURE * proc_score
        )
        bundle.evidence_score = round(float(np.clip(composite_score, 0.0, 1.0)), 3)
        bundle.confidence = bundle.evidence_score
        bundle.is_conclusive = bundle.required_satisfied and bundle.evidence_score >= step.min_confidence

    def _evaluate_evidence_path(self, bundle: EvidenceBundle, rule: EvidencePathRule) -> bool:
        """Evaluate structured alternate evidence groupings."""
        from core.evidence.types import normalize_evidence_name

        if rule.all_of:
            if not all(bundle.check_requirement(normalize_evidence_name(r)) for r in rule.all_of):
                return False

        if rule.any_of:
            group_matched = False
            for group in rule.any_of:
                if all(bundle.check_requirement(normalize_evidence_name(r)) for r in group):
                    group_matched = True
                    break
            if not group_matched:
                return False

        if rule.one_of:
            count = sum(1 for r in rule.one_of if bundle.check_requirement(normalize_evidence_name(r)))
            if count != 1:
                return False

        return True

    def evaluate_evidence_paths(self, bundle: EvidenceBundle, rule: EvidencePathRule) -> Tuple[bool, List[str]]:
        """Public evaluator for structured alternate evidence groupings."""
        satisfied = self._evaluate_evidence_path(bundle, rule)
        missing: List[str] = []
        if not satisfied:
            if rule.all_of:
                missing.extend([r for r in rule.all_of if not bundle.check_requirement(r)])
            elif rule.any_of:
                missing.append("ANY_OF_FAILED")
            elif rule.one_of:
                missing.append("ONE_OF_FAILED")
        return satisfied, missing
