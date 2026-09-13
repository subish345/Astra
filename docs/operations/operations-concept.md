# ASTRA-EA — Concept of Operations (CONOPS)

## Phase 19: Mission Operations & Ground Segment Integration (D19.01)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)  
**Standard:** ECSS-E-ST-70C (Space Operations) / NASA-STD-8739.8 (Software Assurance)  
**Applicability:** Flight-like Onboard Payload Compute & Remote Ground Observability

---

## 1. Operational Purpose & Mission Overview

ASTRA-EA operates as an autonomous, closed-loop AI mission assurance and crew assistance system aboard human-crewed spacecraft and remote orbital laboratory platforms. 

The primary mission operational objective is to ensure that complex scientific procedures (e.g. molecular biology, crystal growth, fluid physics) conducted in microgravity are executed with **100% protocol fidelity**, providing real-time cognitive guidance, detecting procedural deviations, generating verifiable evidence chains, and ensuring ground science teams have full situational awareness without interfering with astronaut workflow.

---

## 2. Operational Phasing Model

In accordance with Section 8, the mission operational lifecycle is structured into 8 discrete, irreversible (except through formal abort/reset) phases:

```
┌─────────────┐     ┌────────────────┐     ┌───────┐     ┌────────────┐
│ PREPARATION │ ──► │ INITIALIZATION │ ──► │ READY │ ──► │ EXPERIMENT │
└─────────────┘     └────────────────┘     └───────┘     └────────────┘
                                                               │
                                                               ▼
┌──────────────┐     ┌──────────┐     ┌──────────┐     ┌───────────┐
│ POST_MISSION │ ◄── │ COMPLETE │ ◄── │ RECOVERY │ ◄── │  ANOMALY  │
└──────────────┘     └──────────┘     └──────────┘     └───────────┘
```

### Phase Transition Matrix

| Phase | Entry Conditions | Allowed Operational Actions | Exit Criteria | Required Permanent Records |
| :--- | :--- | :--- | :--- | :--- |
| **PREPARATION** | Bus power nominal; storage partitions mounted. | Run `astra mission precheck`; execute PRE_MISSION checklist; review procedure YAML. | All critical checklist items signed; hardware & model pass. | `pre_mission_checklist.json` |
| **INITIALIZATION** | Precheck passing; operator dispatch. | Optical camera init; ONNX model load; storage scrub; clock start. | Subsystems report READY; mission clock active. | `startup_configuration_report.json` |
| **READY** | Initialization complete; zero subsystem faults. | Authorize experiment start; review baseline viewpoint. | Explicit `START_EXPERIMENT` command from operator. | `ready_state_snapshot.json` |
| **EXPERIMENT** | READY state verified; run ID assigned. | Step verification; activity recognition; live telemetry stream; local audit record. | Final step verified OR Procedural deviation detected. | `events.json`, `evidence/` |
| **ANOMALY** | Deviation triggered OR Subsystem fault. | Audio recovery prompt; ground alert broadcast; operator acknowledgement. | Corrective recovery instruction dispatched & acknowledged. | `deviation_event.json` |
| **RECOVERY** | Anomaly acknowledged; crew reacting. | Optical tracking of corrective movement; apparatus pose re-verification. | Corrective action confirmed (return to EXPERIMENT) or abort. | `recovery_event.json` |
| **COMPLETION** | All protocol steps completed. | Flush video buffer; close telemetry stream; compute metrics. | All non-volatile buffers flushed to disk. | `completion_summary.json` |
| **POST_MISSION** | Completion acknowledged. | Run export bundle (`astra mission export`); generate report; science review. | Checksums verified; archive sealed. | `report.json`, `report.html` |

---

## 3. Human-System Interaction Architecture

```
                 SPACECRAFT EXPERIMENT WORKSTATION
┌─────────────────────────────────────────────────────────────────┐
│ [Optical Camera] ──► [Onboard Jetson / Edge Compute]            │
│                              │                                  │
│           ┌──────────────────┴──────────────────┐               │
│           ▼                                     ▼               │
│    [Mission Console GUI]               [Audio Headset]          │
│   (HUD, Step Progress,                (Offline Voice Guidance,   │
│    Assurance Badges)                   Deviation Audio Alerts)  │
└──────────────────┬──────────────────────────────────────────────┘
                   │ Spacecraft Telemetry / Streaming Bus (TBD)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ GROUND OBSERVABILITY SEGMENT                                    │
│ [Ground Monitor Console] (Read-Only)                            │
│  - H.264 / MJPEG Live Video Stream                              │
│  - Time-Indexed Telemetry Events                                │
│  - Alert Acknowledgement Banner                                 │
│  - Dual Clock: Onboard MET vs Ground Receipt Time (GRT)         │
│  - Automated Sequence Gap Detection & Reconnection Sync         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Key Governing Principles

1. **Assurance Overrides Convenience:** Onboard verification decisions are mathematically bounded by computer vision confidence and temporal logic. Neither crew nor ground can bypass or edit verified step criteria during an active run.
2. **Autonomous Continuation:** During Loss of Signal (LOS) with Ground Control, onboard operations continue without pause. All events are buffered in local ring storage and synchronized upon Acquisition of Signal (AOS).
3. **No Direct Ground Mutation:** The Ground Observability Monitor is strictly read-only. Ground operators cannot invoke internal Python methods or arbitrarily skip procedure steps.
