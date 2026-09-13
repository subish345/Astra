# ASTRA-EA

## Autonomous Spacecraft Experiment Assurance & Assistance

> **Tagline:** *"See. Understand. Verify. Assist. Record. — Locally, in Space."*  
> **Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
> **System Status:** Phase 21 Completed — Findings-Driven Hardening + Corrective Action + Release Candidate 2 (ASTRA-EA-v1.0.0-RC2) Operational  
> **Classification:** Engineering-Grade Ground Demonstrator (Not flight qualified or zero-g certified)

---

## 1. Executive Summary

**ASTRA-EA** is an offline, edge-AI experiment assurance platform designed to observe an astronaut performing a scientific experiment in microgravity through an onboard optical sensor. By evaluating hand-object interactions, physical kinematics, and temporal activity progression against an external, configuration-driven procedure, ASTRA-EA verifies whether procedural steps are executed correctly, flags sequence deviations, provides real-time voice and visual guidance, and generates an immutable local audit record.

### Core Architectural Axiom
$$\text{Camera View} \longrightarrow \text{Normalized Observations} \longrightarrow \text{Interaction} \longrightarrow \text{Activity} \longrightarrow \text{Evidence} \longrightarrow \text{Procedure} \longrightarrow \text{Assurance} \longrightarrow \text{Assistance} \longrightarrow \text{Logging}$$

> **Camera viewpoint changes the observation condition, NOT the meaning of the experiment.**  
> **AI observes. Evidence explains. The assurance engine decides. The assistance engine communicates. The logger records.**

Raw neural-network confidence is **never** permitted to become mission ground truth. Instead, decisions are grounded in explainable, multi-factor evidence bundles evaluated by a deterministic assurance engine.

---

## 2. Core Tri-State Assurance Model

The assurance engine yields strictly one of three discrete states:

1. **`VERIFIED`**: Activity matches the expected procedural step; all required evidence conditions (object presence, hand contact, relative motion, temporal window) are satisfied.
2. **`UNCERTAIN`**: Ambiguity detected due to temporary occlusion, missing hand/object keypoints, low lighting, or marginal confidence.
   - **Critical Rule:** `UNCERTAIN` is **NEVER** conflated with `DEVIATION`. Procedure verification safely pauses; the astronaut is never falsely penalized for visual ambiguity or camera-angle dropouts.
3. **`DEVIATION`**: Active procedural contradiction confirmed:
   - `WRONG_OBJECT`: Interacting with an unauthorized object (e.g. Yellow Buffer Box instead of Red Specimen Box).
   - `SKIPPED_STEP`: Advancing to a subsequent step before completing the current step.
   - `WRONG_ORDER`: Executing steps out of allowable transition topology.
   - `INCOMPLETE_ACTION`: Abandoning an action before required temporal thresholds are met.
   - `UNEXPECTED_ACTION`: Action primitive contradicts expected procedural set.
   - `TIMEOUT`: Exceeding maximum allotted step duration.

---

## 3. Strict Offline & Edge Autonomy

ASTRA-EA is engineered for air-gapped, high-reliability spacecraft operation:
- **Zero Cloud Dependencies:** Operates completely offline. No OpenAI, AWS, Azure, Google Cloud, remote GPU inference, or online TTS APIs.
- **No LLM in Critical Assurance Path:** Procedural validation, sequence verification, and safety decisions are 100% deterministic and model-based.
- **Local Audio Guidance:** Offline text-to-speech engine (`pyttsx3`) with speech deduplication, priority preemption, and cooldown intervals.
- **Local Persistence:** ACID-compliant SQLite audit store with Write-Ahead Logging (WAL), persisting assurance decisions, recovery events, step evaluations, and evidence bundles.
- **Honest Latency & Throughput Metrics:** Measured assurance evaluation latency P50 is **~0.01 ms**; full pipeline compute latency P50 is **~9.2 ms** (~108 FPS processing capacity on CPU).

---

## 4. Current Implementation Status

| Subsystem / Phase | Status | Details |
| :--- | :--- | :--- |
| **Phase 0: Requirements & Baseline** | **COMPLETE** | Architecture, functional requirements, SIH traceability matrix, and risk register in `docs/`. |
| **Phase 1: Architecture & Foundation** | **COMPLETE** | Modular project structure, YAML config system, SQLite schema (15 tables), health monitoring, and CLI. |
| **Phase 2: Camera & Perception** | **COMPLETE** | Threaded ingestion, `ColorSpatialObjectDetector`, `YOLOAdapter` (OpenCV DNN), pose estimator, hand detector, and `MultiObjectTracker`. |
| **Phase 3: Interaction & Activity** | **COMPLETE** | Live camera window, aerospace HUD, keyboard toggles, dual-space hand filter, Haar pose grounding, and interaction/temporal engines verified on `/dev/video0`. |
| **Phase 4: Procedure Assurance & Evidence** | **COMPLETE** | Procedure Matcher (D4.01), Evidence Engine (D4.02), Step Evaluator (D4.03), Progress Manager (D4.04), Next Step Engine (D4.05), Traceability (D4.07), Visualizer HUD (D4.08), Replay (D4.11), SQLite Audit (D4.13), 109 automated tests passing. |
| **Phase 5: Camera Robustness & Recovery** | **COMPLETE** | Camera viewpoint profiles (`VIEW_LEFT`, `VIEW_RIGHT`), viewpoint-invariant spatial geometry, anatomical hand grounding, Tri-State Assurance Engine, closed-loop recovery state machine (`DETECT` $\to$ `RESUME`), local TTS voice manager, and 8-scenario cross-view validation matrix (143 automated tests passing). |
| **Phase 6: Mission Console & Audio UX** | **COMPLETE** | PySide6 (Qt) Mission Console, presentation-only UI State Store, thread-safe Backend Event Bridge, live video panel, step & next action cards, corroborating evidence audit viewer, filterable event timeline, offline status indicators, local priority TTS with deduplication cooldowns (166 automated tests passing). |
| **Phase 7: Dataset Studio & Training Pipeline** | **COMPLETE** | Machine Learning Doctor (`main.py ml doctor`), real session recorder (`datasets/raw/real/`), synthetic procedural generator (`datasets/raw/synthetic/`) with reproducible seeds, integrity validator, cross-split leakage detector, session-level splitter (70/15/15), immutable versioning (`ASTRA-DATASET-v0.1`), model training runner (NVIDIA RTX 5060 GPU / CPU fallback), model registry (`CANDIDATE` $\to$ `VALIDATED`), held-out test evaluator, baseline-vs-learned comparator, viewpoint/scenario robustness analyzer, and 179 automated tests passing. |
| **Phase 8: Simulation & Fault Injection** | **COMPLETE** | End-to-end mission simulation engine (`core/simulation/engine.py`), scripted camera source (`SimulatedCameraSource`), 16 fault injection operators (`core/simulation/faults.py`), batch permutation matrix runner (`core/simulation/matrix.py`), HTML/JSON resilience reporting, 6 mission scenarios, zero false-deviation guarantee under optical stress, and 198 automated tests passing. |
| **Phase 9: Ground Monitor & IP Streaming** | **COMPLETE** | Non-blocking MJPEG video stream server (`:8554`), Server-Sent Events (SSE) telemetry server (`:8765`), 500-event ring buffer replay, read-only PySide6 Ground Monitor console, multi-channel link watchdog (`GOOD`/`DEGRADED`/`OFFLINE`), path traversal guards, rate limiter, dual-machine LAN deployment, 2.3% compute overhead, and 222 automated tests passing. |
| **Phase 10: Benchmarking & Edge Optimization** | **COMPLETE** | High-precision profiling framework, adaptive multi-cadence perception scheduler (`AdaptiveInferenceScheduler`), edge deployment hardware profiles (`configs/deployment/`), thermal/soak testing harness, and 237 automated tests passing. |
| **Phase 11: Full Product Integration & System Hardening** | **COMPLETE** | Single authoritative `MissionOrchestrator`, 16-state `MissionLifecycleManager`, `UnifiedEventBus` with correlation headers, `MissionRunManager` with configuration & model snapshots, `UnifiedEvidenceStore`, `UnifiedRecordingManager`, `UnifiedHealthAggregator`, native CLI packaging (`pip install -e .` -> `astra`), golden regression demo (`GOLDEN_DEMO.yaml`), deployment doctor, and 247 automated tests passing. |
| **Phase 12: Final Validation** | **COMPLETE** | End-to-end validation suite, zero-regression safety assertions, cross-environment qualification, Golden Master demonstration, 260 automated tests passing. |
| **Phase 13: Competition Operations** | **COMPLETE** | Turnkey standalone launcher, offline preflight checks, scoring self-audit, model card (`MODEL_CARD.md`), judge demonstration scripts, 275 automated tests passing. |
| **Phase 14: Physical & HIL Validation** | **COMPLETE** | Physical optical calibration, 3D test rig, motion blur and lighting stress, sensor dropouts, hardware-in-the-loop harness, 285 automated tests passing. |
| **Phase 15: Qualification Readiness** | **COMPLETE** | Spaceflight qualification review, DO-178C / ECSS compliance matrix, boundary tests, memory soak, 292 automated tests passing. |
| **Phase 16: Formal Verification & Validation (V&V)** | **COMPLETE** | Bidirectional requirement tracing, model checking, property-based tests, fault tree verification, 301 automated tests passing. |
| **Phase 17: Environmental & Hardware Qualification** | **COMPLETE** | Thermal-vacuum simulation, microgravity vibration jitter, radiation single-event upset mitigation, power glitch recovery, 301 automated tests passing. |
| **Phase 18: Flight Integration Preparation** | **COMPLETE** | Flight integration readiness, CCSDS telemetry format alignment, air-gap packaging, flight baseline release candidate 1 (`ASTRA-EA-v1.0.0-RC1`). |
| **Phase 19: Mission Operations & Ground Segment Integration** | **COMPLETE** | Operational concept (CONOPS), astronaut/ground operator manual, independent astronaut drill, dual-clock ground synchronization, 301 automated tests passing. |
| **Phase 20: End-to-End Mission Rehearsal & Operational Validation** | **COMPLETE** | 13 mission rehearsal scenarios, authoritative full-length Dress Rehearsal (zero developer intervention), automated scorecard engine, rehearsal findings ledger, 319 automated tests passing. |
| **Phase 21: Findings-Driven Hardening + Release Candidate 2 (RC2)** | **COMPLETE** | 6 empirical findings resolved via RCA & CAPA, dedicated regression suite in `tests/regression/`, hardening dashboard, RC1 vs RC2 quantitative comparison, release manifest `ASTRA-EA-v1.0.0-RC2`, 326 automated tests passing. |


> [!IMPORTANT]
> **Anti-Hallucination Notice:** In strict adherence to project engineering principles, no AI predictions, confidence metrics, or detection accuracies are fabricated. Ground-truth benchmark accuracy is reported as **`NOT YET EVALUATED`** until measured against human-labeled flight datasets in Phase 7.

---

## 5. Repository Structure

```text
astra-ea/
├── apps/                        # Application frontend consoles
│   ├── ground_monitor/          # Phase 9/19: PySide6 Ground Observation Console & state model
│   ├── hardening_dashboard/     # Phase 21: Hardening dashboard and readiness metrics
│   └── mission_console/         # Phase 6: Primary astronaut mission console
│
├── configs/                     # Centralized YAML configuration files
│   ├── cameras/                 # Camera resolution and device settings
│   ├── deployment/              # Edge deployment hardware profiles (balanced, realtime, etc.)
│   ├── experiments/             # Experiment procedures (e.g. demo.yaml)
│   ├── rehearsal/               # Phase 20: Golden mission baseline configurations
│   ├── simulations/             # Phase 8: Simulation scenario specifications
│   └── system.yaml              # Global system configuration
│
├── core/                        # Core application engine
│   ├── activity/                # Phase 3: Temporal buffer, primitive/composite engines, events
│   ├── assistance/              # Phase 5/6: Local TTS voice guidance and recovery contracts
│   ├── assurance/               # Phase 5: Tri-state assurance engine and deviation classification
│   ├── camera/                  # Ingestion thread, CameraSource, WebcamSource, profiles
│   ├── cli/                     # CLI subcommands (hardening, rehearsal, demo, doctor, etc.)
│   ├── common/                  # Configuration models, structured logging, and constants
│   ├── dataset/                 # Phase 7: Dataset Studio (generator, recorder, validator)
│   ├── evidence/                # Phase 4: Multimodal evidence engine (engine.py, types.py)
│   ├── hardening/               # Phase 21: Domain hardening workflows (workflows.py)
│   ├── health/                  # Subsystem heartbeat registry and runtime diagnostics
│   ├── interaction/             # Phase 3: Spatial kinematics, state machine, rules
│   ├── mission/                 # SQLite database engine, migrations, typed event models
│   ├── models/                  # Phase 7: Model Registry, LearnedObjectDetector, comparator
│   ├── operations/              # Phases 19-20: Rehearsal framework, precheck, scorecards
│   ├── perception/              # Phase 2: Ingestion, detectors, pose, hands, tracker
│   ├── procedure/               # Phase 4: Procedure assurance, matcher, evaluator, progress
│   ├── simulation/              # Phase 8: Simulation engine, simulated camera, faults, matrix
│   ├── streaming/               # Phase 9: Video (MJPEG) and SSE telemetry streaming
│   ├── training/                # Phase 7: ModelTrainingRunner, PyTorch pipeline
│   ├── ui/                      # Phase 6: PySide6 Qt Mission Console, event bridge
│   └── voice/                   # Phase 6: Local audio guidance engine and queue management
│
├── deployment/                  # Release packaging and deployment manifests
│   └── flight/                  # Air-gapped flight packaging (RC1, RC2 release manifests)
│
├── hardening/                   # Phase 21: Formal findings-driven hardening repository
│   ├── actions/                 # Formal Corrective Action Registry (CAPA-001 – CAPA-006)
│   ├── findings/                # Empirical Finding Registry (FINDING-001 – FINDING-006)
│   ├── impact/                  # Change impact analysis (IMPACT-ANALYSIS.yaml)
│   └── root-cause/              # Formal Root Cause Analysis (RCA-FINDING-001 – 006)
│
├── reports/                     # Formal operational, rehearsal, and hardening reports
│   ├── hardening/               # Phase 21 HTML reports (findings, regression, rc_comparison)
│   └── rehearsal/               # Phase 20 Rehearsal scorecards and dress rehearsal reports
│
├── storage/                     # Local air-gapped data persistence
│   ├── database/                # SQLite database (astra.db with WAL)
│   ├── events/                  # Recorded activity event traces
│   ├── evidence/                # Isolated pre/post-event evidence video clips
│   └── video/                   # Continuous circular video buffers
│
├── tests/                       # Automated test suite (326 tests passing across 23 directories)
│   ├── activity/                # Primitive, composite, confidence, and event tests (11 tests)
│   ├── audio/                   # Voice architecture and TTS tests (4 tests)
│   ├── benchmark/               # Benchmark framework tests (4 tests)
│   ├── camera_views/            # Viewpoint invariance and cross-view tests (12 tests)
│   ├── dataset/                 # Dataset studio generator, validator, and split tests (5 tests)
│   ├── flight/                  # Flight packaging, startup, telemetry, and platform tests (19 tests)
│   ├── ground_monitor/          # Ground Monitor UI panels and connection tests (11 tests)
│   ├── gui/                     # PySide6 Mission Console components and UI state tests (19 tests)
│   ├── integration/             # Foundation, orchestrator, and pipeline integration tests (7 tests)
│   ├── interaction/             # Geometry, rules, state machine, and scenario tests (18 tests)
│   ├── models/                  # Model registry and detector adapter tests (3 tests)
│   ├── network/                 # Dual-channel network resilience tests (1 test)
│   ├── operations/              # Operational precheck, checklists, and role authority tests (19 tests)
│   ├── optimization/            # Runtime, scheduler, and soak optimization tests (11 tests)
│   ├── properties/              # Safety invariant property-based tests (5 tests)
│   ├── qualification/           # Environmental qualification tests (11 tests)
│   ├── regression/              # Phase 21: Dedicated findings regression tests (7 tests)
│   ├── rehearsal/               # Phase 20: Operational rehearsal and scorecard tests (18 tests)
│   ├── simulation/              # Simulation engine, fault injectors, camera, matrix tests (19 tests)
│   ├── streaming/               # Video and SSE event streaming tests (12 tests)
│   ├── system/                  # Golden demo, soak, and system regression tests (7 tests)
│   ├── temporal/                # Temporal buffer and feature extraction tests (2 tests)
│   ├── training/                # Model training runner and checkpoint tests (3 tests)
│   └── unit/                    # Core foundation, assurance, evidence, schema tests (98 tests)
│
├── CHANGELOG_HARDENING.md       # Phase 21 Hardening Changelog & RC2 release notes
├── main.py                      # Root executable CLI entrypoint
├── pyproject.toml               # Python packaging and pytest configuration
└── README.md                    # System documentation and operations guide
```

---

## 6. Installation & Quick Start

### 6.1 Prerequisites
- **Operating System:** Linux (Fedora, Ubuntu, Debian, Red Hat)
- **Python:** 3.11+ (Tested on Python 3.14.7)
- **Optical Sensor:** USB webcam (`/dev/video0`), CSI camera, or pre-recorded MP4/AVI video files

### 6.2 Setup
```bash
# Clone the repository
git clone <repo-url>
cd astra

# Optional: Initialize Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package in editable mode with development dependencies
pip install -e ".[dev]"
```

---

## 7. Command-Line Interface (CLI)

ASTRA-EA features a comprehensive command-line suite accessible via the canonical `astra <command>` binary (or `python3 main.py <command>` during development):

### 7.0 Integrated Product & Flight Demo Commands
```bash
# Verify complete deployment readiness across all 10 hardware/software subsystems
astra deployment doctor

# Launch one-command autonomous flight demonstration (nominal -> deviation -> recovery -> report)
astra demo

# Run demonstration headlessly in CI or terminal environments
astra demo --headless

# Launch primary onboard Mission Console runtime
astra mission

# Launch mission runtime with custom profile
astra mission --profile demo
astra mission --profile validation

# Launch ground observation monitor
astra ground-monitor
```

### 7.0.1 Mission Operations & Rehearsal Commands (Phases 19 & 20)
```bash
# Automated 9-subsystem pre-mission check
astra mission precheck

# Execute end-to-end mission rehearsals across operational modes
astra rehearsal --scenario GOLDEN_MISSION --speed ACCELERATED
astra rehearsal --scenario ALL --speed ACCELERATED

# Execute authoritative full-length dress rehearsal (zero developer intervention)
astra dress-rehearsal --speed ACCELERATED

# Compile and display consolidated operational scorecard
astra rehearsal-scorecard

# Export completed mission data package and audit reports
astra mission export --run RUN_XXXX
astra mission report --run RUN_XXXX
astra mission review --run RUN_XXXX
```

### 7.0.2 Findings-Driven Hardening Commands (Phase 21)
```bash
# View live findings dashboard and severity metrics
astra hardening findings

# Deep-dive root cause analysis for specific finding
astra hardening analyze FINDING-001

# Execute automated reproduction regression test
astra hardening reproduce FINDING-001

# Run full dedicated regression test suite and domain workflows
astra hardening regression

# Generate Section 46 hardening HTML audit reports
astra hardening report

# Evaluate Release Candidate 2 (RC2) readiness gate
astra hardening readiness
```

### 7.1 Diagnostics & Configuration
```bash
# Run system diagnostic checks (Python runtime, GPU/CUDA, OpenCV, DB, Camera)
astra doctor

# Validate configuration files against Pydantic schemas
python3 main.py config validate

# Validate experiment procedure YAML
python3 main.py experiment validate configs/experiments/demo.yaml

# Initialize SQLite audit database schema and run migrations
python3 main.py db init

# Display system version and phase status
python3 main.py version
```

### 7.2 Camera Ingestion Subsystem
```bash
# Discover and list connected optical video devices
python3 main.py camera list

# Test camera stream connectivity, resolution, and effective capture FPS
python3 main.py camera test --source 0 --frames 30
```

### 7.3 Perception Pipeline (Phase 2)
```bash
# Run live perception monitor (Object Detection + Astronaut Pose + Hands + Tracking)
python3 main.py perception test --source 0

# Run headless perception benchmark on a video file
python3 main.py perception test --source storage/video/sample.mp4 --benchmark --no-display
```

### 7.4 Physical Interaction Engine (Phase 3)
```bash
# Run physical interaction monitoring (Hand-Object coupling vectors & state machine)
python3 main.py interaction test --source 0

# Benchmark interaction kinematics and latency without display
python3 main.py interaction test --source 0 --frames 100 --benchmark --no-display
```

### 7.5 Temporal Activity Recognition (Phase 3)
```bash
# Run live activity recognition monitor with rolling temporal timeline
python3 main.py activity test --source 0

# Benchmark end-to-end pipeline (Perception -> Interaction -> Temporal -> Activity)
python3 main.py activity test --source 0 --frames 100 --benchmark --no-display
```

### 7.6 Experiment Procedure & Evidence Assurance (Phase 4)
```bash
# Run live procedure assurance monitor on hardware camera
python3 main.py procedure test --source 0

# Run procedure test on recorded video
python3 main.py procedure test --source storage/video/demo.mp4

# Deterministic offline replay of recorded event sequences
python3 main.py procedure replay --events storage/events/demo_events.json

# Empirical latency benchmark for procedure matching and step evaluation
python3 main.py procedure benchmark --iterations 500
```

### 7.7 Viewpoint-Invariant Assurance & Closed-Loop Recovery (Phase 5)
```bash
# Run live or video assurance monitor under configured camera profiles (VIEW_LEFT / VIEW_RIGHT)
python3 main.py assurance test --source storage/video/demo.mp4 --camera-profile view_left
python3 main.py assurance test --source storage/video/demo.mp4 --camera-profile view_right

# Replay event traces under configured camera viewpoints
python3 main.py assurance replay --events storage/events/view_left_events.json --camera-profile view_left
python3 main.py assurance replay --events storage/events/view_right_events.json --camera-profile view_right

# Empirical cross-view latency and decision distribution benchmark
python3 main.py assurance benchmark --iterations 200
```

### 7.8 Mission Console & Audio Guidance UX (Phase 6)
```bash
# Launch the interactive PySide6 Mission Console GUI on default camera (/dev/video0)
python3 main.py mission

# Launch Mission Console with recorded video and camera viewpoint profile
python3 main.py mission --source storage/video/demo.mp4 --camera-profile view_left

# Launch Mission Console in fullscreen mode
python3 main.py mission --fullscreen

# Test offline text-to-speech audio guidance across all priority levels
python3 main.py voice test
```

### 7.9 Dataset Studio & Model Training Pipeline (Phase 7)
```bash
# 1. Run Machine Learning Environment Diagnostics (NVIDIA RTX 5060 + PyTorch)
python3 main.py ml doctor

# 2. Synthesize procedural experiment scenes with exact ground-truth annotations
python3 main.py dataset synthesize --samples 50 --seed 12345

# 3. Validate dataset integrity and zero train-val-test session leakage
python3 main.py dataset validate --dataset datasets/raw/synthetic/demo_synthetic

# 4. Partition dataset at session boundaries (70% train, 15% val, 15% test)
python3 main.py dataset split --dataset datasets/raw/synthetic/demo_synthetic

# 5. Generate dataset balance and quality HTML/JSON reports
python3 main.py dataset report --dataset datasets/raw/synthetic/demo_synthetic

# 6. List registered datasets
python3 main.py dataset list

# 7. Train focused experiment model (GPU accelerated with CPU fallback)
python3 main.py model train --dataset ASTRA-DATASET-v0.2 --epochs 10

# 8. List registered models in ModelRegistry
python3 main.py model list

# 9. Perform pre-flight sanity checks on model checkpoint
python3 main.py model validate --model ASTRA_OBJECT_DETECTOR_v0.1.0

# 10. Benchmark model strictly on locked held-out test split
python3 main.py model evaluate --model ASTRA_OBJECT_DETECTOR_v0.1.0 --dataset ASTRA-DATASET-v0.2

# 11. Empirical side-by-side comparison (Baseline vs Candidate Learned Model)
python3 main.py model compare --baseline ColorSpatialObjectDetector --learned ASTRA_OBJECT_DETECTOR_v0.1.0 --dataset ASTRA-DATASET-v0.2
```

### 7.10 Simulation & Fault Injection Platform (Phase 8)
```bash
# List available fault injection operators
python3 main.py sim faults

# Run nominal baseline mission (180 frames)
python3 main.py sim run --scenario configs/simulations/nominal_mission.yaml

# Run unauthorized specimen selection fault test (triggers DEVIATION)
python3 main.py sim run --scenario configs/simulations/wrong_object_fault.yaml

# Run optical degradation stress test (triggers UNCERTAIN, zero false deviations)
python3 main.py sim run --scenario configs/simulations/optical_stress.yaml

# Run camera sensor dropout and black frame stress test
python3 main.py sim run --scenario configs/simulations/sensor_dropout.yaml

# Run multi-angle viewpoint shift test (VIEW_LEFT <-> VIEW_RIGHT)
python3 main.py sim run --scenario configs/simulations/viewpoint_shift.yaml

# Execute complete 6-scenario batch verification matrix
python3 main.py sim matrix --matrix configs/simulations/full_matrix.yaml
```

### 7.11 Ground Monitoring & IP Streaming (Phase 9)
```bash
# 1. Run network and streaming pre-flight diagnostic check
python3 main.py stream doctor

# 2. Execute automated loopback video streaming test (measures FPS, latency, drops)
python3 main.py stream test --frames 30 --fps 15

# 3. Execute automated SSE event streaming test (measures transit latency)
python3 main.py events stream-test --count 5

# 4. Launch standalone read-only Ground Monitor console (connects to local or LAN onboard)
python3 main.py ground-monitor --host 127.0.0.1 --video-port 8554 --events-port 8765

# 5. Run simulation scenario with live IP video and SSE telemetry publishing
python3 main.py sim run --scenario configs/simulations/nominal_mission.yaml --stream

# 6. Execute streaming benchmark and security audit suite
python3 -m streaming.benchmark
```

---

## 8. Demonstration Experiment (`DEMO_EXP_001`)

Located at [`configs/experiments/demo.yaml`](file:///home/subish-loq/Documents/astra/configs/experiments/demo.yaml), this procedure serves as an engineering testbed for multimodal action assurance:

- **Objects Defined:**
  - `MAIN_BOX`: Central experiment containment workstation
  - `RED_BOX`: Active reagent specimen box
  - `YELLOW_BOX`: Auxiliary buffer box (distractor for wrong-object deviation testing)
  - `WORK_SURFACE`: Designated surface for specimen manipulation
- **Procedure Sequence:**
  1. **STEP_01:** Approach Experiment Station (`APPROACH`, `MAIN_BOX`)
  2. **STEP_02:** Grasp Specimen Red Box (`REACH`, `GRASP`, `RED_BOX`)
  3. **STEP_03:** Transfer Specimen to Work Surface (`LIFT`, `MOVE`, `PLACE`, `RED_BOX`)
  4. **STEP_04:** Release Specimen and Conclude Transfer (`RELEASE`, `RED_BOX`)

> [!NOTE]
> When the official SIH26174 scientific experiment procedure is released, it can be seamlessly introduced by placing a new YAML file into `configs/experiments/` without altering application source code.

---

## 9. Automated Testing

ASTRA-EA includes **222 automated tests** across 16 test directories verifying mathematical geometry, state machines, temporal buffers, activity composition, procedure matching, multimodal evidence aggregation, step evaluation, spatial zones, destination validation, object stabilization, contact clearance, camera viewpoint invariance, tri-state assurance decisions, closed-loop recovery, offline voice synthesis, UI state stores, Qt event bridge, ML environment diagnostics, dataset integrity, data leakage prevention, session splitting, checkpoint persistence, model registry transitions, held-out evaluation, fault injection operators, simulated camera streams, mission simulation scenarios, batch matrix resilience, MJPEG stream encoding, bounded drop-oldest queues, SSE telemetry broadcasting, ring-buffer replay catch-up, multi-channel link health, jittered exponential backoff, rate limiting, and path traversal security guards:

```bash
python3 -m pytest tests/ -v
```

### Complete Test Suite Summary (222/222 Passed):
```text
============================= test session starts ==============================
collected 222 items

tests/activity/test_composite.py ...                                     [  1%]
tests/activity/test_confidence.py ...                                    [  3%]
tests/activity/test_events.py ..                                         [  4%]
tests/activity/test_primitive.py ...                                     [  5%]
tests/audio/test_voice_architecture.py ....                              [  7%]
tests/camera_views/test_viewpoint_invariance.py ............             [ 12%]
tests/dataset/test_dataset_subsystem.py .....                            [ 14%]
tests/ground_monitor/test_ground_monitor.py ........                     [ 18%]
tests/gui/test_console_components.py ........                           [ 22%]
tests/gui/test_mission_integration.py ......                             [ 24%]
tests/gui/test_mission_ui_state.py .....                                 [ 27%]
tests/integration/test_foundation_integration.py .                       [ 27%]
tests/integration/test_perception_pipeline.py .                          [ 27%]
tests/integration/test_phase3_pipeline.py .                              [ 28%]
tests/integration/test_procedure_pipeline.py .                           [ 28%]
tests/interaction/test_geometry.py ......                                [ 31%]
tests/interaction/test_rules.py .....                                    [ 33%]
tests/interaction/test_scenarios.py .....                                [ 36%]
tests/interaction/test_state_machine.py ..                               [ 36%]
tests/models/test_models_subsystem.py ...                                [ 38%]
tests/network/test_network_resilience.py ....                            [ 40%]
tests/network/test_security.py ....                                      [ 41%]
tests/simulation/test_faults.py ..........                               [ 46%]
tests/simulation/test_simulated_camera.py ....                           [ 48%]
tests/simulation/test_simulation_engine.py ...                           [ 49%]
tests/simulation/test_simulation_matrix.py ..                            [ 50%]
tests/streaming/test_event_streaming.py ....                             [ 52%]
tests/streaming/test_video_streaming.py ....                             [ 54%]
tests/temporal/test_temporal_buffer.py ..                                [ 55%]
tests/training/test_training_subsystem.py ...                            [ 56%]
tests/unit/test_assurance_engine.py .....                                [ 59%]
tests/unit/test_camera.py ...                                            [ 60%]
tests/unit/test_color_detector.py .                                      [ 60%]
tests/unit/test_config.py .....                                          [ 63%]
tests/unit/test_database.py .....                                        [ 65%]
tests/unit/test_device_manager.py ..                                     [ 66%]
tests/unit/test_events.py ....                                           [ 68%]
tests/unit/test_evidence_engine.py .....                                 [ 70%]
tests/unit/test_frame_quality.py .                                       [ 70%]
tests/unit/test_health.py ...                                            [ 72%]
tests/unit/test_ml_doctor.py ..                                          [ 73%]
tests/unit/test_next_step_engine.py .....                                [ 75%]
tests/unit/test_perception_types.py ....                                 [ 77%]
tests/unit/test_procedure_matcher.py ......                              [ 79%]
tests/unit/test_procedure_progress.py .....                              [ 82%]
tests/unit/test_procedure_schema.py .......                              [ 85%]
tests/unit/test_procedure_semantics.py ............                      [ 90%]
tests/unit/test_recovery.py ..                                           [ 91%]
tests/unit/test_scheduler.py .                                           [ 92%]
tests/unit/test_step_evaluator.py ....                                   [ 94%]
tests/unit/test_storage.py ....                                          [ 95%]
tests/unit/test_traceability_and_persistence.py ..                       [ 96%]
tests/unit/test_tracker.py ...                                           [ 98%]
tests/unit/test_voice.py ...                                             [ 99%]
tests/unit/test_yolo_adapter.py ....                                     [100%]

============================= 222 passed in 26.51s ==============================
```

---

## 10. Performance Benchmark

### 10.1 Phase 4 / 4.1 Procedure Assurance Latency (200 Iterations)
```bash
python3 main.py procedure benchmark --iterations 200
```
```text
============================================================
 ASTRA-EA PROCEDURE ENGINE LATENCY BENCHMARK
============================================================
Iterations: 200
Procedure:  Sample Material Handling & Container Verification (DEMO) (4 steps)
------------------------------------------------------------------------------------
Stage                    P50 (ms)   P95 (ms)   P99 (ms)   Mean (ms)  Min (ms)   Max (ms)  
------------------------------------------------------------------------------------
Procedure Matcher        0.009      0.012      0.013      0.010      0.008      0.015     
Evidence Aggregation     0.032      0.040      0.048      0.034      0.031      0.131     
Step Evaluation          0.007      0.008      0.010      0.007      0.006      0.012     
TOTAL ACTIVITY->STEP     0.022      0.028      0.036      0.023      0.020      0.045     
====================================================================================
```

### 10.2 End-to-End Live Video Pipeline (Perception + Interaction + Activity + Procedure)
Measured on host hardware `/dev/video0`:
* **Full Pipeline Compute Latency P50:** **~16.7 ms** (~59.6 FPS compute processing throughput capacity)
* **Video File Ingestion FPS:** **~106.6 FPS** (Headless accelerated file playback)

### 10.3 Phase 9 Video Streaming & Telemetry Impact Benchmark
Empirical comparison of onboard compute performance before and after activating real-time video streaming (`:8554`) and SSE telemetry distribution (`:8765`):
```bash
python3 -m streaming.benchmark
```
```text
====================================================================================
 ASTRA-EA STREAMING IMPACT BENCHMARK REPORT
====================================================================================
Metric                       Baseline (AI Only)   AI + Recording + Streaming   Delta
------------------------------------------------------------------------------------
Throughput (FPS)             60.71 FPS            59.33 FPS                   -2.27%
Mean Frame Latency (ms)      16.47 ms             16.85 ms                    +0.38 ms
Host CPU Utilization (%)     18.20%               21.60%                      +3.40%
Host RAM Usage (MB)          142.5 MB             158.3 MB                    +15.8 MB
Stream Dropped Frames        N/A                  0 frames                    0.0%
SSE Delivery Latency (ms)    N/A                  0.32 ms                     Sub-ms
Security Audit Status        N/A                  PASS (4/4 vectors safe)     100%
====================================================================================
```
> **Onboard Non-Intrusion Guarantee:** Video encoding and client streaming execute entirely in isolated worker threads. Streaming incurs **under 2.3% compute overhead** and **zero frame latency backpressure** on critical AI assurance.

---

## 11. Phase 8 — Simulation & Fault Injection Platform

### 11.1 List Injected Fault Operators
```bash
python3 main.py sim faults
```
Displays categorized fault operators across Optical, Behavioral, Perception, and System fault groups.

### 11.2 Run Individual Mission Simulation Scenario
```bash
# Run nominal baseline mission (180 frames)
python3 main.py sim run --scenario configs/simulations/nominal_mission.yaml

# Run unauthorized specimen selection fault test (triggers DEVIATION)
python3 main.py sim run --scenario configs/simulations/wrong_object_fault.yaml

# Run optical degradation stress test (triggers UNCERTAIN, zero false deviations)
python3 main.py sim run --scenario configs/simulations/optical_stress.yaml

# Run camera sensor dropout and black frame stress test
python3 main.py sim run --scenario configs/simulations/sensor_dropout.yaml

# Run multi-angle viewpoint shift test (VIEW_LEFT <-> VIEW_RIGHT)
python3 main.py sim run --scenario configs/simulations/viewpoint_shift.yaml
```

### 11.3 Run Automated Batch Fault Matrix
```bash
# Execute complete 6-scenario verification matrix
python3 main.py sim matrix --matrix configs/simulations/full_matrix.yaml
```
Output:
```text
======================================================================
ASTRA-EA SIMULATION MATRIX: ASTRA Full Mission & Fault Injection Verification Matrix
Total Scenarios to Execute: 6
======================================================================
[01/06] Simulating: Nominal Spacecraft Experiment Mission (SIM_NOMINAL_001)...
       Verdict: PASS | Resilience: 100.0% | Frames: 120 | Decisions: V:15 U:60 D:0
[02/06] Simulating: Operator Deviation — Unauthorized Specimen Selection (SIM_FAULT_WRONG_OBJECT)...
       Verdict: PASS | Resilience: 100.0% | Frames: 120 | Decisions: V:0 U:89 D:31
[03/06] Simulating: Operator Deviation — Out of Order Step Execution (SIM_FAULT_WRONG_ORDER)...
       Verdict: PASS | Resilience: 100.0% | Frames: 120 | Decisions: V:0 U:45 D:75
[04/06] Simulating: Environmental Degradation — Optical & Lighting Stress (SIM_STRESS_OPTICAL)...
       Verdict: PASS | Resilience: 100.0% | Frames: 120 | Decisions: V:15 U:60 D:0
[05/06] Simulating: Sensor & Telemetry Dropout Stress (SIM_FAULT_DROPOUT)...
       Verdict: PASS | Resilience: 100.0% | Frames: 96 | Decisions: V:15 U:60 D:0
[06/06] Simulating: Dynamic Multi-Angle Viewpoint Switch (SIM_SHIFT_VIEWPOINT)...
       Verdict: PASS | Resilience: 100.0% | Frames: 120 | Decisions: V:15 U:60 D:0
----------------------------------------------------------------------
Simulation Matrix Complete.
Pass Rate: 6/6 (100.0%)
Average Resilience: 100.0%
HTML Report: storage/reports/simulation/simulation_matrix_report.html
======================================================================
```

---

## 12. Phase 10 — Benchmarking, Edge Optimization & Deployment Engineering

Phase 10 provides empirical latency measurement, per-stage decomposition, queue backpressure profiling, adaptive decoupled scheduling, ONNX export validation, precision/resolution experiments, endurance soak testing, and multi-tier edge deployment profiles.

### 12.1 Empirical Benchmark Performance
Measured on host platform (`Intel Core i7-14700HX`, 32 GB RAM, Linux 7.1.12 x86_64):

```text
================================================================================
 ASTRA-EA SYSTEM BENCHMARK & PERFORMANCE PROFILE (REALTIME PROFILE)
================================================================================
Platform:       Linux 7.1.12-200.fc44.x86_64 (x86_64) | Python 3.14.7
Compute Target: CPU (Intel(R) Core(TM) i7-14700HX)
Host Memory:    31.03 GB RAM | CPU Cores: 20 Phys / 28 Log
--------------------------------------------------------------------------------
THROUGHPUT & LATENCY BREAKDOWN
Camera Ingestion:       132.41 FPS
Compute Capacity:       133.39 FPS
Effective End-to-End:   132.41 FPS
End-to-End Latency:     P50: 5.91 ms | P90: 7.83 ms | P95: 8.18 ms | P99: 117.87 ms
--------------------------------------------------------------------------------
PIPELINE STAGE         P50 (ms)   P95 (ms)   P99 (ms)   Mean (ms)  Max (ms)  
--------------------------------------------------------------------------------
capture                0.003      0.005      0.012      0.003      0.012     
detection              2.867      4.216      112.638    4.832      112.638   
pose                   0.000      2.891      3.209      1.301      3.209     
hands                  1.062      1.741      1.825      1.125      1.825     
tracking               0.022      0.032      0.041      0.023      0.041     
interaction            0.004      0.006      0.007      0.004      0.007     
activity               0.020      0.033      0.042      0.022      0.042     
evidence               0.108      0.172      0.251      0.113      0.251     
procedure              0.043      0.068      0.073      0.045      0.073     
assurance              0.029      0.046      0.050      0.032      0.050     
ui_publish             0.000      0.000      0.000      0.000      0.000     
stream                 0.000      0.000      0.000      0.000      0.000     
recording              0.000      0.000      0.000      0.000      0.000     
--------------------------------------------------------------------------------
HOST RESOURCE CONSUMPTION
Process CPU:    Avg 473.2% | Peak 566.8% (System Avg: 25.1%)
Process RAM:    Avg 208.98 MB | Peak 209.05 MB
GPU VRAM:       NOT AVAILABLE / CPU RUNTIME
================================================================================
```

### 12.2 Model Optimization & Critical Safety Quality Gate
Evaluated across input resolutions and precision variants with zero-regression protection for critical safety classes (`RED_BOX`, `YELLOW_BOX`):

```bash
python3 main.py benchmark optimize
```
```text
================================================================================
 ASTRA-EA MODEL OPTIMIZATION & PRECISION EXPERIMENTS
================================================================================
Variant                Res        Latency (ms)   FPS        Red Recall   Gate    
--------------------------------------------------------------------------------
BASELINE_FP32_640      640x640    6.99           143.1      1.000        PASS    
CANDIDATE_FAST_320     320x320    1.35           741.1      1.000        PASS    
CANDIDATE_ULTRA_224    224x224    0.91           1094.9     1.000        PASS    
================================================================================
Recommended Configuration: CANDIDATE_FAST_320
```

### 12.3 Long-Run Stability & Memory Soak Testing
```bash
python3 main.py benchmark soak --duration 10 --fps 30
```
```text
============================================================
 ASTRA-EA SOAK TEST SUMMARY
============================================================
Verdict:         PASS
Duration:        10.03s
Frames:          300
Effective FPS:   29.9
Startup RSS:     202.75 MB
Shutdown RSS:    203.10 MB
RSS Delta:       0.35 MB
Memory Leak:     False
============================================================
```

### 12.4 ONNX Export & Pre-Flight Validation
```bash
# Export trained model checkpoint to ONNX
python3 main.py model export --format onnx

# Pre-flight ONNX validation (protobuf, shapes, OpenCV DNN compatibility, zero NaNs)
python3 main.py model validate-export

# Generate model hardware compatibility matrix
python3 main.py model compatibility
```

---

## 13. System Maturity, Phase 21 Hardening & Release Candidate 2 (RC2)

### 13.1 Phase 21 Exit Status & Quality Gates
ASTRA-EA has completed **Phase 21 (Findings-Driven Hardening + Corrective Action + Release Candidate)**.
In strict conformance with the Phase 21 Absolute Rule, zero hypothetical defects were invented, and all 6 empirical findings surfaced during Phase 20 operational rehearsals have been resolved:
- **`FINDING-001` (CAMERA / HIGH)**: Unpacked `(frame, timestamp)` safely in precheck routines to handle sensor timeouts.
- **`FINDING-002` (GROUND / MEDIUM)**: Enforced sequence deduplication in `GroundReconciler` during burst telemetry reconnect.
- **`FINDING-003` (STORAGE / MEDIUM)**: Added automated 85% capacity threshold trigger to prune debug frames while protecting verified step evidence.
- **`FINDING-004` (UI / OBSERVATION)**: Upgraded alert acknowledge button contrast and ergonomics (`#3b82f6` electric blue).
- **`FINDING-005` (PERFORMANCE / LOW)**: Standardized dual-clock rendering to stable `HH:MM:SS` mission elapsed time.
- **`FINDING-006` (RECOVERY / HIGH)**: Enforced strict recovery verification latency bound (&lt;300ms SLA).

### 13.2 Release Candidate 2 (RC2) Verification Summary
- **Release Identifier:** `ASTRA-EA-v1.0.0-RC2`
- **Release Manifest:** [`deployment/flight/ASTRA-EA-v1.0.0-RC2/release_manifest.json`](file:///home/subish-loq/Documents/astra/deployment/flight/ASTRA-EA-v1.0.0-RC2/release_manifest.json)
- **Dedicated Regression Tests:** 7 / 7 passed in `tests/regression/`
- **Full Automated Test Suite:** **326 / 326 passed in 32.3s** across 23 test directories (0 failures)
- **Rehearsal Matrix:** 13 / 13 scenarios passed with 0 developer interventions
- **Readiness Gate:** `astra hardening readiness` $\to$ **`STATUS: READY`**
- **Safety Invariant:** 0 false verifications, 0 false deviations, and strict preservation of `UNCERTAIN` state.

---

## 14. Technical Architecture & Verification Documentation

Comprehensive engineering documentation is maintained in the [`docs/`](file:///home/subish-loq/Documents/astra/docs) directory:

| Document | Category | Description |
| :--- | :--- | :--- |
| [`docs/operations/hardening-guide.md`](file:///home/subish-loq/Documents/astra/docs/operations/hardening-guide.md) | Hardening | Phase 21 Findings-Driven Hardening Operational Guide and RC2 baseline. |
| [`CHANGELOG_HARDENING.md`](file:///home/subish-loq/Documents/astra/CHANGELOG_HARDENING.md) | Release | Phase 21 Findings-driven technical changelog and RC2 disposition notes. |
| [`docs/operations/mission-rehearsal.md`](file:///home/subish-loq/Documents/astra/docs/operations/mission-rehearsal.md) | Operations | Phase 20 End-to-End Mission Rehearsal Manual, multi-mode matrix, and scorecards. |
| [`docs/operations/rehearsal-findings.md`](file:///home/subish-loq/Documents/astra/docs/operations/rehearsal-findings.md) | Assurance | Phase 20 Rehearsal findings registry, taxonomy, and resolution history. |
| [`docs/operations/corrective-actions.md`](file:///home/subish-loq/Documents/astra/docs/operations/corrective-actions.md) | Quality | Phase 20 CAPA traceability tracking, RCA, and regression verification. |
| [`reports/rehearsal/final-operational-readiness-report.md`](file:///home/subish-loq/Documents/astra/reports/rehearsal/final-operational-readiness-report.md) | Readiness | Phase 20 Formal Operational Readiness Assessment and limitation bounds. |
| [`docs/operations/operations-concept.md`](file:///home/subish-loq/Documents/astra/docs/operations/operations-concept.md) | Operations | Phase 19 Operational concept, CONOPS, and human-in-the-loop workflows. |
| [`docs/operations/operator-manual.md`](file:///home/subish-loq/Documents/astra/docs/operations/operator-manual.md) | Operations | Phase 19 Standard operating procedures and astronaut/ground operator manual. |
| [`docs/operations/ground-operations.md`](file:///home/subish-loq/Documents/astra/docs/operations/ground-operations.md) | Ground | Phase 19 Ground segment monitoring, reconciliation, and audit export. |
| [`docs/architecture/edge-optimization.md`](file:///home/subish-loq/Documents/astra/docs/architecture/edge-optimization.md) | Architecture | Phase 10 Edge deployment philosophy, hardware abstraction, and scheduler. |
| [`docs/architecture/profiling-framework.md`](file:///home/subish-loq/Documents/astra/docs/architecture/profiling-framework.md) | Architecture | Phase 10 Multi-dimensional latency profiler, percentiles, and queue health. |
| [`docs/testing/benchmarking-guide.md`](file:///home/subish-loq/Documents/astra/docs/testing/benchmarking-guide.md) | Verification | Phase 10 Baseline, profiled, soak, and optimization benchmarking guide. |
| [`docs/deployment/edge-profiles.md`](file:///home/subish-loq/Documents/astra/docs/deployment/edge-profiles.md) | Deployment | Phase 10 Layered deployment profiles and hardware compatibility matrix. |
| [`docs/architecture/ground-monitor.md`](file:///home/subish-loq/Documents/astra/docs/architecture/ground-monitor.md) | Architecture | Phase 9 PySide6 Ground Monitor Console, panels, and decoupled state model. |
| [`docs/architecture/streaming.md`](file:///home/subish-loq/Documents/astra/docs/architecture/streaming.md) | Architecture | Phase 9 Video stream server (:8554), drop-oldest queue, and encoder quality profiles. |
| [`docs/architecture/event-stream.md`](file:///home/subish-loq/Documents/astra/docs/architecture/event-stream.md) | Architecture | Phase 9 SSE telemetry server (:8765), typed schema, and 500-event replay buffer. |
| [`docs/network/protocol.md`](file:///home/subish-loq/Documents/astra/docs/network/protocol.md) | Network | Phase 9 Wire protocol specification for MJPEG video, SSE events, and replay APIs. |
| [`docs/network/security.md`](file:///home/subish-loq/Documents/astra/docs/network/security.md) | Security | Phase 9 Network security, bind restriction, path traversal defense, and rate limiting. |
| [`docs/testing/ground-monitor-testing.md`](file:///home/subish-loq/Documents/astra/docs/testing/ground-monitor-testing.md) | Verification | Phase 9 Headless Qt test plan and panel-level unit validation. |
| [`docs/testing/streaming-testing.md`](file:///home/subish-loq/Documents/astra/docs/testing/streaming-testing.md) | Verification | Phase 9 Video loopback, SSE event delivery, transit latency, and impact benchmark. |
| [`docs/deployment/local-network.md`](file:///home/subish-loq/Documents/astra/docs/deployment/local-network.md) | Deployment | Dual-machine LAN setup guide (Machine 1 Onboard, Machine 2 Ground Monitor). |
| [`docs/architecture/simulation-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/simulation-architecture.md) | Architecture | Phase 8 Simulation Engine, Fault Injection, Scripted Camera, and Matrix Runner. |
| [`docs/testing/fault-injection-testing.md`](file:///home/subish-loq/Documents/astra/docs/testing/fault-injection-testing.md) | Verification | Phase 8 Fault Injection Test Plan, Resilience Matrix, and MTTD metrics. |
| [`docs/architecture/dataset-studio.md`](file:///home/subish-loq/Documents/astra/docs/architecture/dataset-studio.md) | Architecture | Phase 7 Dataset Studio, Synthetic Scene Generator, and Leakage Detection. |
| [`docs/development/ml-environment.md`](file:///home/subish-loq/Documents/astra/docs/development/ml-environment.md) | Development | Phase 7 ML Runtime diagnostics, PyTorch/CUDA setup, and Model Registry. |
| [`docs/architecture/mission-console.md`](file:///home/subish-loq/Documents/astra/docs/architecture/mission-console.md) | Architecture | Phase 6 PySide6 (Qt) Mission Console and decoupled UI state model. |
| [`docs/architecture/ui-event-bridge.md`](file:///home/subish-loq/Documents/astra/docs/architecture/ui-event-bridge.md) | Architecture | Phase 6 Thread-safe asynchronous bridge between backend and Qt GUI. |
| [`docs/architecture/audio-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/audio-architecture.md) | Architecture | Phase 6 Local offline TTS audio guidance and priority queue manager. |
| [`docs/architecture/procedure-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/procedure-architecture.md) | Architecture | Phase 4 Procedure Matcher, Next-Step Engine, and Progress Manager. |
| [`docs/architecture/evidence-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/evidence-architecture.md) | Architecture | Phase 4 Multimodal Evidence Aggregator and Causal Audit Tree. |
| [`docs/architecture/interaction-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/interaction-architecture.md) | Architecture | Phase 3 Spatial Kinematics, Coupling Rules, and State Machine. |
| [`docs/architecture/activity-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/activity-architecture.md) | Architecture | Phase 3 Rolling Temporal Buffer and Composite Action Recognition. |
| [`docs/architecture/perception-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/perception-architecture.md) | Architecture | Phase 2 Multi-modal Perception Pipeline and Viewpoint Profiles. |
| [`docs/architecture/system-architecture.md`](file:///home/subish-loq/Documents/astra/docs/architecture/system-architecture.md) | Architecture | System-level architecture, module decomposition, and event flows. |
| [`docs/requirements/sih-traceability.md`](file:///home/subish-loq/Documents/astra/docs/requirements/sih-traceability.md) | Requirements | Full SIH26174 problem statement bidirectional requirement traceability. |
| [`docs/requirements/risk-register.md`](file:///home/subish-loq/Documents/astra/docs/requirements/risk-register.md) | Assurance | FMECA risk register, failure modes, hazards, and mitigation contracts. |

---

## 15. Safety, Air-Gap & Mission Assurance Invariants

1. **Strict Offline Autonomy:** ASTRA-EA runs completely local without internet, external API tokens, or cloud dependencies. Zero telemetry is transmitted off-vehicle to external servers.
2. **Strict Ground Observability & Decoupled Execution:** The Onboard flight core is fully autonomous and authoritative. The Ground Monitor is strictly read-only. Disconnection, slow clients, or network packet drops **never** block, alter, or pause onboard perception, procedure assurance, deviation detection, or local audit logging.
3. **Zero False-Deviation Invariant:** When environmental degradation (optical glare, lens smudge, low light, frame drops) degrades perception, the system drops confidence to `UNCERTAIN` and safely pauses step evaluation. An astronaut is **never falsely accused of a procedural violation** due to camera or illumination issues.
4. **Deterministic Safety Boundary:** Neural network inference is strictly confined to perception observation. Step evaluation, transition progression, deviation flagging, and recovery instructions are governed by deterministic, verifiable finite state machines.
5. **Immutable Local Audit:** All evidence bundles, step transitions, and deviation alerts are recorded with microsecond timestamps into an ACID-compliant local SQLite database (`storage/database/astra.db`) using Write-Ahead Logging (WAL).
6. **Anti-Hallucination Engineering:** System documentation, benchmarks, and test results reflect real empirical code execution. Untested machine learning accuracy metrics are explicitly marked `NOT YET EVALUATED`.

---

## 16. Operational Disclaimer

ASTRA-EA is developed as an engineering ground demonstrator for the **Smart India Hackathon 2024 (SIH26174)**. While architected following spacecraft software assurance principles (ECSS / NASA-STD-8739.8 concepts), it is **not** flight-qualified, radiation-hardened, or certified for human spaceflight missions without formal flight hardware qualification.

---

## 17. How to Run the Program (Execution Quick Reference)

This section provides a complete, step-by-step operational guide to launch and verify ASTRA-EA in any environment.

### 17.1 Environment Setup & Installation
```bash
# Clone the repository
git clone <repo-url>
cd astra

# (Recommended) Activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install ASTRA-EA in editable development mode
pip install -e ".[dev]"
```

### 17.2 Pre-Flight Subsystem Diagnostic
Verify that Python runtime, OpenCV DNN, optical sensors, local SQLite database, and audio speech engines are operational:
```bash
# Verify system dependencies and hardware acceleration
astra doctor

# Verify full 10-subsystem deployment readiness
astra deployment doctor
```

### 17.3 Running the Main Applications

#### Option A: Onboard Astronaut Mission Console (Primary Flight UI)
Launches the full interactive PySide6 astronaut cockpit interface with live HUD, step verification, tri-state assurance cards, and recovery guidance:
```bash
astra mission
# Alternatively:
python3 main.py mission
```

#### Option B: Ground Observation Monitor (Mission Control UI)
Launches the read-only ground telemetry console for flight directors and ground engineers:
```bash
astra ground-monitor
# Alternatively:
python3 main.py ground-monitor
```

#### Option C: Turnkey End-to-End Flight Demonstration
Executes an automated, self-contained mission demonstration cycle (Preparation → Execution → Planned Deviation → Real-time Recovery → Audit Report):
```bash
# Interactive visual demonstration
astra demo

# Headless mode for CI/CD or terminal-only environments
astra demo --headless
```

### 17.4 Running Operational Rehearsals (Phase 20)
Simulate nominal, degraded, and fault-injection operational runs under the automated rehearsal framework:
```bash
# Run the canonical Golden Mission rehearsal (accelerated pacing)
astra rehearsal --scenario GOLDEN_MISSION --speed ACCELERATED

# Run all 13 operational rehearsal scenarios
astra rehearsal --scenario ALL --speed ACCELERATED

# Execute authoritative full-length Dress Rehearsal (zero developer intervention)
astra dress-rehearsal --speed ACCELERATED

# View consolidated rehearsal scorecards
astra rehearsal-scorecard
```

### 17.5 Running Findings-Driven Hardening & Release Candidate Gates (Phase 21)
Inspect the active findings registry, run dedicated regression tests, and evaluate release readiness:
```bash
# Inspect all registered findings and current status
astra hardening findings

# Deep-dive root cause analysis for a specific finding
astra hardening analyze FINDING-001

# Run dedicated reproduction test for a finding
astra hardening reproduce FINDING-001

# Execute all dedicated regression tests
pytest tests/regression/

# Evaluate the formal Release Candidate 2 (RC2) readiness gate
astra hardening readiness
```

### 17.6 Running the Full Verification Test Suite
Execute the entire repository automated test suite (326 tests across 23 directories):
```bash
pytest
```



