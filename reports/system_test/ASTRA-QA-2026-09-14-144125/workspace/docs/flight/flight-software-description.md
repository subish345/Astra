# ASTRA-EA — Flight Software Description

### Document ID: `ASTRA-FSD-001`
**Milestone**: Phase 18 — Flight Integration Preparation + Onboard Software Packaging  
**Baseline**: `ASTRA-EA-QB-001` | **Software Version**: `v1.0.0-RC1`  

---

## 1. Architectural Architecture

ASTRA-EA operates as a modular, decoupled flight software pipeline executing on the target edge compute platform:

```
┌─────────────────────────────────────────────────────────────┐
│                    ASTRA-EA CORE PIPELINE                   │
│                                                             │
│   [CameraDriver] ──► [PerceptionEngine] ──► [TemporalAssurance]
│          ▲                    ▲                     │       │
│          │                    │                     ▼       │
│      [Watchdog]      [ModelIntegrity]          [Evidence]   │
│          │                                          │       │
│          ▼                                          ▼       │
│   [HealthMonitor] ◄────────────────────── [MissionState]    │
│          │                                          │       │
│          ▼                                          ▼       │
│   [TelemetryPub]                            [StorageManager]│
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Boot & Startup Sequence (Section 10 & 11)

Startup follows a deterministic 9-stage sequence managed by `FlightStartupSequence`:

1. **BOOT & SECURITY**: Inspects execution mode (`FLIGHT_INTEGRATION`). Enforces security policies (disables debug shortcuts, locks configuration).
2. **PLATFORM DETECTION**: Queries CPU, GPU, RAM, storage, and platform profile (`FLIGHT_TARGET_TBD`). Validates operating envelope.
3. **CONFIGURATION INTEGRITY**: Verifies procedure YAML syntax, schema, and step prerequisites.
4. **MODEL INTEGRITY**: Verifies ONNX model file existence, SHA-256 digest, metadata sidecar, and class mappings.
5. **STORAGE CHECK**: Confirms write access and verified storage capacity across all 5 flight partitions.
6. **CLOCK INITIALIZATION**: Initializes `MissionClock`, starts Mission Elapsed Time counter, calibrates external clock offset.
7. **CAMERA INITIALIZATION**: Initializes `CameraDriver`, validates sensor handshake, starts frame streaming.
8. **AI ENGINE INITIALIZATION**: Loads neural inference runtime, warms up execution graph, confirms fallback availability.
9. **HEALTH SELF-TEST**: Queries all 11 subsystems. If all report nominal, transitions system to state **`READY`**.

### Boot Failure States
If any stage fails, the startup sequence immediately halts and sets an explicit failure state:
- `BOOT_FAILURE`: Security violation or invalid host platform.
- `CONFIG_FAILURE`: Procedure YAML missing, corrupted, or unverified.
- `MODEL_FAILURE`: Checksum mismatch or unsupported model architecture.
- `STORAGE_FAILURE`: Storage partition in `CRITICAL` condition (>95% used).
- `CAMERA_FAILURE`: Sensor disconnected or video device unavailable.
- `CLOCK_FAILURE`: Timing driver fault.
- `HEALTH_FAILURE`: Subsystem self-test failure.

---

## 3. Operational Modes

### 3.1 IDLE / READY Mode
System has completed self-test. Camera is streaming, watchdog is active, waiting for uplink command `START_EXPERIMENT`.

### 3.2 EXPERIMENT ASSURANCE Mode
Autonomous assurance pipeline active:
- Video frames acquired via `CameraDriver.read_frame()`.
- Objects and crew interactions detected via `YOLOv8n / ONNX`.
- Temporal dwell constraints evaluated via `TemporalActivityTracker`.
- Multi-barrier evidence verified before step transition.
- Telemetry published at configured frequencies.

### 3.3 DEGRADED Mode
Engaged automatically when non-fatal anomalies occur:
- **Telemetry Disconnection**: Onboard assurance continues; telemetry logged locally.
- **Model Exception**: System engages heuristic fallback without crashing.
- **Camera Frame Drops**: Verification paused; system awaits valid frames.

### 3.4 PAUSED Mode
Procedure execution suspended either by operator uplink command `PAUSE` or automatically due to camera blackout or uncertain visual viewpoint.

### 3.5 SAFE SHUTDOWN
Triggered by operator command `STOP_EXPERIMENT` or watchdog critical timeout:
- Flushes active mission state to `flight_data/mission/active_mission_state.json`.
- Closes database connections and SQLite WAL logs cleanly.
- Releases camera hardware device.
- Emits final `HEALTH` telemetry packet indicating shutdown.
