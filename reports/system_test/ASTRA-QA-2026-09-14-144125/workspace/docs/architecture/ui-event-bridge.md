# ASTRA-EA — Backend-to-UI Event Bridge Architecture

## Thread-Safe Reactive Bridge for Spacecraft Mission Telemetry

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Objective & Design

In mission-critical spacecraft software, UI freezes or rendering stalls can disrupt operator situation awareness. The **UI Event Bridge** guarantees:
1. Complete asynchronous isolation of AI inference from Qt paint loops.
2. Type-safe delivery of procedural and assurance events.
3. Zero memory corruption or thread race conditions.

```text
┌────────────────────────────────────────┐
│      MissionPipelineWorker (QThread)    │
│  Perception -> Activity -> Assurance    │
└──────────────────┬─────────────────────┘
                   │ Emits Signals (Thread Boundary)
                   ▼
┌────────────────────────────────────────┐
│     BackendEventBridge (QObject)       │
│  sig_frame_ready, sig_step_progress,   │
│  sig_assurance_decision, sig_deviation │
└──────────────────┬─────────────────────┘
                   │ Dispatches Slots (Main Thread)
                   ▼
┌────────────────────────────────────────┐
│    MissionConsoleWindow (GUI Thread)   │
│  MissionUIState Updates -> Repaint     │
└────────────────────────────────────────┘
```

---

## 2. Event Signal Specifications

[`BackendEventBridge`](file:///home/subish-loq/Documents/astra/core/ui/bridge.py) defines the following canonical Qt signals:

```python
class BackendEventBridge(QObject):
    # Optical stream: (numpy_image, PerceptionState)
    sig_frame_ready = Signal(object, object)

    # Procedure progress state: (ProcedureState)
    sig_step_progress = Signal(object)

    # Formal assurance evaluation: (AssuranceDecision, Optional[ExperimentStep])
    sig_assurance_decision = Signal(object, object)

    # Multimodal corroboration bundle: (EvidenceBundle)
    sig_evidence_bundle = Signal(object)

    # Procedural deviation alert: (AssuranceDecision, ExperimentStep)
    sig_deviation = Signal(object, object)

    # Closed-loop recovery context: (RecoveryContext)
    sig_recovery = Signal(object)

    # Astronaut voice notification: (text_str, priority_name_str)
    sig_voice = Signal(str, str)

    # Subsystem telemetry heartbeat: (dict)
    sig_health = Signal(dict)

    # Chronological mission timeline entry: (event_type, title, description, severity)
    sig_timeline_event = Signal(str, str, str, str)

    # Overall session state: (status_str)
    sig_session_status = Signal(str)
```

---

## 3. UI State Store Mapping

The [`MissionUIState`](file:///home/subish-loq/Documents/astra/core/ui/state.py) acts as a passive, typed projection of the active session:

- **Step Transitions**:
  `apply_step_progress(curr, next, completed, status)` updates `step_statuses`, `current_step`, and `next_action`.
- **Assurance Outcomes**:
  `apply_assurance_decision(dec_type, conf, reasons)` updates visual banners and confidence readouts without modifying procedural state machine logic.
- **Deviations & Recovery**:
  `apply_deviation(dev_type, exp, det, reason, rec)` triggers the deviation banner and pre-populates recovery instruction cards.
- **Audit Logs**:
  `add_timeline_event(type, title, desc, sev)` appends immutable records to the mission audit trail.
