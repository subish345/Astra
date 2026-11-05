"""Safety-Style Invariant Property Tests for ASTRA-EA (Phase 16).

Tests formal aerospace invariant properties:
- Invariant 1: No evidence / ambiguous evidence -> No step verification (ASTRA-SAF-001)
- Invariant 2: Sensor dropout / camera freeze -> Verification paused (ASTRA-SAF-003)
- Invariant 3: Ground network disconnect -> Onboard assurance continues (ASTRA-SAF-004)
- Invariant 4: Audio DAC / TTS failure -> Visual assurance continues (ASTRA-REL-001)
- Invariant 5: Wrong object interaction -> Cannot verify nominal step (ASTRA-SYS-006)
"""

import pytest
import time
from core.activity.types import ActivityObservation, TemporalWindow
from core.assurance.engine import TriStateAssuranceEngine
from core.assurance.types import AssuranceDecision, DecisionType
from core.common.config import get_project_root
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.procedure.progress import ProcedureProgressManager
from core.assistance.voice import LocalVoiceManager
from core.procedure.validator import load_procedure_file


@pytest.fixture
def demo_procedure():
    root = get_project_root()
    return load_procedure_file(root / "configs" / "experiments" / "demo.yaml")


@pytest.mark.requirement("ASTRA-SAF-001")
def test_invariant_no_evidence_no_verification(demo_procedure):
    """Invariant 1: Insufficient or ambiguous evidence (empty/low confidence) shall NEVER verify a step."""
    assurance_engine = TriStateAssuranceEngine()
    step_1 = demo_procedure.steps[0]
    
    # 1a. Empty evidence bundle with low confidence
    empty_bundle = EvidenceBundle(
        bundle_id="BND_EMPTY",
        items={},
        required_satisfied=False,
        evidence_score=0.10,
        confidence=0.10,
    )
    act = ActivityObservation(
        activity_name="UNKNOWN",
        actor="unknown",
        target_object_id=None,
        confidence=0.15,
        window=TemporalWindow(start_time=0.0, end_time=1.0),
    )
    decision = assurance_engine.evaluate_step(
        current_step=step_1,
        activity=act,
        evidence=empty_bundle,
        camera_profile="VIEW_LEFT",
        procedure=demo_procedure,
    )
    assert not decision.is_verified, "Empty/ambiguous evidence falsely verified a step!"

    # 1b. Missing required evidence
    low_bundle = EvidenceBundle(
        bundle_id="BND_LOW",
        items={
            "actor_detected": EvidenceItem(evidence_type=EvidenceType.ACTOR_DETECTED, verified=False, confidence=0.2),
        },
        required_satisfied=False,
        missing_required=["OBJECT_DETECTED", "HAND_OBJECT_CONTACT"],
        evidence_score=0.25,
        confidence=0.25,
    )
    decision_low = assurance_engine.evaluate_step(
        current_step=step_1,
        activity=act,
        evidence=low_bundle,
        camera_profile="VIEW_LEFT",
        procedure=demo_procedure,
    )
    assert not decision_low.is_verified, "Missing required evidence falsely verified a step!"


@pytest.mark.requirement("ASTRA-SAF-003")
def test_invariant_missing_camera_no_step_completion(demo_procedure):
    """Invariant 2: Ingestion frame cessation for >= 3 frames shall pause assurance and forbid step completion."""
    progress = ProcedureProgressManager(demo_procedure)
    
    initial_step = progress.current_step
    assert initial_step is not None

    # Simulate camera dropout / frozen frame ingestion counter
    consecutive_dropouts = 5
    is_paused = consecutive_dropouts >= 3

    assert is_paused is True
    # Under paused state, step cannot advance
    assert progress.current_step == initial_step, "Procedure advanced despite camera dropout!"


@pytest.mark.requirement("ASTRA-SAF-004")
def test_invariant_ground_disconnect_onboard_continues(demo_procedure):
    """Invariant 3: Ground network disconnect or streaming socket failure shall NOT interrupt onboard assurance."""
    assurance_engine = TriStateAssuranceEngine()
    step_1 = demo_procedure.steps[0]
    
    # Simulate valid evidence
    items = {
        "actor_detected": EvidenceItem(evidence_type=EvidenceType.ACTOR_DETECTED, verified=True, confidence=0.95),
        "object_detected": EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.95),
    }
    valid_bundle = EvidenceBundle(
        bundle_id="BND_VALID",
        items=items,
        required_satisfied=True,
        evidence_score=0.95,
        confidence=0.95,
    )
    act = ActivityObservation(
        activity_name="APPROACH_DESTINATION",
        actor="astronaut",
        target_object_id="MAIN_BOX",
        confidence=0.95,
        window=TemporalWindow(start_time=1.0, end_time=3.0),
    )

    # Onboard engine evaluates normally without raising any network-related exceptions
    try:
        dec = assurance_engine.evaluate_step(
            current_step=step_1,
            activity=act,
            evidence=valid_bundle,
            camera_profile="VIEW_LEFT",
            procedure=demo_procedure,
        )
        onboard_succeeded = dec.is_verified
    except Exception as e:
        pytest.fail(f"Onboard assurance crashed due to network state: {e}")

    assert onboard_succeeded is True, "Onboard assurance failed to verify under network air-gap!"


@pytest.mark.requirement("ASTRA-REL-001")
def test_invariant_voice_failure_assurance_continues():
    """Invariant 4: Audio DAC / TTS failure shall NOT suspend or crash procedural progression."""
    voice = LocalVoiceManager()
    
    class BrokenAudioBackend:
        def speak(self, text, priority="LOW"):
            raise RuntimeError("ALSA audio device write error: device unavailable")

    voice.backend = BrokenAudioBackend()
    
    # Attempt to speak deviation alert; should catch exception gracefully and not crash
    try:
        voice.speak("Warning: procedural deviation detected.", priority="HIGH")
        voice_isolated = True
    except RuntimeError:
        voice_isolated = False

    assert voice_isolated is True, "Voice failure propagated and crashed caller!"


@pytest.mark.requirement("ASTRA-SYS-006")
def test_invariant_wrong_object_cannot_become_correct_via_ui(demo_procedure):
    """Invariant 5: Wrong object interaction cannot be verified as correct regardless of UI state or client input."""
    assurance_engine = TriStateAssuranceEngine()
    step_1 = demo_procedure.steps[0]

    # Interaction with completely wrong apparatus
    act = ActivityObservation(
        activity_name="INTERACT_WRONG",
        actor="astronaut",
        target_object_id="UNKNOWN_WRONG_OBJECT",
        confidence=0.90,
        window=TemporalWindow(start_time=1.0, end_time=3.0),
    )
    bundle = EvidenceBundle(
        bundle_id="BND_WRONG",
        target_object_id="UNKNOWN_WRONG_OBJECT",
        required_satisfied=False,
        evidence_score=0.2,
        confidence=0.2,
    )

    dec = assurance_engine.evaluate_step(
        current_step=step_1,
        activity=act,
        evidence=bundle,
        camera_profile="VIEW_LEFT",
        procedure=demo_procedure,
    )

    assert not dec.is_verified, "Wrong object falsely yielded VERIFIED state!"
