# ASTRA-EA: Spacecraft Logical Interface Control Document (ICD)

**Classification:** Payload Systems Engineering & Interface Control Document  
**Document ID:** `ASTRA-ICD-001`  
**System:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Scope & Interface Architecture

This document defines the formal **logical interface contracts** between the ASTRA-EA edge payload and the host spacecraft bus. Physical pinouts and connector standards are intentionally decoupled to preserve compatibility with both the **Bharatiya Antariksh Station (BAS)** payload racks and modular exploration vehicles.

```
+-------------------------------------------------------------------------+
|                    HOST SPACECRAFT INTERFACES                           |
|                                                                         |
|  [ICD-CAM-01] Optical Camera Ingestion Contract                         |
|  [ICD-PWR-01] Power States & Conditioning Contract                      |
|  [ICD-TIME-01] Dual-Clock Master Time Synchronization Contract          |
|  [ICD-BUS-01] Vehicle Data Bus & Command/Telemetry Contract             |
|  [ICD-THM-01] Thermal Environment & Telemetry Contract                  |
+-------------------------------------------------------------------------+
```

---

## 2. Optical Camera Ingestion Interface (`ICD-CAM-01`)

### 2.1 Logical Stream Parameters
- **Data Protocol:** POSIX Video4Linux2 (V4L2) / GMSL2 serialized CSI-2 / USB3 Vision.
- **Pixel Encoding:** Uncompressed YUYV $4:2:2$ or RGB24.
- **Spatial Resolution:** $1920 \times 1080$ (Nominal) / $1280 \times 720$ (Degraded).
- **Temporal Rate:** $30.0 \pm 0.5$ frames per second (FPS).
- **Triggering Mode:** Free-running continuous capture or external hardware sync pulse (PPS).

### 2.2 Ingestion Frame Envelope Schema
Every frame delivered to the edge perception worker includes metadata headers:
```json
{
  "frame_sequence_id": 104281,
  "optical_timestamp_ns": 1789288800123456789,
  "exposure_time_us": 12500,
  "sensor_gain_db": 6.0,
  "camera_profile_id": "VIEW_LEFT",
  "hardware_status": "NOMINAL"
}
```

### 2.3 Sensor Failure Signaling
- **Timeout Threshold:** If no frame is delivered within $100\text{ ms}$ ($\ge 3$ frame periods), the ingestion supervisor asserts `SIGNAL_CAMERA_BLACKOUT`.
- **System Action:** Procedural assurance transitions to `VERIFICATION PAUSED`.

---

## 3. Power State Management Interface (`ICD-PWR-01`)

ASTRA-EA monitors host vehicle power conditioning without asserting direct power rail control.

| Spacecraft Power State | Voltage / Bus Condition | ASTRA-EA System Action | Permitted Operations |
| :--- | :--- | :--- | :--- |
| **`POWER_ON`** | Initial cold boot rail energization | Execute boot self-test & model integrity hash | Diagnostics & Self-Test |
| **`POWER_GOOD`** | Nominal voltage ($28\text{V} \pm 2\text{V}$ DC) | Normal full-workload operation | Full AI, Audio, Recording & Assurance |
| **`POWER_DEGRADED`**| Voltage dip or battery reserve $<30\%$ | Enter `LOW_RESOURCE` degraded mode | Disable non-critical UI; retain assurance |
| **`POWER_LOSS`** | Imminent spacecraft bus shutdown signal | Execute emergency flush ($<500\text{ ms}$) | Finalize SQLite WAL & unmount NVMe safely |
| **`POWER_RECOVERY`** | Voltage restored to nominal | Automatic state recovery from SQLite log | Resume active experiment run |

---

## 4. Master Time Synchronization Interface (`ICD-TIME-01`)

To guarantee absolute causal traceability across orbital downlinks, ASTRA-EA maintains a strict separation between **Spacecraft Event Time (SCET)** and **Local Monotonic Duration**:

```
EVENT TIME (SCET UTC)     ===> Recorded at physical instant photon strikes camera sensor.
RECEIPT TIME (Ground UTC) ===> Recorded when telemetry packet is processed at Earth station.
```

- **Monotonic Duration Clock:** High-resolution hardware clock (`CLOCK_MONOTONIC_RAW`) driving step timers, temporal dwell windows, and frame rate regulation (immune to NTP/GPS step adjustments).
- **Wall-Clock UTC Synchronizer:** Driven by spacecraft PPS (Pulse Per Second) or time distribution messages, stamping all SQLite database events in ISO-8601 UTC with microsecond resolution.

---

## 5. Vehicle Data Bus & Telemetry Interface (`ICD-BUS-01`)

Implemented logically in `core/integration/bus.py`:
- **Physical Protocol Independence:** Abstracted across MIL-STD-1553B (Command/Response), SpaceWire (High-rate packets), CAN aerospace, or Ethernet.
- **Downlink Telemetry Packet (Rate: $1.0\text{ Hz}$):**
  - Mission Identifier (`mission_id`) & Run Identifier (`run_id`).
  - Active Procedure Step ID & Verification Status (`VERIFIED`, `UNCERTAIN`, `DEVIATION`).
  - Pipeline Throughput (FPS) & P95 Decision Latency.
  - Subsystem Health Bitmask (Camera, Model, Storage, DB, Audio).
- **Uplink Command Schema (Authenticated):**
  - `CMD_START_EXPERIMENT(procedure_id, config_hash)`
  - `CMD_PAUSE_EXPERIMENT(reason)`
  - `CMD_RESUME_EXPERIMENT()`
  - `CMD_REQUEST_EVIDENCE_CLIP(step_id, time_window)`

---

## 6. Thermal Environment Interface (`ICD-THM-01`)

The edge runtime adapts workload dynamically based on external spacecraft chassis thermal signals:

| Thermal State | Threshold Condition | Edge Runtime Action |
| :--- | :--- | :--- |
| **`THERMAL_NORMAL`** | Payload enclosure temperature $<45^\circ\text{C}$ | Full neural inference @ 30 FPS. |
| **`THERMAL_WARNING`**| Payload enclosure temperature $45^\circ\text{C} - 60^\circ\text{C}$ | Reduce video recording to 15 FPS; disable UI web server. |
| **`THERMAL_CRITICAL`**| Payload enclosure temperature $>60^\circ\text{C}$ | Engage rule-based baseline detector; reduce inference rate to 10 FPS. |
