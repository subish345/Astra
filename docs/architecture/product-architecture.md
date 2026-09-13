# ASTRA-EA Integrated Product Architecture

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Product Version**: `v1.0.0`  
**Deployment Model**: 100% Offline Air-Gapped Spacecraft Core Runtime + Remote Ground Monitoring

---

## 1. Executive Architecture Overview

In Phase 11, ASTRA-EA transitioned from a collection of modular AI subsystems into **One Unified Product Runtime**. The system provides real-time, closed-loop assurance for on-board biological and physical science experiments on space stations and deep-space habitats.

```text
                                  ASTRA-EA
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
            ONBOARD CORE                              GROUND
                 │                                       │
      ┌──────────┼───────────┐                           │
      │          │           │                           │
  Optical AI  Pipeline   Mission UI                      │
    Sensor   Runtime       Console                       │
      │          │           │                        Ground
      │      ┌───┴────┐      │                        Monitor
      │      │        │      │                           │
      │  Perception  │      │                           │
      │      Activity │      │                           │
      │      Procedure│      │                           │
      │      Assurance│      │                           │
      │      Recovery │      │                           │
      │      └────────┘      │                           │
      │                      │                           │
      └──────────┬───────────┘                           │
                 │                                       │
       Authoritative Mission State                       │
                 │                                       │
        ┌────────┼─────────┐                             │
        │        │         │                             │
     SQLite    Video    Evidence                         │
     Storage  Recorders  Store                           │
        │        │         │                             │
        └────────┼─────────┘                             │
                 │                                       │
                 └──────────── IP Video & Events ────────┘
                               (Isolated Non-Blocking)
```

---

## 2. Core Architectural Pillars

### 2.1 Single Source of Truth
No UI widget, background worker, or ground monitor maintains an independent or divergent state. State authority is strictly partitioned:
* **Mission Lifecycle**: Authoritative 16-state finite state machine (`core/mission/lifecycle.py`).
* **Experiment Progress**: Directed procedure progress manager (`core/procedure/progress.py`).
* **Assurance & Recovery**: Invariant tri-state assurance engine (`core/assurance/engine.py`) and closed-loop guidance state machine (`core/assistance/recovery.py`).
* **Health**: Centralized health aggregator enforcing critical vs non-critical failure policies (`core/health/aggregator.py`).

### 2.2 Mission Lifecycle State Machine
```text
  BOOT ──► INITIALIZING ──► SELF_TEST ──► READY ──► STARTING ──► RUNNING
                                 │                            ▲   │   ▲
                                 ▼                            │   ▼   │
                              FAILED                        PAUSED ◄──┤
                                 ▲                            │       │
                                 │                            ▼       ▼
                               ABORTED ◄── ABORTING ◄──── DEGRADED / RECOVERY
                                                              │
                                                              ▼
                                                         COMPLETING ──► COMPLETED ──► SHUTTING_DOWN ──► STOPPED
```

### 2.3 Unified Non-Blocking Event Bus & Traceability
All subsystem decisions and operational milestones emit typed envelope events (`core/mission/event_bus.py`) with complete correlation headers:
```json
{
  "event_id": "EVT_3A89F102",
  "event_type": "DeviationDetected",
  "sequence_num": 142,
  "timestamp": "2026-09-13T12:47:22.105Z",
  "context": {
    "mission_id": "ASTRA_MISSION",
    "run_id": "RUN_20260913_124722",
    "experiment_id": "DEMO_EXP_001",
    "step_id": "STEP_02"
  },
  "severity": "WARNING",
  "payload": {
    "step": "STEP_02",
    "reasons": ["Manipulated incorrect object: BLUE_BOX instead of required YELLOW_BOX"],
    "recovery": {
      "recommendation": "Release BLUE_BOX and acquire YELLOW_BOX"
    }
  }
}
```

### 2.4 Reproducible Run Package
Every experiment execution produces a standardized run package under `data/runs/RUN_XXXX/`:
1. `config_snapshot.yaml`: Effective runtime configuration snapshot.
2. `model_snapshot.json`: Exact detector weights, runtime engine, input resolution, and confidence thresholds.
3. `version_metadata.json`: ASTRA-EA release version, Git commit hash, Python version, platform architecture.
4. `run_metadata.json`: Mission start/end timestamps, duration, overall status.
5. `events.json`: Complete sequence of correlated mission events.
6. `timeline.json`: Human-readable operator timeline records.
7. `health_summary.json`: Health status across all 11 monitored subsystems.
8. `mission_report.json` & `mission_report.html`: Self-contained audit reports.

---

## 3. Subsystem Criticality & Graceful Degradation

| Subsystem | Criticality | Behavior on Failure |
| :--- | :--- | :--- |
| **Optical Camera** | `CRITICAL` | Verification pauses immediately (`PAUSED`). Stale frames are rejected. |
| **Perception AI** | `CRITICAL` | Mission transitions to `DEGRADED`. Falls back to baseline detector if configured. |
| **Procedure Engine** | `CRITICAL` | Mission blocks execution. Step transitions halted. |
| **Assurance Engine** | `CRITICAL` | Mission blocks execution. Safety verification halted. |
| **Evidence Store** | `CRITICAL` | Mission pauses if audit artifacts cannot be written to disk. |
| **SQLite Database** | `CRITICAL` | Enters degraded state; event queue buffers in memory. |
| **Storage Subsystem** | `IMPORTANT` | Warns before 2 GB limit. Continues with alert flag. |
| **Local Recording** | `IMPORTANT` | AI continues; recording flagged as degraded. |
| **Offline Voice (TTS)**| `OPTIONAL` | Audio silenced; visual HUD guidance remains 100% active. |
| **IP Video Streamer** | `OPTIONAL` | Local mission unaffected; network stream marked offline. |
| **Ground Monitor** | `OPTIONAL` | Local crew console unaffected; ground observer reconnects seamlessly. |
