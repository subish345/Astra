# Activity Subsystem Development & Extension Guide

## 1. Subsystem Philosophy
ASTRA-EA physical activity recognition is strictly decoupled from experiment procedure logic:
- **Phase 3 (This Subsystem):** Understands physical actions (e.g. "Astronaut picked up RED_BOX").
- **Phase 4 (Procedure Assurance):** Decides whether that action was expected at the current experiment step.

Never hard-code experiment step identifiers (e.g. "STEP_01", "ASSURANCE_VERIFIED") inside `core/interaction/` or `core/activity/`.

---

## 2. Adding a New Primitive Activity

1. **Register the enum value** in `core/activity/types.py`:
   ```python
   class PrimitiveActivityType(str, Enum):
       ...
       INSPECT = "INSPECT"
   ```
2. **Define classification rule** in `core/activity/primitive.py`:
   Inspect `features` (e.g. stationary object held near face or torso for $> 2.0$ seconds).
3. **Add unit test** in `tests/activity/test_primitive.py`.

---

## 3. Adding a New Composite Activity

1. **Register the enum value** in `core/activity/types.py`:
   ```python
   class CompositeActivityType(str, Enum):
       ...
       INSPECT_OBJECT = "INSPECT_OBJECT"
   ```
2. **Define sequence rule** in `core/activity/composite.py`:
   ```python
   def _matches_inspect(self, seq: List[str]) -> bool:
       return seq and seq[-1] == "INSPECT" and "HOLD" in seq[:-1]
   ```
3. **Add unit test** in `tests/activity/test_composite.py`.

---

## 4. Exporting Annotations for Phase 7 Dataset Studio

Activity episodes can be serialized using `core/activity/annotation.py`:
```python
from core.activity.annotation import ActivityAnnotation, export_annotations_json

ann = ActivityAnnotation.from_observation(
    comp_obs,
    video_id="SESSION_001",
    start_frame=421,
    end_frame=498,
    annotation_source="auto_pipeline",
)
export_annotations_json([ann], "storage/datasets/annotations.json")
```
This data structure forms the bridge to Phase 7 synthetic dataset generation and model fine-tuning.
