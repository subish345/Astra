# ASTRA-EA Fault Injection & Simulation Testing Guide

Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. CLI Commands Quick Reference

### List Available Fault Injection Operators
```bash
python3 main.py sim faults
```
Displays all supported Optical, Behavioral, Perception, and System fault operators along with their simulation mechanics.

---

### Run Individual Mission Simulation Scenario
```bash
# Run nominal baseline mission
python3 main.py sim run --scenario configs/simulations/nominal_mission.yaml

# Run unauthorized specimen selection fault test
python3 main.py sim run --scenario configs/simulations/wrong_object_fault.yaml

# Run optical degradation stress test (low light, glare, smudge)
python3 main.py sim run --scenario configs/simulations/optical_stress.yaml

# Run sensor and frame dropout stress test
python3 main.py sim run --scenario configs/simulations/sensor_dropout.yaml

# Run multi-angle viewpoint switch test
python3 main.py sim run --scenario configs/simulations/viewpoint_shift.yaml
```

**Optional Arguments:**
- `--max-frames <N>`: Limit simulation execution to $N$ frames.
- `--realtime`: Pace execution to match target frame rate (e.g. 30 FPS).
- `--report-dir <path>`: Custom output directory for HTML and JSON reports.

---

### Run Automated Simulation Fault Matrix
```bash
# Run full verification matrix across all scenarios
python3 main.py sim matrix --matrix configs/simulations/full_matrix.yaml

# Run all YAML scenarios in a directory
python3 main.py sim matrix --scenarios-dir configs/simulations
```

---

## 2. Authoring Custom Simulation Scenarios

Simulation scenarios are defined as declarative YAML files in `configs/simulations/`:

```yaml
scenario_id: "SIM_CUSTOM_001"
name: "Custom Cabin Lighting Drop and Specimen Misidentification"
description: "Simulates sudden cabin power drop followed by distractor specimen grasp."
procedure_path: "configs/experiments/demo.yaml"
camera_profile: "VIEW_LEFT"
duration_sec: 12.0
target_fps: 30.0
synthetic_seed: 70007

faults:
  # 1. Optical fault: Low light drop at 1.5s
  - fault_type: "LOW_LIGHT"
    start_time: 1.5
    duration_sec: 3.0
    intensity: 0.80

  # 2. Behavioral fault: Wrong specimen selection at 5.0s
  - fault_type: "WRONG_OBJECT"
    start_time: 5.0
    duration_sec: 4.0
    intensity: 1.00
    target: "YELLOW_BOX"

expected_final_status: "DEVIATION"
expected_deviations:
  - "WRONG_OBJECT"
```

---

## 3. Interpreting Reports & Scorecards

Upon completion of an individual run or matrix batch, reports are saved to `storage/reports/simulation/`:

1. **Structured JSON Telemetry** (`*_report.json`):
   - Contains frame-by-frame decision history (`sim_time`, `step_id`, `decision_type`, `confidence`, `active_faults`).
   - Contains aggregated metrics: `resilience_score`, `pipeline_crashes`, `false_positive_deviations`, `mttd_sec`.
2. **Visual HTML Scorecard** (`*_report.html`):
   - Aerospace mission control styling.
   - Status badges: `PASS` (Green) or `FAIL` (Red).
   - Detailed metric breakdown and complete decision timeline.
