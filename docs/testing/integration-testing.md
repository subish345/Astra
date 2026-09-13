# ASTRA-EA Integration & Verification Testing Guide

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Product Version**: `v1.0.0`

---

## 1. Test Pyramid & Coverage Hierarchy

ASTRA-EA enforces a strict six-tier verification testing pyramid to ensure absolute reliability in flight-like conditions:

```text
               ▲
              / \
             /   \     Soak & Stability Tests (30+ min continuous load)
            /     \    System & Golden Path Tests (E2E mission lifecycle)
           /───────\   Failure Regression & Fault Injection Matrix (6 scenarios)
          /         \  Integration Tests (Service boundaries, event bus, DB)
         /           \ Unit Tests (Algorithms, geometry, schemas, state machines)
        /─────────────\
```

Total Automated Tests: **247 Passed** (0 Failures, 100% Pass Rate).

---

## 2. Running Automated Tests

Run the complete test suite:
```bash
python3 -m pytest tests/ -v
```

Run Phase 11 integration and system test suites specifically:
```bash
python3 -m pytest tests/integration/test_mission_orchestrator.py \
                  tests/system/test_golden_demo.py \
                  tests/system/test_failure_regression.py \
                  tests/system/test_soak_integration.py -v
```

---

## 3. Golden Demo Regression Test (`GOLDEN_DEMO.yaml`)

The Golden Demo scenario (`configs/simulations/GOLDEN_DEMO.yaml`) represents the canonical regression path for ASTRA-EA:
1. **Pre-Flight Self-Test**: Validates optical sensors, object models, procedure definitions, SQLite storage, local voice synthesis, and recording pipelines.
2. **Step 1 (Nominal)**: Astronaut approaches and grasps `RED_BOX`. Action and spatial bounds verified.
3. **Step 2 (Injected Fault)**: Astronaut grasps `BLUE_BOX` instead of required `YELLOW_BOX`.
4. **Assurance Trigger**: Tri-state engine flags `DEVIATION` with reason `WRONG_OBJECT`.
5. **Closed-Loop Assistance**: Real-time HUD and vocal warning prompts: *"Release BLUE_BOX and acquire YELLOW_BOX"*.
6. **Recovery Observation**: Astronaut releases `BLUE_BOX`, acquiring `YELLOW_BOX`. Recovery transition verified.
7. **Steps 3 & 4 (Completion)**: Specimen placed in test chamber, sealed, and procedure completes.
8. **Audit Generation**: Final `mission_report.json` and `mission_report.html` generated with 100% cross-consistency across SQLite database, timeline, and event logs.

---

## 4. Failure Regression & Recovery Validation

Failure tests ensure that unexpected hardware or software events never cause unhandled crashes:
* **Camera Loss**: Optical feed loss triggers immediate mission pause (`PAUSED`). Stale frames are prevented from verifying steps. Upon sensor reconnection, the mission resumes.
* **Storage Warnings**: Filesystem monitoring warns when partition free space drops below 2.0 GB.
* **Crash Recovery**: If the system process terminates abruptly, restart detects incomplete runs (`detect_incomplete_runs()`) and offers safe recovery or finalized interrupted status without data loss.
* **Air-Gap Verification**: Full functionality operates with zero external network connectivity or cloud APIs.
