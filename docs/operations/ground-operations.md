# ASTRA-EA — Ground Segment Operations Manual

## Phase 19: Mission Operations & Ground Segment Integration (D19.09)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Ground Observability Philosophy (Section 22, 23)

The Ground Segment Observability Console (`apps/ground_monitor`) provides remote flight directors, payload developers, and mission controllers with real-time situational awareness.

### Critical Ground Rule (Section 23)
> **Ground Monitor does NOT override onboard assurance.**  
> Ground operators cannot unilaterally advance step counters, force-verify incomplete steps, or delete un-verified evidence. All state assertions originate autonomously from the flight engine.

---

## 2. Telemetry Channels & Link Status (Section 55)

The Ground Monitor header panel separates communication channels into distinct badges:

| Channel | Badge ID | Nominal State | Degraded State | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Video** | `VID` | `ONLINE (30 FPS)` | `OFFLINE` | Live compressed optical MJPEG/H.264 camera stream. |
| **Events** | `EVT` | `ONLINE` | `OFFLINE` | Server-Sent Events (SSE) stream carrying typed `GroundEvent` records. |
| **Telemetry** | `TLM` | `ONLINE` | `OFFLINE` | Periodic JSON telemetry packets (CPU, storage, memory, FPS, drop count). |
| **Command** | `CMD` | `TBD` | `OFFLINE` | Future telecommand uplink placeholder (TBD by spacecraft bus). |

---

## 3. Disconnection, Buffer Retention & Reconciliation (Section 41, 42, 43, 44)

```text
GROUND LINK DISCONNECT
         │
         ▼
[Ground Marked OFFLINE] ◄── Ground Monitor surfaces disconnection warning
         │
[Onboard Continues]     ◄── Flight software continues autonomous experiment tracking
         │
[Event Buffering]       ◄── Events buffered in local flight_data/telemetry/ ring buffer
         │
RECONNECT DETECTED
         │
         ▼
[Sequence Gap Check]    ◄── Ground reconciler detects gap (e.g. missed seq 103..107)
         │
[Reconciliation Sync]   ◄── Ground requests missed sequence range from onboard buffer
         │
[Timeline Harmonized]   ◄── Events sorted into timeline; duplicates discarded; SYNC: OK
```

### Gap Detection Rules (Section 44)
1. Monotonic sequence counter `sequence_num` increments with every emitted event.
2. If Ground last saw sequence `100` and next receives `104`, a gap of `[101, 103]` is logged.
3. The Ground Reconciler requests the backlog, ingests `101`, `102`, `103`, and verifies zero duplicate records are appended to the timeline.

---

## 4. Observation Requests (Section 24)

Where enabled by the telemetry interface, Ground Operators can dispatch read-only observation queries:
- **`REQUEST STATUS`**: Solicits instantaneous platform health, active step ID, and current MET.
- **`REQUEST EVIDENCE`**: Solicits cryptographic snapshot of latest step transition or deviation.
- **`REQUEST REPORT`**: Solicits interim summary report of completed steps and deviations.
