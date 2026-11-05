# Physical Interaction Testing Guide (Phase 3)

## 1. Overview
The Interaction test suite validates mathematical correctness, state machine stability, hysteresis, and edge-case handling using synthetic deterministic streams.

---

## 2. Test Matrix

| Test Module | Test Case | Purpose |
| :--- | :--- | :--- |
| `test_geometry.py` | `test_calculate_pixel_and_normalized_distance` | Verifies Euclidean and resolution-invariant normalization |
| `test_geometry.py` | `test_calculate_box_overlap_iou` | Verifies IoU intersection and union math |
| `test_geometry.py` | `test_determine_relative_position` | Verifies directional bearing (INSIDE, ABOVE, etc.) |
| `test_geometry.py` | `test_compute_velocity_vector` | Verifies time-differenced derivative calculations |
| `test_geometry.py` | `test_compute_motion_correlation` | Verifies cosine similarity bounds in $[-1.0, 1.0]$ |
| `test_rules.py` | `test_approach_evaluation` | Verifies distance and approach speed criteria |
| `test_rules.py` | `test_near_evaluation` | Verifies near-proximity window separation from contact |
| `test_rules.py` | `test_contact_evaluation_persistence` | Verifies confirmation frames hysteresis |
| `test_rules.py` | `test_coupled_motion_evaluation` | Verifies coupled trajectory requirements |
| `test_rules.py` | `test_object_moved_alone_negative_condition` | Verifies rejection of independent object motion (Test B) |
| `test_state_machine.py` | `test_state_machine_approach_to_contact_progression` | Verifies multi-stage state transitions |
| `test_state_machine.py` | `test_state_machine_track_loss_handling` | Verifies uncertainty flag during temporary occlusion |
| `test_scenarios.py` | `test_scenario_correct_grasp_progression` | End-to-end positive grasp and lift scenario |
| `test_scenarios.py` | `test_negative_scenario_a_false_near_object` | Negative Test A: hand hovers near object without contact |
| `test_scenarios.py` | `test_negative_scenario_b_object_moves_alone` | Negative Test B: object moves alone without hand contact |
| `test_scenarios.py` | `test_negative_scenario_c_contact_no_move` | Negative Test C: steady contact without object translation |
| `test_scenarios.py` | `test_negative_scenario_d_occlusion_handling` | Negative Test D: temporary track occlusion resilience |

---

## 3. Running Interaction Tests
Execute via pytest:
```bash
pytest tests/interaction/ -v
```

Execute live monitor or benchmark via CLI:
```bash
# Live webcam test
python3 main.py interaction test --source 0

# Benchmark mode without display
python3 main.py interaction test --source 0 --frames 100 --benchmark --no-display
```
