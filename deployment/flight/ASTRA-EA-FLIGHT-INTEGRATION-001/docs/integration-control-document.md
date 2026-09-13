# ASTRA-EA — Interface Control Document (ICD)

### Document ID: `ASTRA-ICD-FLIGHT-001`
**Milestone**: Phase 18 — Flight Integration Preparation + Onboard Software Packaging  
**System Baseline**: `ASTRA-EA-QB-001` | **Software Baseline**: `v1.0.0-RC1`  
**Standard Compliance**: ECSS-E-ST-40C / NASA-STD-8739.8  
**Applicability**: Spacecraft Bus & Payload Flight Software Integration  

---

## 1. Scope & System Overview

This document specifies the mechanical, electrical, data, timing, command, and telemetry interface contracts between the **ASTRA-EA Payload Flight Software** and the **Host Spacecraft / Vehicle Bus**.

In accordance with Phase 18 Absolute Rules:
> [!NOTE]
> Physical bus transceiver hardware, exact packet encapsulation headers, and bus electrical characteristics remain **TBD / INTERFACE PLACEHOLDERS** until specified by the target spacecraft program authority. Logical data contracts are fully specified herein.

---

## 2. Hardware & Platform Interface Contracts

```
┌─────────────────────────────────────────────────────────────┐
│                    SPACECRAFT VEHICLE                       │
│                                                             │
│   28V DC Power Bus (18V-36V) ──► Payload Power Input        │
│   Optical Field of View      ──► M12 / COTS Lens Sensor     │
│   Spacecraft Clock / PPS     ──► MissionClock Synchronizer  │
│   Spacecraft Data Bus (TBD)  ──► Uplink / Downlink Channels │
│                                                             │
│               ASTRA-EA FLIGHT SOFTWARE                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Power Interface (`IF-PWR-01`)
* **Nominal Bus Voltage**: 28.0 V DC (Spacecraft standard).
* **Operating Float Envelope**: 18.0 V to 36.0 V DC.
* **Maximum Power Dissipation**: $\le 20.0$ W (NVIDIA Orin NX 20W profile).
* **Brownout Ride-Through**: $\ge 50$ ms without processor reset.
* **Power Failure States**:
  - `POWER_NOMINAL`: Bus voltage $22\text{V} \le V \le 34\text{V}$.
  - `POWER_WARNING`: Voltage float $18\text{V} \le V < 22\text{V}$ or $34\text{V} < V \le 36\text{V}$.
  - `POWER_CRITICAL`: Voltage $< 18\text{V}$, non-essential telemetry degraded.
  - `POWER_LOSS`: Impending shutdown, atomic state flush executed.
  - `POWER_RECOVERY`: Voltage restored, boot evaluation initiates restart policy.

### 2.2 Optical Sensor Interface (`IF-OPT-01`)
* **Sensor Type**: Sony IMX477 1/2.3" CMOS (or spacecraft-qualified equivalent).
* **Native Ingestion**: POSIX V4L2 / GMSL2 (1080p @ 30 FPS).
* **Driver Contract**: `core.platform.camera.CameraDriver`.
* **Failure Interlock**: On camera loss (`CAMERA_FAILED`), perception transitions to `PERCEPTION_DEGRADED` and verification transitions to `PROCEDURE_VERIFICATION_PAUSED`. Stale frames are never used for new assurance decisions.

### 2.3 Timing & Synchronization Interface (`IF-TIME-01`)
* **Timing Contract**: `core.platform.clock.MissionClock`.
* **Supported Clocks**:
  - Wall-Clock ISO 8601 UTC (`now_utc_iso()`).
  - Monotonic System Timer (`now_monotonic()`).
  - Mission Elapsed Time (`get_met_seconds()`).
  - Synchronized Frame Timestamp (`stamp_frame()`).
  - Sequenced Event Timestamp (`stamp_event()`).
* **Spacecraft Synchronization**: Calibrated offset via `set_clock_offset_ms()`. Physical 1-PPS synchronization line: **TBD**.

---

## 3. Logical Telemetry Interface (`IF-TELEM-01`)

Telemetry packets are emitted as standardized JSON/NDJSON records categorized by function:

| Telemetry Stream | Frequency | Fields | Target Interface |
| :--- | :--- | :--- | :--- |
| **`HEALTH`** | 1.0 Hz (TBD) | Camera status, model status, storage status, CPU/GPU die temps, power voltage | Spacecraft Housekeeping Bus |
| **`MISSION`** | 1.0 Hz (TBD) | Experiment ID, run ID, active step ID, procedure state, step progress | Spacecraft Payload Bus |
| **`ASSURANCE`** | Event-driven | Decision (`VERIFIED`, `UNCERTAIN`, `DEVIATION`), confidence, recovery instruction | Spacecraft Mission Events |
| **`PERFORMANCE`**| 0.5 Hz (TBD) | Pipeline FPS, inference latency (ms), queue depth, RAM RSS | Payload Engineering Channel |
| **`FAULT`** | Event-driven | Fault code, subsystem, severity (`WARNING`, `CRITICAL`), containment action | Spacecraft Anomaly Bus |

---

## 4. Logical Command Interface (`IF-CMD-01`)

Commands originate from authorized spacecraft controllers or ground passes.

### 4.1 Permitted Flight Commands
1. **`REQUEST_STATUS`**: Queries current health, procedure, and assurance state.
2. **`START_EXPERIMENT`**: Initiates autonomous assurance on target procedure.
3. **`STOP_EXPERIMENT`**: Halts active experiment and flushes evidence.
4. **`PAUSE`**: Temporarily pauses procedure verification.
5. **`RESUME`**: Resumes paused procedure verification.
6. **`REQUEST_EVIDENCE`**: Requests cryptographic proof and keyframe for step ID.
7. **`REQUEST_REPORT`**: Requests complete experiment run summary.

### 4.2 Safety Interlocks
Commands are processed through `CommandDispatcher` and `CommandSafetyGuard`:
- `START_EXPERIMENT` is rejected if camera is offline, model is unverified, procedure YAML is corrupted, or storage capacity is critical.
- Unregistered, malformed, or out-of-sequence commands are rejected with logged diagnostic codes.
- Ground Monitor UI connects strictly through external telemetry and events; direct internal method invocation is strictly prohibited.

---

## 5. Storage Partitioning & Priority (`IF-STOR-01`)

Flight data is strictly partitioned under `flight_data/`:
- `flight_data/mission/`: Atomic mission state persistence and run metadata.
- `flight_data/evidence/`: Cryptographic SHA-256 evidence packages and keyframes.
- `flight_data/telemetry/`: Time-indexed downlink packets.
- `flight_data/reports/`: Run verification reports and startup configuration audits.
- `flight_data/diagnostics/`: Rotating bounded flight logs (`flight.log`).

### Storage Priority Policy (Section 28)
```
MISSION EVENTS > ASSURANCE EVENTS > EVIDENCE > MISSION VIDEO > DIAGNOSTICS > DEBUG
```
Under storage pressure, diagnostic logs and oldest non-critical video frames are pruned first. Verified mission events and assurance proofs are never pruned.

---

## 6. Subsystem Watchdog & Fault Recovery (`IF-WATCH-01`)

A central watchdog monitors heartbeats from:
- `main_process`
- `camera`
- `perception`
- `event_bus`
- `storage`
- `mission_state`

Timeout triggers configurable policy: `ENTER_DEGRADED` (default) $\to$ `PAUSE_MISSION` $\to$ `SAFE_SHUTDOWN`.
