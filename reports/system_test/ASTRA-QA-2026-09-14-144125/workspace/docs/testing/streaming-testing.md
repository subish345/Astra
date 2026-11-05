# ASTRA-EA — Video & Event Streaming Testing Strategy

## Verification for Local IP Video, SSE Telemetry, and Network Backpressure

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Overview & Verification Scope

The Phase 9 streaming subsystem connects the autonomous Onboard ASTRA-EA runtime to the Ground Monitor. The testing strategy validates four core guarantees:
1. **Zero AI Pipeline Disruption:** Video compression and client distribution run in non-blocking worker threads. A blocked or slow network client must drop stream frames rather than backpressure the AI perception loop.
2. **Deterministic Sequence & Delivery:** Mission telemetry events are stamped with monotonically increasing sequence numbers and preserved in a 500-event ring buffer for seamless replay after link recovery.
3. **Multi-Channel Resilience:** Video and event streams operate over distinct ports (`:8554` and `:8765`), allowing partial network degradation (e.g. video offline, events online) to be detected and handled independently.
4. **Defensive Boundary Controls:** Automated checks confirm bind address validation, path traversal neutralization, and rate limiting.

---

## 2. Streaming Test Suites

| Suite | Path | Verification Focus |
| :--- | :--- | :--- |
| **Video Streaming** | [`tests/streaming/test_video_streaming.py`](file:///home/subish-loq/Documents/astra/tests/streaming/test_video_streaming.py) | • `StreamEncoder` quality profiles (`LOW`, `MEDIUM`, `HIGH`).<br>• Zero-client encoding bypass (0.01 ms execution overhead).<br>• Bounded queue (depth=1) with drop-oldest backpressure.<br>• Multipart MJPEG framing and boundary separators.<br>• Clean server startup, client frame reception, and graceful shutdown. |
| **Event Telemetry** | [`tests/streaming/test_event_streaming.py`](file:///home/subish-loq/Documents/astra/tests/streaming/test_event_streaming.py) | • `GroundEvent` dataclass validation and SSE wire formatting.<br>• Atomic sequence numbering and ring-buffer replay (`GET /events/replay?since={seq}`).<br>• SSE client connection, keep-alive `: ping` processing, and event ingestion.<br>• Onboard-to-ground transit latency calculation.<br>• Thread-safe server shutdown via `threading.Event`. |
| **Network Resilience** | [`tests/network/test_network_resilience.py`](file:///home/subish-loq/Documents/astra/tests/network/test_network_resilience.py) | • `HeartbeatWatchdog` three-tier status (`GOOD` <2.5s, `DEGRADED` 2.5–6s, `OFFLINE` >6s).<br>• Exponential backoff with random jitter (`BackoffManager`).<br>• Dual-channel `ConnectionManager` state orchestration.<br>• Simulated link loss, offline buffering, and automatic reconnection synchronization. |
| **Security & Auditing** | [`tests/network/test_security.py`](file:///home/subish-loq/Documents/astra/tests/network/test_security.py) | • Bind address filtering (`127.0.0.1` vs `0.0.0.0` warnings).<br>• Path traversal attacks on `/evidence/{id}` (`..`, `/`, `\0`, special characters).<br>• Token-bucket rate limiter under burst traffic conditions.<br>• Non-mutative API verification. |

---

## 3. Dedicated CLI Diagnostic Tools

Phase 9 integrates built-in CLI verification commands for pre-flight network checkout:

### 3.1 Streaming Subsystem Doctor
Inspects live server health, bind configuration, active client counts, FPS, and frame drop telemetry:
```bash
python3 main.py stream doctor
```

### 3.2 Video Stream Loopback Test
Spawns an ephemeral video server, connects an internal `VideoStreamClient`, verifies reception of synthetic test frames, calculates encode and transport latency, counts drops, and terminates cleanly:
```bash
python3 main.py stream test --frames 30 --fps 15
```

### 3.3 Event Stream Broadcast Test
Starts an ephemeral SSE event server, connects an internal `EventStreamClient`, publishes `TEST_EVENT` telemetry payloads, asserts delivery, measures transit latency, and shuts down:
```bash
python3 main.py events stream-test --count 5
```

---

## 4. Automated Benchmark & Impact Suite

To verify that streaming does not degrade the onboard AI inference pipeline, the automated benchmark runner compares pure AI inference throughput against combined AI + streaming + local recording:

```bash
python3 -m streaming.benchmark
```

Generates:
- `storage/reports/streaming/stream_impact_report.json`
- `storage/reports/streaming/security_report.json`

### Benchmark Results Baseline

| Metric | AI Inference Only | AI + Recording + Streaming | Difference |
| :--- | :--- | :--- | :--- |
| **Pipeline Throughput** | 60.71 FPS | 59.33 FPS | **-2.27%** (negligible) |
| **Mean Frame Latency** | 16.47 ms | 16.85 ms | **+0.38 ms** |
| **CPU Utilization** | 18.2% | 21.6% | **+3.4%** |
| **Stream Drop Rate** | N/A | 0 dropped frames | **0.0%** |
| **SSE Transit Latency** | N/A | 0.32 ms | Real-time |
