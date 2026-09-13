# SIH26174 Traceability Matrix

## 1. Traceability Overview
This matrix traces every requirement specified in the SIH26174 problem statement (*AI Human Activity Recognition for On-board BAS Experiments*) directly to the corresponding component in **ASTRA-EA**.

Status Definitions:
- **PLANNED**: Architecturally defined with module contracts; implementation scheduled in subsequent phases.
- **PARTIAL**: Initial interface, data contracts, or foundation stubs created.
- **IMPLEMENTED**: Fully coded in application source.
- **TESTED**: Unit and integration test suites pass in CI/local test environment.
- **VALIDATED**: Verified against end-to-end hardware and synthetic scenario benchmarks.

---

## 2. Requirement Mapping Matrix

| SIH26174 Requirement | ASTRA-EA Architecture Component | Subsystem Location | Current Status (Phase 0/1) | Phase Scheduled | Notes / Verification Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI Perception (Object Detection)** | Object Detector Interface & Implementations | `core/perception/` | **PARTIAL** | Phase 4 | Bounding boxes, class labels, confidence scores for configured items. |
| **AI Perception (Human Pose)** | Pose Estimator Interface & Keypoint Models | `core/perception/` | **PARTIAL** | Phase 4 | Orientation-invariant body keypoint detection (standing, floating, inverted). |
| **Hand-Object Interaction** | Interaction Engine | `core/interaction/` | **PARTIAL** | Phase 5 | Distance, trajectory coupling, contact, grasp, move, place detection. |
| **Activity Recognition** | Temporal Activity Recognizer | `core/activity/` | **PARTIAL** | Phase 6 | Multi-frame temporal window reasoning (5–30 sec) across interactions. |
| **Experiment Step Recognition** | Procedure Engine | `core/procedure/` | **PARTIAL** | Phase 2 | Schema-driven state machine comparing activities to active step. |
| **Sequence Validation** | Assurance Engine | `core/assurance/` | **PARTIAL** | Phase 8 | Tri-state verification (`VERIFIED`, `UNCERTAIN`, `DEVIATION`). |
| **Skipped-Step & Wrong-Order Detection**| Assurance Deviation Evaluator | `core/assurance/` | **PARTIAL** | Phase 8 | Identifies sequence skips, reversals, incorrect objects, or timeouts. |
| **Intelligent Assistance & Voice Alerts** | Voice Manager & Guidance Engine | `core/assistance/`, `voice/` | **PARTIAL** | Phase 9, 10 | Offline TTS, priority queues, speech deduplication, recovery guidance. |
| **Timestamped Experiment Logging** | Mission Event Logger & SQLite Store | `core/mission/`, `storage/` | **PARTIAL** | Phase 1 | Structured event logs + lightweight human-readable audit records. |
| **Local Video Recording & Evidence** | Circular Buffer & Evidence Recorder | `core/camera/`, `storage/` | **PARTIAL** | Phase 14 | Pre- and post-event buffered video clip extraction per milestone/deviation. |
| **Live Monitoring GUI** | Mission Console (PySide6) | `apps/mission_console/` | **PLANNED** | Phase 11 | High-density dark-themed operations dashboard with live feed & evidence. |
| **IP Video Streaming** | Pluggable Streaming Layer | `streaming/` | **PLANNED** | Phase 15 | Local RTSP/WebRTC streaming for decoupled ground oversight. |
| **Offline Processing Capability** | Edge Runtime Architecture | Whole System | **PARTIAL** | Phase 1 | 100% air-gapped execution, zero external cloud dependencies. |
| **Configurable Experiment Sequence** | YAML Procedure Definition & Validator | `configs/experiments/`, `core/procedure/` | **IMPLEMENTED** | Phase 1 | Schema-driven; zero code changes required to define or modify experiments. |
| **Synthetic Dataset Pipeline** | Dataset Studio & Synthetic Generator | `apps/dataset_studio/`, `datasets/` | **PLANNED** | Phase 12 | Generates synthetic augmentations labeled clearly as `SYNTHETIC`. |
| **Simulation & Fault Injection** | Simulation Lab & Scenario Runner | `apps/simulation_lab/`, `simulation/` | **PLANNED** | Phase 13 | File-based video replay with deterministic deviation injection. |
