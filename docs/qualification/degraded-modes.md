# ASTRA-EA: Software Partitioning, Fault Containment & Degraded Operational Modes

**Classification:** Safety & Reliability Engineering Specification  
**Document ID:** `ASTRA-DEG-001`  
**Standard:** ECSS-Q-ST-80C / NASA-STD-8719.13 (Software Safety)  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Logical Software Partitioning & Isolation

To prevent non-critical software defects (such as web browser crashes or network socket dropouts) from corrupting core experiment assurance, the runtime is partitioned into four decoupled failure domains:

```
+-------------------------------------------------------------------------+
|                  PARTITION 1: CRITICAL ASSURANCE CORE                   |
|  - Video Ingestion Worker           - Procedure State Machine           |
|  - Spatial Interaction Engine       - Tri-State Assurance Engine        |
|  - Temporal Dwell Accumulator       - Fail-Safe Anomaly Interceptor     |
+------------------------------------+------------------------------------+
                                     | (One-way non-blocking queue)
                                     v
+------------------------------------+------------------------------------+
|                  PARTITION 2: SECONDARY PERCEPTION                      |
|  - Neural Object Detector (GPU/NPU) - Secondary Rule-Based Baseline     |
|  - Fallback Supervisor              - Keypoint Estimator                |
+------------------------------------+------------------------------------+
                                     | (Async memory queues)
                                     v
+------------------------------------+------------------------------------+
|                  PARTITION 3: TELEMETRY & AUDIT STORE                   |
|  - Local SQLite WAL Writer         - Microsecond JSON Event Bus         |
|  - MP4 Video Disk Recorder         - Evidence File Archiver             |
+------------------------------------+------------------------------------+
                                     | (Decoupled WebSocket / HTTP)
                                     v
+-------------------------------------------------------------------------+
|                  PARTITION 4: AUXILIARY OPERATOR I/O                    |
|  - Cockpit Voice Engine (TTS)       - Ground Monitor Streaming Server   |
|  - Mission Console Web Server       - Remote Telemetry Broadcast        |
+-------------------------------------------------------------------------+
```

---

## 2. Watchdog Supervisor & Process Health Monitor

The Watchdog process operates as an independent supervisor monitoring subsystem heartbeats at $2.0\text{ Hz}$:

| Subsystem Monitored | Heartbeat Source | Timeout Threshold | Watchdog Action |
| :--- | :--- | :---: | :--- |
| **Optical Ingestion** | V4L2 frame arrival timestamp | $100\text{ ms}$ ($\ge 3$ frames)| Assert `CAMERA_UNAVAILABLE`; transition to `PAUSED`. |
| **Neural Inference** | Model worker forward pass | $150\text{ ms}$ | Flag `MODEL_DEGRADED`; engage heuristic fallback. |
| **Assurance Engine** | State machine evaluation loop | $200\text{ ms}$ | Log critical fault; hold previous safe state. |
| **Disk Storage** | SQLite commit latency | $1,000\text{ ms}$ | Assert `STORAGE_DEGRADED`; switch to memory buffer. |
| **Ground Streamer** | WebSocket TCP transmit buffer | $2,000\text{ ms}$ | Assert `STREAM_UNAVAILABLE`; prune client socket. |

---

## 3. Safe Startup & Safe Shutdown Lifecycles

### 3.1 Safe Startup State Machine
```
[POWER ON] ──> [SELF-TEST] ──> [CONFIG VALIDATION] ──> [MODEL CHECKSUM] ──> [STORAGE CHECK] ──> [READY]
      |              |                  |                      |                    |
      v              v                  v                      v                    v
   [ABORT]        [ABORT]            [ABORT]                [ABORT]              [ABORT]
```
*Rule:* The system **SHALL NOT** enter `READY` or allow experiment initiation if any pre-flight check fails.

### 3.2 Safe Shutdown Sequence
1. Receive shutdown command or `POWER_LOSS` bus interrupt.
2. Inhibit new camera frame ingestion.
3. Finalize active procedure step and flush pending evidence snapshots.
4. Issue SQLite `PRAGMA wal_checkpoint(TRUNCATE)` to commit pending transactions.
5. Finalize MP4 video recording headers and close file descriptors.
6. Terminate auxiliary web workers and exit cleanly.

---

## 4. Formal Degraded Operational Modes Matrix

| Degraded Mode | Entry Trigger Condition | Permitted Behaviors | Forbidden Behaviors | Exit / Recovery Condition | Logging Requirement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`NORMAL`** | All 11 subsystems healthy | Full AI, Cockpit Audio, 1080p Recording, Ground Stream | None | Nominal operating mode | Periodic 1Hz telemetry |
| **`LOW_RESOURCE`** | Available RAM $<500\text{ MB}$ or CPU $>80\%$ | Core assurance, baseline detection, SQLite logging | Ground MJPEG streaming, high-res video recording | RAM $>750\text{ MB}$ for 30 seconds | Log `STATE_CHANGE: LOW_RESOURCE` |
| **`NETWORK_LOST`** | Ethernet / Wi-Fi physical link down | 100% onboard assurance, local audio, local MP4 recording | Ground telemetry transmission | Network link re-established | Log `NETWORK_DISCONNECT`; queue events |
| **`VOICE_UNAVAILABLE`**| Audio device crash / ALSA init failure | Visual HUD guidance banners, full assurance | Audible speech synthesis | Audio driver re-initialization | Log `VOICE_FAILED`; auto-switch to HUD |
| **`STREAM_UNAVAILABLE`**| WebSocket buffer saturation / client lag | Full onboard assurance, local video recording | Live MJPEG network broadcast | Client disconnect or bandwidth recovery | Log `GROUND_STREAM_THROTTLED` |
| **`MODEL_DEGRADED`** | Neural detector exception / VRAM exhaustion | Heuristic color baseline detection, procedure tracking | Complex neural object disambiguation | Neural worker restart / reload | Log `PERCEPTION_FALLBACK_ENGAGED` |
| **`CAMERA_UNAVAILABLE`**| Sensor timeout $\ge 3$ consecutive frames | Hold active procedure state, alert operator | False verification of procedure steps | Camera stream stable for $\ge 30$ frames | Log `CAMERA_BLACKOUT`; enter `PAUSED` |
| **`STORAGE_DEGRADED`** | Free storage $<1.0\text{ GB}$ or write error | In-memory event caching, live visual guidance | Long MP4 recording, non-essential debug logs | Storage cleared $>2.0\text{ GB}$ | Log `STORAGE_PRESSURE_WARNING` |

---

## 5. The Critical Assurance Invariant

> **Non-critical services (Ground Streaming, Web UI, Voice TTS, and Developer Profilers) are strictly isolated. A total crash of all auxiliary services SHALL NOT disrupt or prevent the local onboard engine from detecting a wrong object or verifying procedural recovery.**
