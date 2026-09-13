# ASTRA-EA Ground Telemetry Event Stream Architecture

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Classification:** Phase 9 Telemetry Schema, Sequence Ordering, and State Catch-up Blueprint

---

## 1. Architectural Role

While video streaming provides raw visual confirmation, the **Ground Telemetry Event Stream** delivers structured, machine-verifiable operational facts from the onboard assurance engine to remote observers.

```text
ONBOARD PIPELINE                              EVENT STREAM SERVER
Assurance Decision ---> EventPublisher ---> [Rolling Buffer: 500 Events]
Recovery Context   ---> (Assigns seq #)           |
Subsystem Health   --->                           +---> Live SSE Stream (/events)
                                                  |
                                                  +---> Historical Replay (/events/replay?since=N)
                                                  |
                                                  +---> Heartbeat Emitter (/heartbeat)
```

---

## 2. Event Taxonomy & Hierarchy

All events adhere to the typed `GroundEvent` schema defined in [`streaming/events/schema.py`](file:///home/subish-loq/Documents/astra/streaming/events/schema.py):

| Event Type | Typical Trigger | Severity Tier | Timeline Category |
| :--- | :--- | :--- | :--- |
| **`EXPERIMENT_STARTED`** | Procedure initialized by astronaut or mission script | `INFO` | `SYSTEM` |
| **`STEP_VERIFIED`** | Step physical evidence conditions completely satisfied | `INFO` | `STEPS` |
| **`STEP_UNCERTAIN`** | Optical ambiguity, occlusion, or low confidence detected | `WARNING` | `STEPS` |
| **`DEVIATION_DETECTED`** | Procedural violation confirmed (`WRONG_OBJECT`, `WRONG_ORDER`, etc.) | `DANGER` | `DEVIATIONS` |
| **`RECOVERY_REQUIRED`** | Closed-loop corrective instruction formulated | `WARNING` | `RECOVERY` |
| **`RECOVERY_VERIFIED`** | Corrective astronaut physical action verified | `INFO` | `RECOVERY` |
| **`EXPERIMENT_COMPLETED`** | Final procedure step verified and logged | `INFO` | `SYSTEM` |
| **`SYSTEM_HEALTH_CHANGED`** | Periodic telemetry update from perception/camera/assurance | `INFO` | `SYSTEM` |
| **`HEARTBEAT`** | Periodic keepalive emitted every 2.0s | `INFO` | `SYSTEM` |
| **`TEST_EVENT`** | Synthetic diagnostic loopback test | `INFO` | `SYSTEM` |

---

## 3. Sequence Integrity & Monotonic Ordering

Every emitted event is assigned an atomically incremented, monotonic 64-bit integer (`sequence_num = 1, 2, 3...`):
- **Gap Detection:** If Ground receives sequence #4 followed immediately by sequence #7, it detects a network dropout of 2 events.
- **Replay Reconciliation:** Upon reconnecting, the ground client queries `GET /events/replay?since=4`, and the server dispatches sequence #5 and #6 from its rolling ring buffer.
- **Deduplication:** Events with $\text{seq} \le \text{last\_seen\_seq}$ are discarded by the client presentation layer.

---

## 4. Clock Synchronization & Onboard Authority

In strict accordance with spacecraft telemetry standards:
1. **Onboard Timestamp Authority:** All timestamps in `GroundEvent.timestamp` are recorded in UTC ISO 8601 format by the onboard spacecraft clock.
2. **Transit Latency Transparency:** The Ground Monitor measures receipt time and calculates latency:
   $$\text{Transit Latency} = t_{\text{ground\_receipt}} - t_{\text{onboard\_timestamp}}$$
3. Ground never overrides or overwrites the onboard timestamp with ground station local time.
