from core.activity.live_observer import LiveObserver
from core.common.config import get_project_root
from core.perception.types import BoundingBox, Detection, HandObservation, HandType, PerceptionState
from core.procedure.validator import load_procedure_file


def state(timestamp=1, x=100, objects=None):
    return PerceptionState(timestamp=timestamp, frame_id=1, source_id="test", frame_width=640, frame_height=480,
        hands=[HandObservation(HandType.LEFT, [], 0.9, (x, 100))], objects=objects or [])


def test_live_observe_name_and_no_steps():
    procedure = load_procedure_file(get_project_root() / "configs/experiments/always_observe.yaml")
    assert procedure.experiment.name == "Live Observe"
    assert procedure.continuous_observation
    assert not procedure.steps


def test_phone_near_hand_not_confirmed_grip():
    phone = Detection("cell phone", 0.9, BoundingBox(90, 90, 120, 120))
    text = LiveObserver().describe(state(objects=[phone]))
    assert "cell phone" in text
    assert "grip unverified" in text


def test_distant_object_not_in_hand():
    phone = Detection("cell phone", 0.9, BoundingBox(400, 300, 450, 350))
    assert "cell phone" not in LiveObserver().describe(state(objects=[phone]))


def test_motion_and_visibility_loss():
    observer = LiveObserver()
    observer.describe(state())
    assert "moving" in observer.describe(state(1.2, 150))
    assert "No person" in observer.describe(PerceptionState(2, 2, "test"))
    assert "moving" not in observer.describe(state(2.1, 200))


def test_phone_label_clears_when_detection_disappears():
    observer = LiveObserver()
    phone = Detection("cell phone", 0.9, BoundingBox(90, 90, 120, 120))
    assert "cell phone" in observer.describe(state(objects=[phone]))
    assert "cell phone" not in observer.describe(state(1.2))


def test_low_confidence_object_is_not_named():
    phone = Detection("cell phone", 0.2, BoundingBox(90, 90, 120, 120))
    assert "cell phone" not in LiveObserver().describe(state(objects=[phone]))
