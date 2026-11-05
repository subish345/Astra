# ASTRA-EA — Mission Console Architecture

## Phase 6 Mission Console & Astronaut User Experience

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Architectural Foundation & Non-Negotiable Rule

The **Mission Console** is strictly a **PRESENTATION AND INTERACTION LAYER**.

```text
Perception → Interaction → Activity → Evidence → Procedure → Assurance → Events → MISSION CONSOLE
                                                                              ↘ AUDIO / VOICE
```

### Absolute Operational Rule:
The GUI **does NOT** contain:
- Object detection or spatial keypoint tracking logic
- Activity classification or temporal state machine logic
- Procedural step-matching rules
- Deviation detection rules or error thresholds
- Closed-loop recovery decision logic
- Composite confidence score calculations

The Mission Console consumes typed mission events and renders state. **The UI never decides mission truth.**

---

## 2. Technology & Deployment Model

- **Framework**: `PySide6` (Qt 6.11.2).
- **Environment**: 100% local, air-gapped spacecraft execution. Zero browser, Electron, or cloud dependencies.
- **Rendering**: Supports native Wayland / X11 display servers and headless offscreen rendering (`QT_QPA_PLATFORM=offscreen`) for automated test pipelines.
- **Responsive Layouts**: Designed to adapt fluidly across standard mission displays (1280×720, 1366×768, 1920×1080) with full windowed, maximized, and fullscreen (`F11`) modes.

---

## 3. UI Hierarchy & Visual Strategy

Visual hierarchy is strictly mapped to astronaut operational priorities:

| Priority | Level | Visual Component | Description |
|:---:|---|---|---|
| **Priority 1** | **Critical State** | `StatusPanel` (Red Banner) | Deviations (`WRONG_OBJECT`, `SKIPPED_STEP`), active recovery directives, or hardware failures. |
| **Priority 2** | **Current Task** | `StepPanel` (Blue Card) | Active step name, elapsed time, expected action, and prominent **Next Action Guidance**. |
| **Priority 3** | **Assurance Verification** | `StatusPanel` (Green/Amber) | `VERIFIED` confirmations, `UNCERTAIN` notices (never called error), and progress timeline. |
| **Priority 4** | **Audit & Telemetry** | `EvidencePanel`, `TimelinePanel`, `HealthPanel` | Corroborating multimodal evidence, chronological event logs, FPS, latency, and CPU/RAM usage. |

---

## 4. Subsystem Components

```text
core/ui/
├── theme.py                 # Color tokens, space dark mode stylesheets, status badges
├── state.py                 # MissionUIState (typed presentation data store)
├── bridge.py                # BackendEventBridge (thread-safe Qt Signal bus)
├── worker.py                # MissionPipelineWorker (QThread background runner)
├── panels/
│   ├── video_panel.py       # Camera feed, overlay toggles, debug modes
│   ├── step_panel.py        # Current Step & Next Action Card
│   ├── progress_panel.py    # Vertical step timeline (✓ ● ○)
│   ├── status_panel.py      # VERIFIED / UNCERTAIN / DEVIATION / RECOVERY cards
│   ├── evidence_panel.py    # Multimodal evidence corroboration
│   ├── timeline_panel.py    # Filterable chronological event log
│   ├── health_panel.py      # System health & resource telemetry
│   └── session_bar.py       # Header, offline badge, experiment selector, controls
├── views/
│   ├── console_view.py      # Primary Mission Console view
│   ├── evidence_view.py     # Full evidence audit inspection
│   ├── timeline_view.py     # Mission timeline analysis
│   ├── health_view.py       # Full system diagnostic screen
│   └── settings_view.py     # Camera, voice, and overlay configuration
└── main_window.py           # MissionConsoleWindow (Main Qt Shell)
```

---

## 5. Threading & Decoupling

Zero inference or heavy math is executed on the Qt UI thread.
1. **Background Pipeline Thread (`MissionPipelineWorker: QThread`)**: Ingests frames, executes YOLO/Color detection, pose estimation, spatial interaction, activity evaluation, evidence aggregation, and assurance decisions.
2. **Signal Bus (`BackendEventBridge: QObject`)**: Marshals typed objects across the thread boundary via Qt signals (`sig_frame_ready`, `sig_step_progress`, `sig_assurance_decision`, `sig_deviation`, `sig_recovery`, `sig_health`).
3. **UI Main Thread**: Updates widgets reactively in sub-millisecond slot executions, guaranteeing responsive 60 FPS user interaction.
