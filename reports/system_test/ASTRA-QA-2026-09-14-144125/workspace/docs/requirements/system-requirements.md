# ASTRA-EA System Requirements Specification

## 1. Introduction
This document defines the functional and non-functional requirements for the **Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)** ground demonstrator, in fulfillment of problem statement **SIH26174**.

---

## 2. Requirements Matrix Overview

| Requirement Category | Scope | Timeline |
| :--- | :--- | :--- |
| **Core Baseline** | Local edge-AI ingestion, assurance, assistance, logging | **REQUIRED NOW** |
| **Ground Operations** | Ground monitor, exportable audit reports, dataset tooling | **REQUIRED NOW** |
| **Spacecraft Adaptation**| 3D HMR, multi-camera fusion, flight qualification | **FUTURE EXTENSION** |

---

## 3. Functional Requirements (FR)

### 3.1 Video Ingestion & Camera
- **FR-01 [REQUIRED NOW]**: The system shall support real-time video ingestion from local cameras (USB/MIPI/CSI) at a minimum of 15 FPS.
- **FR-02 [REQUIRED NOW]**: The system shall support deterministic video file playback (`.mp4`, `.avi`, `.mkv`) for reproducible testing and simulation.
- **FR-03 [REQUIRED NOW]**: Ingestion shall maintain monotonic frame timestamps synchronized to wall-clock reference.

### 3.2 Perception Engine
- **FR-04 [REQUIRED NOW]**: The system shall detect configured experiment objects with 2D bounding boxes, class labels, and confidence metrics.
- **FR-05 [REQUIRED NOW]**: The system shall detect human presence (astronaut) and 2D body pose keypoints independent of body orientation (standing, floating, inverted).
- **FR-06 [REQUIRED NOW]**: The system shall detect left and right hand keypoints and wrist locations.
- **FR-07 [REQUIRED NOW]**: The system shall maintain persistent identity tracking (`track_id`) for objects and hands across temporal occlusions lasting up to 1.5 seconds.

### 3.3 Interaction & Activity Reasoning
- **FR-08 [REQUIRED NOW]**: The system shall detect spatial-temporal hand-object relationships including `APPROACH`, `CONTACT`, `GRASP`, `LIFT`, `MOVE`, `PLACE`, and `RELEASE`.
- **FR-09 [REQUIRED NOW]**: Activity recognition shall evaluate temporal windows (5–30 seconds) rather than isolated single frames.
- **FR-10 [REQUIRED NOW]**: The system shall produce structured `EvidenceBundle` instances containing verification factors for each candidate activity.

### 3.4 Procedure & Assurance
- **FR-11 [REQUIRED NOW]**: The procedure engine shall load and validate experiment definitions dynamically from YAML/JSON without modifying source code.
- **FR-12 [REQUIRED NOW]**: The assurance engine shall evaluate evidence against the active experiment step and yield strictly one of three states: `VERIFIED`, `UNCERTAIN`, or `DEVIATION`.
- **FR-13 [REQUIRED NOW]**: The system shall explicitly differentiate between `UNCERTAIN` (insufficient evidence, occlusion, low confidence) and `DEVIATION` (contradictory action or skipped step). `UNCERTAIN` shall never trigger a failure penalty.
- **FR-14 [REQUIRED NOW]**: The system shall classify deviations into `SKIPPED_STEP`, `WRONG_ORDER`, `WRONG_OBJECT`, `INCOMPLETE_ACTION`, `UNEXPECTED_ACTION`, `REPEATED_ACTION`, and `TIMEOUT`.

### 3.5 Assistance & Voice Guidance
- **FR-15 [REQUIRED NOW]**: The assistance engine shall provide offline audio guidance using a local text-to-speech synthesizer.
- **FR-16 [REQUIRED NOW]**: Voice output shall enforce speech deduplication, priority queuing (`INFO`, `GUIDANCE`, `WARNING`, `CRITICAL`), and configurable cooldown intervals.
- **FR-17 [REQUIRED NOW]**: Upon deviation, the system shall guide the astronaut through a closed-loop recovery sequence and verify corrective action before advancing.

### 3.6 Telemetry, Logging & Audit
- **FR-18 [REQUIRED NOW]**: All state transitions, decisions, deviations, and health events shall be persisted to an ACID-compliant local SQLite database.
- **FR-19 [REQUIRED NOW]**: The system shall generate lightweight human-readable timestamped mission log files alongside structured database records.
- **FR-20 [REQUIRED NOW]**: The system shall automatically save circular-buffered pre-event and post-event video clips for every verified step and deviation event.
- **FR-21 [REQUIRED NOW]**: The system shall export comprehensive final mission reports in JSON, TXT, and HTML formats.

### 3.7 Operator GUI & Monitoring
- **FR-22 [REQUIRED NOW]**: The platform shall provide a high-density, dark-themed space operations console (PySide6) displaying live annotated video, active step progress, evidence checklist, decision status, and subsystem health.
- **FR-23 [REQUIRED NOW]**: The system shall support a decoupled Ground Monitor displaying streaming telemetry over a local network.

---

## 4. Non-Functional Requirements (NFR)

### 4.1 Autonomy & Offline Capability
- **NFR-01 [REQUIRED NOW - CRITICAL]**: The entire perception, assurance, assistance, and logging pipeline shall operate with 100% functionality in an air-gapped, zero-Internet environment.
- **NFR-02 [REQUIRED NOW - CRITICAL]**: No cloud service (OpenAI, AWS, Azure, GCP, remote TTS) or external LLM API shall be utilized in the critical assurance path.

### 4.2 Performance & Edge Efficiency
- **NFR-03 [REQUIRED NOW]**: End-to-end inference and assurance decision latency shall remain under 100 ms per processed frame on development hardware (NVIDIA RTX 5060 Laptop GPU).
- **NFR-04 [REQUIRED NOW]**: Memory allocation for circular video buffers and tracking state shall be strictly bounded to prevent heap exhaustion.

### 4.3 Reliability & Fault Tolerance
- **NFR-05 [REQUIRED NOW]**: Failure of auxiliary subsystems (voice TTS, network streaming, or GUI rendering) shall never crash or halt the core perception and assurance logging pipeline.
- **NFR-06 [REQUIRED NOW]**: Temporary camera disconnections shall transition the system into a graceful `DEGRADED` health state, pausing procedure verification without data corruption.

### 4.4 Modularity & Maintainability
- **NFR-07 [REQUIRED NOW]**: All core layers (Camera, Perception, Interaction, Activity, Procedure, Assurance, Assistance, Storage) shall communicate via abstract interfaces and typed data contracts.
- **NFR-08 [REQUIRED NOW]**: Experiment definitions shall be 100% decoupled from Python logic, allowing new scientific procedures to be introduced purely via YAML configuration.

---

## 5. Future Extensions (FE)

- **FE-01 [FUTURE EXTENSION]**: 3D Human Mesh Recovery (HMR) for volumetric pose estimation in microgravity.
- **FE-02 [FUTURE EXTENSION]**: Multi-camera spatial fusion across wide-angle and macro experiment rack views.
- **FE-03 [FUTURE EXTENSION]**: Edge-hardware deployment optimization using TensorRT, ONNX Runtime INT8 quantization, and hardware NPU targets.
- **FE-04 [FUTURE EXTENSION]**: Direct experiment hardware interlocking via separate, deterministic safety PLCs.
- **FE-05 [FUTURE EXTENSION]**: Spaceflight radiation hardening and thermal-vacuum qualification analysis.
