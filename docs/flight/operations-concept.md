# ASTRA-EA — Concept of Operations (CONOPS)

### Document ID: `ASTRA-CONOPS-001`
**Milestone**: Phase 18 — Flight Integration Preparation + Onboard Software Packaging  
**Target Mission**: In-Orbit Science & Material Processing Experiment Assurance  

---

## 1. Operational Timeline

```
[ PRE-EXPERIMENT ] ──► [ NOMINAL EXECUTION ] ──► [ POST-EXPERIMENT ]
         │                       │                        │
         ▼                       ▼                        ▼
 - Power-On Boot          - Step Guidance          - Mission Summary
 - Subsystem Self-Test    - Interaction Tracking   - Evidence Manifest
 - Procedure Selection    - Real-Time Assurance    - Telemetry Downlink
 - Ground Status ACK      - Deviation Handling     - State Freeze
```

---

## 2. Operational Phases

### Phase A: Pre-Experiment Readiness
1. **Power Application**: Spacecraft bus applies 28V DC power to the payload enclosure.
2. **Deterministic Boot**: System boots within $\le 5.0$ seconds, runs `FlightStartupSequence`, validates model/procedure checksums.
3. **Self-Test Verification**: Platform checks camera, storage, and health monitor.
4. **Housekeeping Telemetry**: Downlinks `HEALTH` packet to spacecraft housekeeping bus (`READY` state).

### Phase B: Experiment Initiation
1. **Command Uplink**: Ground controller or crew astronaut issues `START_EXPERIMENT` with target `experiment_id` and `procedure_id`.
2. **Command Validation**: `CommandDispatcher` validates authorization, parameter syntax, and confirms camera/model availability.
3. **Mission State Persistence**: Creates run entry in `flight_data/mission/active_mission_state.json`.

### Phase C: Active Experiment Execution
1. **Step Guidance**: Audio engine speaks concise, unambiguous astronaut action prompts while cockpit HUD displays visual overlays.
2. **Visual Observation**: Camera streams frames to neural detector at 30 FPS.
3. **Interaction Assurance**: Evaluates spatial overlap, hand proximity, and dwell time.
4. **Step Verification**: When all 5 evidence barriers are satisfied, emits `VERIFIED` telemetry and advances to next step.

### Phase D: Anomaly & Deviation Handling
1. **Deviation Detection**: If crew member touches wrong apparatus or skips mandatory steps, assurance state transitions immediately to `DEVIATION`.
2. **Auditory & Visual Alert**: System emits calm, non-accusatory corrective instruction (e.g. *"Attention: Valve B opened prior to manifold purge. Please close Valve B."*).
3. **Corrective Recovery Confirmation**: System monitors crew action; upon verifying corrective remediation, transitions state back to `VERIFIED` and resumes.

### Phase E: Experiment Completion & Reporting
1. **Clean Termination**: Upon completion of final step, system records final evidence hashes.
2. **Report Generation**: Generates run summary JSON and HTML in `flight_data/reports/`.
3. **Downlink Package**: Flushes mission state, marks completed, and returns to `READY` state awaiting next experiment.
