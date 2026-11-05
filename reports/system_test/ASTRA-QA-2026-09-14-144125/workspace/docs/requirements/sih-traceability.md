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

| SIH26174 Requirement | ASTRA-EA Architecture Component | Subsystem Location | Current Status (Phase 4) | Phase Verified | Notes / Verification Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI Perception (Object Detection)** | Object Detector Interface & Implementations | `core/perception/detection/` | **VALIDATED** | Phase 2 | `ColorSpatialObjectDetector`, `YOLOAdapter` (OpenCV DNN), verified on live camera. |
| **AI Perception (Human Pose)** | Pose Estimator Interface & Keypoint Models | `core/perception/pose/` | **VALIDATED** | Phase 2 | Microgravity orientation-invariant torso & shoulder keypoint grounding. |
| **Hand-Object Interaction** | Spatial Interaction Engine | `core/interaction/` | **VALIDATED** | Phase 3 | Distance, trajectory coupling, contact, grasp, move, place state machine. |
| **Activity Recognition** | Temporal Activity Recognizer | `core/activity/` | **VALIDATED** | Phase 3 | Bounded rolling buffer (5–30s), primitive and composite action composition. |
| **Experiment Step Recognition** | Procedure Engine & Step Evaluator | `core/procedure/` | **VALIDATED** | Phase 4 | Procedure matcher, step evaluator, progress FSM, expected next step engine. |
| **Multimodal Corroborating Evidence** | Evidence Corroboration Engine | `core/evidence/` | **VALIDATED** | Phase 4 | 13-factor multimodal evidence bundles with deterministic scoring. |
| **Timestamped Experiment Logging** | Mission Event Logger & SQLite Store | `core/mission/`, `storage/` | **VALIDATED** | Phase 1, 4 | SQLite WAL schema (15 tables), step evaluations, evidence bundles, and traces. |
| **Deterministic Offline Replay** | Procedure Replay Engine | `core/procedure/replay.py` | **VALIDATED** | Phase 4 | Offline deterministic replay of recorded event traces without camera hardware. |
| **Causal Audit Traceability** | Step Trace Record Engine | `core/procedure/traceability.py` | **VALIDATED** | Phase 4 | Full causal ASCII audit trees linking step decisions to frame numbers & bboxes. |
| **Sequence Deviation Detection** | Assurance Deviation Evaluator | `core/assurance/` | **READY** | Phase 5 | Tri-state verification (`VERIFIED`, `UNCERTAIN`, `DEVIATION`) & deviation taxonomy. |
| **Intelligent Assistance & Voice Alerts** | Voice Manager & Guidance Engine | `core/assistance/` | **READY** | Phase 5 | Offline TTS (`pyttsx3`), priority queues, speech deduplication, recovery guidance. |
| **Live Monitoring GUI** | Mission Console (PySide6) | `apps/mission_console/` | **PLANNED** | Phase 6 | High-density dark-themed operations dashboard with live video HUD. |
| **Synthetic Dataset Pipeline** | Dataset Studio & Synthetic Generator | `apps/dataset_studio/` | **PLANNED** | Phase 7 | Generates synthetic microgravity augmentations labeled as `SYNTHETIC`. |
| **Offline Processing Capability** | Edge Runtime Architecture | Whole System | **VALIDATED** | Phase 1–4 | 100% air-gapped local execution, zero cloud or external API dependencies. |
| **Configurable Experiment Sequence** | YAML Procedure Definition & Validator | `configs/experiments/`, `core/procedure/` | **VALIDATED** | Phase 1, 4 | Dynamic schema-driven; zero code changes required to define experiments. |
