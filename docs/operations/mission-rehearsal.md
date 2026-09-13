# ASTRA-EA Mission Rehearsal & Operational Validation Manual (Phase 20, D20.25)

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Operational Overview

Phase 20 establishes the operational rehearsal framework for ASTRA-EA. The objective is to transition from component-level demonstrations to unified, mission-like execution combining:

```text
ASTRONAUT OPERATOR
       +
ONBOARD FLIGHT SOFTWARE
       +
PHYSICAL EXPERIMENT RIG / HIL PLATFORM
       +
GROUND OBSERVABILITY CONSOLE
       +
ASSURANCE & DEVIATION ENGINE
       +
RECOVERY GUIDANCE
       +
POST-MISSION AUDIT & REPORTING
```

The core operational rule governing all rehearsals:

> **Can a trained operator execute the entire experiment and recover from anomalies without developer intervention?**

---

## 2. Rehearsal Execution Modes (Section 5 & 6)

ASTRA-EA enforces four distinct operational execution modes. In strict adherence to Section 6, **every screen and report prominently displays its active mode badge**; a simulation is NEVER labeled a live mission.

```text
+-------------------+---------------------------------------------------------------+
| Mode              | Description                                                   |
+-------------------+---------------------------------------------------------------+
| FULL_REAL         | Physical experiment, live camera sensor, and real runtime     |
| HIL               | Physical/edge hardware environment with controlled injection  |
| SIMULATION        | Deterministic simulated execution sandbox                     |
| STEPWISE          | Interactive milestone-by-milestone operator training mode     |
+-------------------+---------------------------------------------------------------+
```

---

## 3. Mission Rehearsal Lifecycle (Section 7)

Every formal rehearsal advances through the mandatory operational milestones:

```text
T-START (Environment clean verification)
   ↓
PRE-MISSION (Checklist verification: power, camera, model, procedure, storage)
   ↓
SELF-TEST (Clock sync, neural session check, ground heartbeat)
   ↓
READY (Start authorization dispatched)
   ↓
EXPERIMENT START (Active telemetry recording, run ID generation)
   ↓
STEP EXECUTION (Continuous perception, activity recognition, evidence seal)
   ↓
ANOMALY (Planned deviation detected, alert generated, audio guidance active)
   ↓
RECOVERY (Operator responds, corrective action verified by perception)
   ↓
CONTINUE (Remaining steps executed and verified)
   ↓
EXPERIMENT COMPLETE (Recording flushed, database sealed)
   ↓
POST-MISSION (Report generated, checksums hashed, evidence manifest written)
   ↓
GROUND REVIEW (Read-only observability audit completed)
```

---

## 4. Rehearsal Command Reference

### Run the Golden Mission Baseline
```bash
astra rehearsal --scenario GOLDEN_MISSION --speed ACCELERATED
```

### Run All 12 Operational Scenarios Sequentially
```bash
astra rehearsal --scenario ALL --speed ACCELERATED
```

### Run Specific Failure Drill Scenarios
```bash
# Clean run with zero deviations
astra rehearsal --scenario REH_02_CLEAN --speed ACCELERATED

# Sensor loss and pause behavior
astra rehearsal --scenario REH_05_CAMERA_FAILURE --mode HIL --speed ACCELERATED

# Telemetry ground sever and reconciliation
astra rehearsal --scenario REH_04_NETWORK_FAILURE --mode HIL --speed ACCELERATED

# Independent operator validation
astra rehearsal --scenario REH_12_OPERATOR_INDEP --operator "Astronaut_Trainee_2"
```

### Execute Authoritative Dress Rehearsal
```bash
astra dress-rehearsal --speed ACCELERATED
```

### Generate & Audit Consolidated Scorecards
```bash
astra rehearsal-scorecard
```

---

## 5. Artifact Package Architecture (Section 42)

Every rehearsal run produces a self-contained, isolated bundle in `reports/rehearsal/RUN_XXXX/`:

```text
reports/rehearsal/RUN_XXXX/
├── scorecard.json                  # Machine-readable evaluation & latency timings
├── mission_report.html             # Standalone responsive audit report
├── timeline.json                   # Milestones keyed to Mission Elapsed Time (MET)
├── events.json                     # Monotonically sequenced event stream
├── health.json                     # Aggregate subsystem health snapshot
├── evidence_manifest.json          # Cryptographic frame references & SHA-256 hashes
├── configuration_snapshot.yaml     # Immutable snapshot of active config
└── rehearsal_notes.md              # Operator observations & findings
```

---

## 6. Success & Failure Criteria (Sections 39 & 40)

### Mission PASS Criteria
* 100% of required procedure steps verified with valid evidence.
* 100% of planned deviations detected and successfully recovered.
* **0 false verifications** (no step verified without satisfying evidence).
* **0 false deviations** (occlusions handle gracefully as `UNCERTAIN`).
* Strict data consistency across SQLite, logs, timeline, and evidence.
* Generated post-mission audit reports cryptographically sealed.

### Rehearsal FAIL Criteria
* Any false verification or unverified transition.
* Loss or corruption of critical evidence frames.
* Unhandled exception crashing runtime or console.
* Ground reconciliation producing duplicate sequence numbers.
* Unauthorized developer intervention during execution.
