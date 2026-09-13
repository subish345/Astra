# ==============================================================================
# ASTRA-EA Camera-Angle Viewpoint Invariance & Robustness Matrix
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Automated validation of camera viewpoint invariance and deviation robustness.

Validates that procedural understanding, activity semantics, assurance decisions,
and recovery mechanics remain invariant when the camera moves between VIEW_LEFT
and VIEW_RIGHT.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Dict, List

from core.activity.types import ActivityObservation, TemporalWindow
from core.assistance.recovery import ClosedLoopRecoveryManager, RecoveryState
from core.assurance.engine import TriStateAssuranceEngine
from core.assurance.types import AssuranceDecision, DecisionType
from core.camera.profile import CameraProfile, get_camera_profile
from core.common.config import get_project_root
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.mission.events import DeviationReason
from core.perception.spatial import SpatialGeometry, ground_hand_anatomical
from core.perception.types import BoundingBox, HandObservation, HandType, Keypoint, PoseObservation
from core.procedure.validator import load_procedure_file


@pytest.fixture
def procedure():
    root = get_project_root()
    return load_procedure_file(root / "configs" / "experiments" / "demo.yaml")


@pytest.fixture
def assurance_engine():
    return TriStateAssuranceEngine()


@pytest.fixture
def recovery_manager():
    return ClosedLoopRecoveryManager()


def create_mock_bundle(
    step_id: str,
    required_satisfied: bool = True,
    evidence_score: float = 0.95,
    occluded: bool = False,
) -> EvidenceBundle:
    """Helper to build synthetic multimodal evidence bundles."""
    items: Dict[str, EvidenceItem] = {}
    if required_satisfied:
        items["EVD_ACTOR"] = EvidenceItem(evidence_type=EvidenceType.ACTOR_DETECTED, verified=True, confidence=0.95)
        items["EVD_OBJECT"] = EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.92)
        items["EVD_CONTACT"] = EvidenceItem(evidence_type=EvidenceType.HAND_OBJECT_CONTACT, verified=True, confidence=0.90)

    metadata = {"occluded": True} if occluded else {}
    return EvidenceBundle(
        bundle_id=f"BND_{step_id}",
        step_id=step_id,
        items=items,
        required_satisfied=required_satisfied,
        evidence_score=evidence_score if required_satisfied else (0.45 if occluded else 0.20),
        confidence=evidence_score if required_satisfied else (0.45 if occluded else 0.20),
        metadata=metadata,
    )


# ==============================================================================
# 8-SCENARIO VALIDATION MATRIX (Prompt Sections 11 & 12)
# ==============================================================================

class TestCameraViewpointMatrix:
    """Test suite executing the 8 required camera-angle scenarios."""

    # --------------------------------------------------------------------------
    # Scenario 1 & 2: CORRECT RUNS (VIEW_LEFT vs VIEW_RIGHT)
    # --------------------------------------------------------------------------
    def test_scenario_1_view_left_correct(self, procedure, assurance_engine):
        """Scenario 1: Complete correct experiment procedure observed from VIEW_LEFT."""
        cam_profile = get_camera_profile("VIEW_LEFT")
        assert cam_profile.id == "VIEW_LEFT"

        completed = set()
        for step in procedure.steps:
            act = ActivityObservation(
                activity_name=step.expected_actions[0],
                actor="astronaut",
                target_object_id=step.expected_objects[0],
                confidence=0.92,
                window=TemporalWindow(start_time=1.0, end_time=3.0),
            )
            bundle = create_mock_bundle(step.id, required_satisfied=True, evidence_score=0.95)

            decision = assurance_engine.evaluate_step(
                current_step=step,
                activity=act,
                evidence=bundle,
                camera_profile=cam_profile,
                procedure=procedure,
                completed_step_ids=completed,
            )
            assert decision.is_verified, f"Step {step.id} failed verification from VIEW_LEFT"
            assert decision.decision == DecisionType.VERIFIED
            assert decision.camera_profile == "VIEW_LEFT"
            completed.add(step.id)

        assert len(completed) == 4

    def test_scenario_2_view_right_correct(self, procedure, assurance_engine):
        """Scenario 2: Complete correct experiment procedure observed from VIEW_RIGHT."""
        cam_profile = get_camera_profile("VIEW_RIGHT")
        assert cam_profile.id == "VIEW_RIGHT"

        completed = set()
        for step in procedure.steps:
            act = ActivityObservation(
                activity_name=step.expected_actions[0],
                actor="astronaut",
                target_object_id=step.expected_objects[0],
                confidence=0.92,
                window=TemporalWindow(start_time=1.0, end_time=3.0),
            )
            bundle = create_mock_bundle(step.id, required_satisfied=True, evidence_score=0.95)

            decision = assurance_engine.evaluate_step(
                current_step=step,
                activity=act,
                evidence=bundle,
                camera_profile=cam_profile,
                procedure=procedure,
                completed_step_ids=completed,
            )
            assert decision.is_verified, f"Step {step.id} failed verification from VIEW_RIGHT"
            assert decision.decision == DecisionType.VERIFIED
            assert decision.camera_profile == "VIEW_RIGHT"
            completed.add(step.id)

        assert len(completed) == 4

    # --------------------------------------------------------------------------
    # Scenario 3 & 4: WRONG OBJECT DEVIATION (VIEW_LEFT vs VIEW_RIGHT)
    # --------------------------------------------------------------------------
    def test_scenario_3_view_left_wrong_object(self, procedure, assurance_engine):
        """Scenario 3: Interacting with YELLOW_BOX instead of RED_BOX from VIEW_LEFT."""
        cam_profile = get_camera_profile("VIEW_LEFT")
        step_2 = procedure.steps[1]  # STEP_02: Acquire Red Box (expected: RED_BOX)
        assert "RED_BOX" in step_2.expected_objects

        act = ActivityObservation(
            activity_name="GRASP",
            actor="astronaut",
            target_object_id="YELLOW_BOX",  # WRONG OBJECT
            confidence=0.91,
            window=TemporalWindow(start_time=1.0, end_time=2.5),
        )
        bundle = create_mock_bundle(step_2.id, required_satisfied=True)

        decision = assurance_engine.evaluate_step(
            current_step=step_2,
            activity=act,
            evidence=bundle,
            camera_profile=cam_profile,
            procedure=procedure,
        )
        assert decision.is_deviation
        assert decision.decision == DecisionType.DEVIATION
        assert decision.deviation_reason == DeviationReason.WRONG_OBJECT
        assert "YELLOW_BOX" in decision.reason
        assert decision.recommended_recovery is not None

    def test_scenario_4_view_right_wrong_object(self, procedure, assurance_engine):
        """Scenario 4: Interacting with YELLOW_BOX instead of RED_BOX from VIEW_RIGHT."""
        cam_profile = get_camera_profile("VIEW_RIGHT")
        step_2 = procedure.steps[1]  # STEP_02: Acquire Red Box
        assert "RED_BOX" in step_2.expected_objects

        act = ActivityObservation(
            activity_name="GRASP",
            actor="astronaut",
            target_object_id="YELLOW_BOX",  # WRONG OBJECT
            confidence=0.91,
            window=TemporalWindow(start_time=1.0, end_time=2.5),
        )
        bundle = create_mock_bundle(step_2.id, required_satisfied=True)

        decision = assurance_engine.evaluate_step(
            current_step=step_2,
            activity=act,
            evidence=bundle,
            camera_profile=cam_profile,
            procedure=procedure,
        )
        assert decision.is_deviation
        assert decision.decision == DecisionType.DEVIATION
        assert decision.deviation_reason == DeviationReason.WRONG_OBJECT
        assert "YELLOW_BOX" in decision.reason
        assert decision.recommended_recovery is not None

    # --------------------------------------------------------------------------
    # Scenario 5 & 6: SKIPPED STEP DEVIATION (VIEW_LEFT vs VIEW_RIGHT)
    # --------------------------------------------------------------------------
    def test_scenario_5_view_left_skipped_step(self, procedure, assurance_engine):
        """Scenario 5: Attempting STEP_03 (MOVE) before STEP_01/STEP_02 completed from VIEW_LEFT."""
        cam_profile = get_camera_profile("VIEW_LEFT")
        current_step = procedure.steps[0]  # Currently on STEP_01
        completed = set()  # Neither STEP_01 nor STEP_02 is completed

        # Premature MOVE action corresponding to STEP_03
        act = ActivityObservation(
            activity_name="MOVE",
            actor="astronaut",
            target_object_id="RED_BOX",
            confidence=0.89,
            window=TemporalWindow(start_time=1.0, end_time=2.5),
        )
        bundle = create_mock_bundle(current_step.id, required_satisfied=False)

        decision = assurance_engine.evaluate_step(
            current_step=current_step,
            activity=act,
            evidence=bundle,
            camera_profile=cam_profile,
            procedure=procedure,
            completed_step_ids=completed,
        )
        assert decision.is_deviation
        assert decision.deviation_reason == DeviationReason.SKIPPED_STEP

    def test_scenario_6_view_right_skipped_step(self, procedure, assurance_engine):
        """Scenario 6: Attempting STEP_03 (MOVE) before STEP_01/STEP_02 completed from VIEW_RIGHT."""
        cam_profile = get_camera_profile("VIEW_RIGHT")
        current_step = procedure.steps[0]  # Currently on STEP_01
        completed = set()

        act = ActivityObservation(
            activity_name="MOVE",
            actor="astronaut",
            target_object_id="RED_BOX",
            confidence=0.89,
            window=TemporalWindow(start_time=1.0, end_time=2.5),
        )
        bundle = create_mock_bundle(current_step.id, required_satisfied=False)

        decision = assurance_engine.evaluate_step(
            current_step=current_step,
            activity=act,
            evidence=bundle,
            camera_profile=cam_profile,
            procedure=procedure,
            completed_step_ids=completed,
        )
        assert decision.is_deviation
        assert decision.deviation_reason == DeviationReason.SKIPPED_STEP

    # --------------------------------------------------------------------------
    # Scenario 7 & 8: VIEWPOINT-INDUCED UNCERTAINTY (VIEW_LEFT vs VIEW_RIGHT)
    # --------------------------------------------------------------------------
    def test_scenario_7_view_left_uncertain(self, procedure, assurance_engine):
        """Scenario 7: Camera occlusion from VIEW_LEFT produces UNCERTAIN, never false DEVIATION."""
        cam_profile = get_camera_profile("VIEW_LEFT")
        step_2 = procedure.steps[1]

        act = ActivityObservation(
            activity_name="GRASP",
            actor="astronaut",
            target_object_id="RED_BOX",
            confidence=0.48,  # Reduced visibility
            window=TemporalWindow(start_time=1.0, end_time=2.0),
        )
        bundle = create_mock_bundle(step_2.id, required_satisfied=False, occluded=True)

        decision = assurance_engine.evaluate_step(
            current_step=step_2,
            activity=act,
            evidence=bundle,
            camera_profile=cam_profile,
            procedure=procedure,
        )
        # CRITICAL PRINCIPLE (Prompt §15): Reduced visibility must NEVER trigger a false deviation!
        assert decision.is_uncertain
        assert not decision.is_deviation
        assert decision.decision == DecisionType.UNCERTAIN

    def test_scenario_8_view_right_uncertain(self, procedure, assurance_engine):
        """Scenario 8: Camera occlusion from VIEW_RIGHT produces UNCERTAIN, never false DEVIATION."""
        cam_profile = get_camera_profile("VIEW_RIGHT")
        step_2 = procedure.steps[1]

        act = ActivityObservation(
            activity_name="GRASP",
            actor="astronaut",
            target_object_id="RED_BOX",
            confidence=0.48,  # Reduced visibility
            window=TemporalWindow(start_time=1.0, end_time=2.0),
        )
        bundle = create_mock_bundle(step_2.id, required_satisfied=False, occluded=True)

        decision = assurance_engine.evaluate_step(
            current_step=step_2,
            activity=act,
            evidence=bundle,
            camera_profile=cam_profile,
            procedure=procedure,
        )
        # CRITICAL PRINCIPLE (Prompt §15): Reduced visibility must NEVER trigger a false deviation!
        assert decision.is_uncertain
        assert not decision.is_deviation
        assert decision.decision == DecisionType.UNCERTAIN


# ==============================================================================
# CROSS-VIEW SEMANTIC CONSISTENCY METRICS (Prompt Sections 14 & 19)
# ==============================================================================

class TestCrossViewConsistency:
    """Validates cross-view semantic consistency across equivalent physical inputs."""

    def test_semantic_invariance_across_viewpoints(self, procedure, assurance_engine):
        """Equivalent physical actions across viewpoints produce 100% decision consistency."""
        profile_left = get_camera_profile("VIEW_LEFT")
        profile_right = get_camera_profile("VIEW_RIGHT")

        decisions_left: List[str] = []
        decisions_right: List[str] = []

        # Run 4 test conditions on both viewpoints:
        # 1. Correct Step 1
        # 2. Correct Step 2
        # 3. Wrong Object on Step 2
        # 4. Partial Occlusion on Step 2
        test_cases = [
            (procedure.steps[0], "APPROACH_DESTINATION", "MAIN_BOX", True, False),
            (procedure.steps[1], "GRASP", "RED_BOX", True, False),
            (procedure.steps[1], "GRASP", "YELLOW_BOX", True, False),  # Wrong object
            (procedure.steps[1], "GRASP", "RED_BOX", False, True),     # Occluded
        ]

        for step, act_name, obj_id, req_sat, is_occ in test_cases:
            act = ActivityObservation(
                activity_name=act_name,
                actor="astronaut",
                target_object_id=obj_id,
                confidence=0.48 if is_occ else 0.92,
                window=TemporalWindow(start_time=1.0, end_time=2.0),
            )
            bundle = create_mock_bundle(step.id, required_satisfied=req_sat, occluded=is_occ)

            dec_l = assurance_engine.evaluate_step(step, act, bundle, camera_profile=profile_left, procedure=procedure)
            dec_r = assurance_engine.evaluate_step(step, act, bundle, camera_profile=profile_right, procedure=procedure)

            decisions_left.append(dec_l.decision.value)
            decisions_right.append(dec_r.decision.value)

            # Assert identical semantic decision for equivalent physical action
            assert dec_l.decision == dec_r.decision
            if dec_l.is_deviation:
                assert dec_l.deviation_reason == dec_r.deviation_reason

        # Calculate consistency metric
        matches = sum(1 for l, r in zip(decisions_left, decisions_right) if l == r)
        consistency_pct = (matches / len(decisions_left)) * 100.0
        assert consistency_pct == 100.0, f"Cross-view consistency {consistency_pct}% < 100%"


# ==============================================================================
# CLOSED-LOOP RECOVERY STATE MACHINE TESTS
# ==============================================================================

class TestClosedLoopRecoveryStateMachine:
    """Validates the DETECT -> EXPLAIN -> RECOMMEND -> OBSERVE -> VERIFY -> RESUME loop."""

    def test_recovery_lifecycle_wrong_object(self, procedure, assurance_engine, recovery_manager):
        step_2 = procedure.steps[1]
        act_wrong = ActivityObservation(
            activity_name="GRASP",
            actor="astronaut",
            target_object_id="YELLOW_BOX",
            confidence=0.91,
            window=TemporalWindow(start_time=1.0, end_time=2.0),
        )
        bundle = create_mock_bundle(step_2.id, required_satisfied=True)
        decision = assurance_engine.evaluate_step(step_2, act_wrong, bundle, procedure=procedure)

        assert decision.is_deviation

        # 1. State machine handles decision -> transitions through DETECTED, EXPLAINING, RECOMMENDING -> enters OBSERVING
        messages = recovery_manager.handle_decision(decision, step_2)
        assert len(messages) >= 2
        assert recovery_manager.current_state == RecoveryState.OBSERVING
        assert recovery_manager.is_recovering

        # 2. In OBSERVING: Astronaut takes corrective action by releasing wrong object
        act_corrective = ActivityObservation(
            activity_name="RELEASE",
            actor="astronaut",
            target_object_id="YELLOW_BOX",
            confidence=0.88,
            window=TemporalWindow(start_time=2.1, end_time=3.0),
        )
        bundle_corr = create_mock_bundle(step_2.id, required_satisfied=False)

        recovered, completion_msg = recovery_manager.observe_corrective_action(act_corrective, bundle_corr, step_2)
        assert recovered is True
        assert completion_msg is not None
        assert recovery_manager.current_state == RecoveryState.RECOVERY_VERIFIED

        # 3. Astronaut now executes correct step action -> VERIFIED -> RESUMED -> IDLE
        recovery_manager.complete_recovery()
        assert recovery_manager.current_state == RecoveryState.IDLE
        assert not recovery_manager.is_recovering


# ==============================================================================
# ANATOMICAL HAND GROUNDING INVARIANCE TESTS (Prompt Section 6)
# ==============================================================================

class TestAnatomicalHandGrounding:
    """Validates that astronaut anatomical handedness is preserved without image-space confusion."""

    def test_anatomical_hand_preservation(self):
        # Astronaut body pose with clear left and right wrist landmarks
        pose = PoseObservation(
            person_id=1,
            keypoints=[
                Keypoint(x=0.30, y=0.50, confidence=0.90, name="left_wrist"),
                Keypoint(x=0.70, y=0.50, confidence=0.90, name="right_wrist"),
                Keypoint(x=0.50, y=0.30, confidence=0.95, name="nose"),
            ],
            confidence=0.92,
        )

        # Hand observation positioned close to anatomical right wrist (x=0.69, y=0.51)
        hand_right = HandObservation(
            hand_type=HandType.UNKNOWN,
            keypoints=[],
            confidence=0.85,
            wrist=(0.69, 0.51),
        )

        # Hand observation positioned close to anatomical left wrist (x=0.31, y=0.49)
        hand_left = HandObservation(
            hand_type=HandType.UNKNOWN,
            keypoints=[],
            confidence=0.85,
            wrist=(0.31, 0.49),
        )

        grounded_r = ground_hand_anatomical(hand_right, [pose])
        grounded_l = ground_hand_anatomical(hand_left, [pose])

        assert grounded_r == HandType.RIGHT
        assert grounded_l == HandType.LEFT

    def test_ambiguous_hand_returns_unknown_without_fabrication(self):
        """When landmarks are absent or ambiguous, returns UNKNOWN without guessing."""
        hand_ambiguous = HandObservation(
            hand_type=HandType.UNKNOWN,
            keypoints=[],
            confidence=0.70,
            wrist=(0.50, 0.50),
        )

        # Pose without wrist landmarks
        pose_no_wrists = PoseObservation(
            person_id=1,
            keypoints=[
                Keypoint(x=0.50, y=0.20, confidence=0.80, name="nose"),
            ],
            confidence=0.80,
        )

        result = ground_hand_anatomical(hand_ambiguous, [pose_no_wrists])
        # MUST return UNKNOWN, never fabricate based on frame x coordinate!
        assert result == HandType.UNKNOWN
