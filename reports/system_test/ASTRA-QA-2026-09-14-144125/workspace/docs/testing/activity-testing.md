# Temporal Activity Testing Guide (Phase 3)

## 1. Overview
The Activity recognition test suite verifies sliding temporal window retention, kinematic feature extraction, primitive action classification, composite event synthesis, explainable confidence scoring, and event deduplication.

---

## 2. Test Matrix

| Test Module | Test Case | Purpose |
| :--- | :--- | :--- |
| `test_temporal_buffer.py` | `test_temporal_buffer_rolling_and_expiration` | Verifies rolling capacity and time-based eviction |
| `test_temporal_buffer.py` | `test_temporal_feature_extraction` | Verifies velocity, acceleration, and contact duration derivation |
| `test_primitive.py` | `test_classify_approach` | Verifies primitive APPROACH classification |
| `test_primitive.py` | `test_classify_lift_vs_move` | Verifies differentiation of vertical LIFT from horizontal MOVE |
| `test_primitive.py` | `test_classify_touch_and_hold` | Verifies classification of TOUCH and sustained HOLD |
| `test_composite.py` | `test_pickup_composition` | Verifies synthesis of PICKUP from `APPROACH + GRASP + LIFT` |
| `test_composite.py` | `test_move_object_composition` | Verifies synthesis of MOVE_OBJECT from `HOLD + MOVE` |
| `test_composite.py` | `test_place_object_composition` | Verifies synthesis of PLACE_OBJECT from `MOVE + PLACE + RELEASE` |
| `test_confidence.py` | `test_confidence_calculation_and_tier_mapping` | Verifies weighted multi-factor formula and qualitative tiers |
| `test_confidence.py` | `test_uncertainty_resolution_on_track_loss` | Verifies UNCERTAIN status assignment |
| `test_confidence.py` | `test_in_progress_resolution_on_short_duration` | Verifies IN_PROGRESS status prior to minimum duration |
| `test_events.py` | `test_interaction_deduplication` | Verifies prevention of per-frame interaction event flooding |
| `test_events.py` | `test_activity_lifecycle_deduplication` | Verifies STARTED -> CONFIRMED -> ENDED lifecycle emission |
| `test_phase3_pipeline.py` | `test_end_to_end_phase3_pipeline_integration` | Full pipeline integration from synthetic frames to annotations |

---

## 3. Running Activity Tests
Execute via pytest:
```bash
pytest tests/activity/ tests/temporal/ tests/integration/test_phase3_pipeline.py -v
```

Execute live monitor or benchmark via CLI:
```bash
# Live webcam test
python3 main.py activity test --source 0

# Benchmark mode without display
python3 main.py activity test --source 0 --frames 100 --benchmark --no-display
```
