# ASTRA-EA

## Autonomous Spacecraft Experiment Assurance & Assistance

> **Tagline:** *"See. Understand. Verify. Assist. Record. — Locally, in Space."*  
> **Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
> **System Status:** Phase 0 + Phase 1 (Engineering Foundation & Core Contracts)  
> **Classification:** Engineering-Grade Ground Demonstrator (Not flight qualified or zero-g certified)

---

## 1. Executive Summary

**ASTRA-EA** is an offline, edge-AI experiment assurance platform designed to observe an astronaut performing a predefined scientific experiment through an onboard optical sensor. By evaluating hand-object interactions, physical kinematics, and temporal activity progression against an external, configuration-driven procedure, ASTRA-EA determines whether procedural steps are executed correctly, flags sequence deviations, provides real-time voice and visual guidance, and generates an immutable local audit record.

### Core Architectural Axiom
$$\text{Camera} \longrightarrow \text{Perception} \longrightarrow \text{Interaction} \longrightarrow \text{Activity} \longrightarrow \text{Evidence} \longrightarrow \text{Procedure} \longrightarrow \text{Assurance} \longrightarrow \text{Assistance} \longrightarrow \text{Logging}$$

> **AI observes. Evidence explains. The assurance engine decides. The assistance engine communicates. The logger records.**

Raw neural-network confidence is **never** permitted to become mission ground truth. Instead, decisions are grounded in explainable, multi-factor evidence bundles evaluated by a deterministic assurance engine.

---

## 2. Core Tri-State Assurance Model

The assurance engine yields strictly one of three discrete states:

1. **`VERIFIED`**: Activity matches the expected procedural step; all required evidence conditions (object presence, hand contact, relative motion, temporal window) are satisfied.
2. **`UNCERTAIN`**: Ambiguity detected due to temporary occlusion, missing hand/object keypoints, low lighting, or marginal confidence.
   - **Critical Rule:** `UNCERTAIN` is **NEVER** conflated with `DEVIATION`. Procedure verification safely pauses; the astronaut is never falsely penalized for visual ambiguity.
3. **`DEVIATION`**: Active procedural contradiction confirmed:
   - `SKIPPED_STEP`: Advancing to a subsequent step before completing the current step.
   - `WRONG_ORDER`: Executing steps in reverse or out of allowable transition topology.
   - `WRONG_OBJECT`: Interacting with an unauthorized object (e.g. Yellow Buffer Box instead of Red Specimen Box).
   - `INCOMPLETE_ACTION`: Abandoning an action before required temporal thresholds are met.
   - `TIMEOUT`: Exceeding maximum allotted step duration.

---

## 3. Strict Offline & Edge Autonomy

ASTRA-EA is engineered for air-gapped, high-reliability operation:
- **Zero Cloud Dependencies:** Operates without Internet connectivity. No OpenAI, AWS, Azure, Google Cloud, remote GPU inference, or online TTS APIs.
- **No LLM in Critical Assurance Path:** Procedural validation, sequence verification, and safety decisions are 100% deterministic and model-based.
- **Local Audio Guidance:** Offline text-to-speech engine (`pyttsx3`) with speech deduplication and cooldown intervals.
- **Local Persistence:** ACID-compliant SQLite audit store with Write-Ahead Logging (WAL) and local circular video buffer evidence capture.

---

## 4. Current Implementation Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **Phase 0 Documentation** | **COMPLETE** | Full system architecture, requirements, traceability, and risk register in `docs/`. |
| **Phase 1 Foundation** | **COMPLETE** | Repository structure, configuration loader, SQLite schema, event contracts, CLI, and test suite. |
| **Procedure Schema & Validator** | **COMPLETE** | Pydantic schema-driven experiment definitions; validated against `configs/experiments/demo.yaml`. |
| **Camera Ingestion Abstraction** | **COMPLETE** | `CameraSource` interface with `WebcamSource` and `VideoFileSource` implementations. |
| **Perception / Reasoning Contracts**| **COMPLETE** | Typed contracts and abstract base classes for Perception, Interaction, Activity, Evidence, Assurance, and Assistance. |
| **Subsystem Health Monitoring** | **COMPLETE** | `HealthManager` with component heartbeat registration and failure state degradation. |
| **Automated Testing Suite** | **COMPLETE** | 32 unit and integration tests passing cleanly. |
| **Deep Learning Perception Models**| **PLANNED (Phase 4)** | Object detection, pose estimation, and hand tracking will be integrated in subsequent phases. |
| **Mission Console GUI** | **PLANNED (Phase 11)** | High-density PySide6 space operations dashboard scheduled after core vision pipeline is validated. |

> [!IMPORTANT]
> **Anti-Hallucination Notice:** In strict adherence to project engineering principles, no AI predictions, confidence metrics, or detection accuracies are fabricated. All development doubles are explicitly tagged with `source = "STUB"`. The official SIH experiment sequence is not hardcoded; all procedures are loaded dynamically from YAML.

---

## 5. Repository Structure

```text
astra-ea/
├── apps/                        # Operational applications
│   ├── mission_console/         # Space operations PySide6 console (Phase 11)
│   ├── experiment_studio/       # Visual experiment definition authoring tool
│   ├── dataset_studio/          # Dataset curation and synthetic generation tool
│   ├── simulation_lab/          # Video replay and fault injection harness
│   └── ground_monitor/          # Remote local-network telemetry monitor
│
├── core/                        # Core application engine
│   ├── camera/                  # CameraSource abstraction, WebcamSource, VideoFileSource
│   ├── perception/              # Object, pose, and hand detection contracts and interfaces
│   ├── interaction/             # Hand-object spatial-temporal coupling contracts
│   ├── activity/                # Temporal window activity recognition contracts
│   ├── evidence/                # Multimodal corroboration evidence engine contracts
│   ├── procedure/               # Procedure schema, validator, and state machine
│   ├── assurance/               # Tri-state assurance engine and deviation classification
│   ├── assistance/              # Voice guidance and closed-loop recovery contracts
│   ├── mission/                 # SQLite database engine, migrations, and typed event models
│   ├── health/                  # Subsystem heartbeat registry and health status manager
│   ├── common/                  # Configuration management, structured logging, and constants
│   └── cli/                     # Command-line interface implementation
│
├── configs/                     # Centralized YAML configuration files
│   ├── experiments/             # Experiment procedures (e.g. demo.yaml)
│   ├── cameras/                 # Camera resolution and device settings (default.yaml)
│   ├── models/                  # Model checkpoints and inference parameters
│   └── system/                  # Global system configuration (system.yaml)
│
├── storage/                     # Local air-gapped data persistence
│   ├── database/                # SQLite database (astra.db)
│   ├── video/                   # Continuous circular video buffers
│   ├── evidence/                # Isolated pre/post-event evidence video clips
│   └── reports/                 # Generated audit and mission performance reports
│
├── docs/                        # Formal engineering documentation
│   ├── architecture/            # System architecture, data flow, contracts, tech stack
│   ├── requirements/            # Functional/non-functional requirements, traceability, risks
│   └── development/             # Developer setup, conventions, and workflows
│
├── tests/                       # Automated test suite
│   ├── unit/                    # Unit tests for config, schema, database, events, health, storage
│   └── integration/             # End-to-end foundation integration tests
│
├── main.py                      # Root executable entrypoint
├── pyproject.toml               # Python packaging and dependency specifications
└── README.md                    # Project overview and operations guide
```

---

## 6. Installation & Quick Start

### 6.1 Prerequisites
- Linux OS (Tested on Fedora Linux / Red Hat with Kernel 6.x)
- Python 3.11+ (Development system uses Python 3.14.7)
- OpenCV compatible camera (USB webcam, MIPI, or CSI) or recorded video files

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

### 6.3 Command-Line Interface (CLI)

ASTRA-EA provides comprehensive CLI commands via `main.py` (or the `astra` executable):

```bash
# 1. Run system diagnostics and verify environment health
python3 main.py doctor

# 2. Validate system and camera configuration files
python3 main.py config validate

# 3. Validate experiment procedure against Pydantic schema
python3 main.py experiment validate configs/experiments/demo.yaml

# 4. Initialize SQLite audit database schema and run migrations
python3 main.py db init

# 5. Test camera stream connectivity, resolution, and effective FPS
python3 main.py camera test --source 0 --frames 30

# 6. Display system version
python3 main.py version
```

---

## 7. Automated Testing

Run the complete test suite:
```bash
python3 -m pytest tests/ -v
```

Expected output:
```text
tests/integration/test_foundation_integration.py .                       [  3%]
tests/unit/test_camera.py ...                                            [ 12%]
tests/unit/test_config.py .....                                          [ 28%]
tests/unit/test_database.py .....                                        [ 43%]
tests/unit/test_events.py ....                                           [ 56%]
tests/unit/test_health.py ...                                            [ 65%]
tests/unit/test_procedure_schema.py .......                              [ 87%]
tests/unit/test_storage.py ....                                          [100%]
============================== 32 passed in 0.25s ==============================
```

---

## 8. Demonstration Experiment (`DEMO_EXP_001`)

Located at `configs/experiments/demo.yaml`, this procedure serves as an engineering testbed for multimodal action assurance:

- **Objects Defined:**
  - `MAIN_BOX`: Central experiment workstation
  - `RED_BOX`: Target specimen container
  - `YELLOW_BOX`: Auxiliary buffer container (distractor for wrong-object deviation testing)
  - `WORK_SURFACE`: Designated zone for specimen manipulation
- **Procedure Sequence:**
  1. **STEP_01:** Approach Experiment Station (`APPROACH`, `MAIN_BOX`)
  2. **STEP_02:** Grasp Specimen Red Box (`REACH`, `GRASP`, `RED_BOX`)
  3. **STEP_03:** Transfer Specimen to Work Surface (`LIFT`, `MOVE`, `PLACE`, `RED_BOX`)
  4. **STEP_04:** Release Specimen and Conclude Transfer (`RELEASE`, `RED_BOX`)

> [!NOTE]
> When the official SIH26174 scientific experiment procedure is released, it can be seamlessly introduced by placing a new YAML file into `configs/experiments/` without altering application source code.

---

## 9. Next Recommended Phase

**PHASE 2 — EXPERIMENT ENGINE & STATE MACHINE**
- Dynamic step transition state machine (`READY` $\to$ `MONITORING` $\to$ `IN_PROGRESS` $\to$ `VERIFYING` $\to$ `VERIFIED` $\to$ `NEXT_STEP`)
- Deviation transition triggers (`DEVIATION` $\to$ `ALERTING` $\to$ `RECOVERY` $\to$ `RECOVERY_VERIFYING`)
- Timeout handling and procedure completion checks
