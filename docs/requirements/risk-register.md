# ASTRA-EA Engineering Risk Register

## 1. Risk Assessment Framework
Risks are evaluated on a 5x5 matrix combining Likelihood (1 = Rare, 5 = Almost Certain) and Severity/Impact (1 = Negligible, 5 = Catastrophic).

---

## 2. Active Risk Register

### R001 — Insufficient Real Microgravity / Spacecraft Training Data
- **Severity**: High (4) | **Likelihood**: High (4) | **Risk Score**: 16 (High)
- **Description**: Public datasets for scientific laboratory experiments in microgravity are scarce; training solely on terrestrial datasets may result in domain shift.
- **Mitigation**:
  1. Implement a hybrid synthetic dataset generator that varies lighting, object orientations, and camera angles.
  2. Clearly partition and tag datasets as `SYNTHETIC` vs `REAL` to avoid data contamination.
  3. Support focused local recording via webcam with varied background clutter.

### R002 — Severe Object and Hand Occlusion During Experimentation
- **Severity**: Medium (3) | **Likelihood**: High (4) | **Risk Score**: 12 (High)
- **Description**: Astronaut hands, tool racks, or body posture frequently occlude small containers or test tubes.
- **Mitigation**:
  1. Multi-object tracking with persistent state and track retention across temporary occlusions up to 1.5 seconds.
  2. Implement an explicit `UNCERTAIN` state rather than penalizing an occlusion as a procedure `DEVIATION`.
  3. Trigger non-intrusive voice guidance ("Verification paused: please keep experiment area visible").

### R003 — False Sequence Deviation Alerts (False Positives)
- **Severity**: High (4) | **Likelihood**: Medium (3) | **Risk Score**: 12 (High)
- **Description**: Premature deviation alerts erode astronaut trust and interrupt scientific workflow.
- **Mitigation**:
  1. Enforce multi-factor evidence bundles requiring object confidence, hand contact, physical motion, and temporal consistency.
  2. Never decide procedure state based on a single frame; enforce temporal windows (5–30 sec).
  3. Require confidence thresholds and evidence score gates before raising alerts.

### R004 — Spurious Activity Classification
- **Severity**: Medium (3) | **Likelihood**: Medium (3) | **Risk Score**: 9 (Medium)
- **Description**: Transient hand gestures or background movements misclassified as experiment actions.
- **Mitigation**:
  1. Spatial coupling verification: an action is only classified as `GRASP` or `MOVE` if the object bounding box moves synchronously with the hand trajectory.
  2. Temporal smoothing and interaction state progression (`APPROACH` $\to$ `CONTACT` $\to$ `GRASP` $\to$ `MOVE`).

### R005 — Camera Stream Degradation or Hardware Disconnection
- **Severity**: Critical (5) | **Likelihood**: Low (2) | **Risk Score**: 10 (Medium)
- **Description**: USB cable detachment, driver crash, or dropped frames in the video pipeline.
- **Mitigation**:
  1. Isolated `CameraSource` abstraction with automated reconnection retry loops.
  2. System transitions gracefully into `DEGRADED` health state; procedure verification safely pauses without throwing uncaught runtime exceptions.

### R006 — Accidental Cloud Dependency or Network Loss Failure
- **Severity**: Critical (5) | **Likelihood**: Low (2) | **Risk Score**: 10 (Medium)
- **Description**: Third-party packages attempting outbound telemetry, online license checks, or remote API calls.
- **Mitigation**:
  1. Strict offline-first architecture policy.
  2. Automated test suite executable in air-gapped environment (disconnected network).
  3. No remote LLM, web TTS, or cloud GPU endpoints anywhere in the critical path.

### R007 — Inference Latency Exceeding Real-Time Budget
- **Severity**: Medium (3) | **Likelihood**: Medium (3) | **Risk Score**: 9 (Medium)
- **Description**: Heavy convolutional or transformer models causing frame queue backup and laggy guidance.
- **Mitigation**:
  1. Use lightweight YOLO-family detectors, lightweight pose estimators, and CPU-efficient tracking.
  2. Asynchronous processing with bounded circular frame buffers (bounded queue dropping stale frames if necessary).
  3. Continuous latency telemetry logged via `HealthManager`.

### R008 — Undisclosed Official SIH Procedure Changes
- **Severity**: Medium (3) | **Likelihood**: High (4) | **Risk Score**: 12 (High)
- **Description**: Official SIH experiment details may change or require different objects/actions upon release.
- **Mitigation**:
  1. Complete decoupling of procedure logic from application source code.
  2. All steps, objects, actions, evidence criteria, and recovery instructions specified via YAML schema.
  3. Zero hardcoding of steps in Python code.

### R009 — Data Leakage Across Training, Validation, and Test Splits
- **Severity**: High (4) | **Likelihood**: Medium (3) | **Risk Score**: 12 (High)
- **Description**: Random frame-level train/test splitting inflates accuracy due to high correlation between adjacent video frames.
- **Mitigation**:
  1. Enforce strict session-level or recording-level dataset splitting.
  2. Validation and test splits must only contain unseen sessions and varied participants.

### R010 — Excessive Software Complexity and Monolithic Architecture
- **Severity**: High (4) | **Likelihood**: Medium (3) | **Risk Score**: 12 (High)
- **Description**: Intertwining computer vision, Qt GUI, SQLite, and audio into tightly coupled modules.
- **Mitigation**:
  1. Strict modular contracts and abstract base classes (`core/perception/`, `core/assurance/`, `core/assistance/`, etc.).
  2. Comprehensive automated unit testing per isolated layer.
  3. Headless CLI execution mode (`astra doctor`, `astra db init`, `astra experiment validate`) independent of GUI.
