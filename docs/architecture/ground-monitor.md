# ASTRA-EA Ground Monitor Architecture

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Classification:** Phase 9 Technical Design & Remote Observability Blueprint

---

## 1. Primary Architectural Principle

The **ASTRA-EA Ground Monitor** is an external, remote observation and situational awareness platform designed for flight controllers, principal investigators, and ground support personnel. 

### Core Separation Axiom
$$\text{ONBOARD} = \text{EXECUTION + PERCEPTION + ASSURANCE + RECOVERY + LOCAL LOGGING}$$
$$\text{GROUND} = \text{OBSERVATION + MONITORING + SITUATIONAL AWARENESS + REVIEW}$$

```text
+-------------------------------------------------------------------------+
|                              ONBOARD ASTRA                              |
|                                                                         |
| Camera ---> Perception ---> Interaction ---> Temporal ---> Procedure    |
|                                                              |          |
|                                                          Assurance      |
|                                                              |          |
|                                                       Recovery + Voice  |
|                                                              |          |
|                                                        Local SQLite WAL |
+-------------------------------------------------------------------------+
                                    |
                    Non-blocking IP Streaming (LAN)
                                    |
                                    v
+-------------------------------------------------------------------------+
|                          GROUND MONITOR (READ-ONLY)                     |
|                                                                         |
|    +-------------------------+     +-------------------------------+   |
|    | Live IP Video Stream    |     | Active Step & Progress Card   |   |
|    | (MJPEG over HTTP)       |     | Tri-State Assurance Banner    |   |
|    +-------------------------+     +-------------------------------+   |
|    | Chronological Timeline  |     | Active Deviations & Guidance  |   |
|    | Latency + Category Tabs |     | Subsystem Health Telemetry    |   |
|    +-------------------------+     +-------------------------------+   |
+-------------------------------------------------------------------------+
```

### Safety Invariants
1. **Read-Only Observation:** The Ground Monitor possesses **zero authority** to modify active procedure steps, override assurance decisions, force transitions, or alter spacecraft hardware.
2. **Onboard Immunity:** A ground client disconnect, slow TCP buffer, or network partition will **never block, stall, or crash** the onboard AI inference or experiment assurance loop.
3. **No Ground AI in Operational Loop:** AI perception and step verification execute exclusively onboard. Ground monitors receive and display onboard results.

---

## 2. Component Layout

The Ground Monitor application (`apps/ground_monitor/app.py`) is structured into decoupled UI panels:

| Panel | Module | Primary Responsibilities |
| :--- | :--- | :--- |
| **Header Panel** | `header_panel.py` | Displays master link badge (`ONLINE`, `PARTIAL`, `OFFLINE`), dual channel indicators (Video/Events), heartbeat latency, and `SIMULATION MODE` indicator. |
| **Video Panel** | `video_panel.py` | Renders continuous live IP video, stream FPS, resolution, dropped frame counter, and offline reticle placeholder. |
| **Mission Panel** | `mission_panel.py` | Displays active procedure ID, session run ID, step progress bar, current activity, and large Tri-State Assurance banner (`VERIFIED`, `UNCERTAIN`, `DEVIATION`). |
| **Alert Panel** | `alert_panel.py` | Surfaces active procedural deviations, severity badges (`DANGER`, `WARNING`, `INFO`), and closed-loop recovery guidance directives. |
| **Timeline Panel** | `timeline_panel.py` | Displays chronological event stream with onboard UTC timestamp, arrival timestamp, and transit latency delta; supports category filters (`ALL`, `STEPS`, `DEVIATIONS`, `RECOVERY`, `SYSTEM`). |
| **Health Panel** | `health_panel.py` | Monitors onboard subsystem status (`Perception`, `Camera`, `Assurance`, `Storage`), stream bitrate/FPS, heartbeat age, and connection quality (`GOOD`, `DEGRADED`, `OFFLINE`). |
| **Evidence Viewer** | `evidence_viewer.py` | Read-only modal viewer inspecting corroborating evidence JSON bundles, causal trees, and object bounding boxes. |

---

## 3. Dual-Channel Connection Architecture

To guard against partial network failures, the Ground Monitor operates two independent transport channels via `streaming/connection/manager.py`:

1. **Video Channel (`VideoStreamClient`):**
   - Connects to `http://<host>:8554/video` via HTTP multipart MJPEG.
   - Non-blocking frame ingestion; decodes JPEG payloads on a dedicated reader thread.
   - Computes empirical client FPS and tracks socket resets.

2. **Telemetry Event Channel (`EventStreamClient`):**
   - Connects to `http://<host>:8765/events` via Server-Sent Events (SSE).
   - Receives typed `GroundEvent` JSON packets.
   - Computes network transit latency: $\Delta t = t_{\text{client\_receive}} - t_{\text{onboard\_timestamp}}$.

### Link Quality Degradation Model
$$\text{Elapsed Time Since Last Heartbeat} \longrightarrow \text{Link Quality Tier}$$
- $\Delta t < 2.5\text{s}$: **`GOOD` (🟢 ONLINE)** — Nominal real-time operations.
- $2.5\text{s} \le \Delta t < 6.0\text{s}$: **`DEGRADED` (🟡 WARNING)** — Telemetry delayed; display last known state.
- $\Delta t \ge 6.0\text{s}$: **`OFFLINE` (🔴 LINK LOST)** — Link severed; initiate exponential backoff reconnection.

---

## 4. Reconnection & Catch-Up Protocol

When link restoration occurs after an outage:
1. `EventStreamClient` reconnects to the SSE endpoint.
2. The client checks `last_sequence_received` (e.g. sequence #12).
3. The client issues a replay request: `GET /events/replay?since=12`.
4. `EventStreamServer` queries its internal ring buffer (`EventPublisher`) and transmits missed intermediate events in chronological order.
5. The Ground Monitor updates its mission timeline and state store without duplicate alerts or missing steps.
