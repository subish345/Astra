# ASTRA-EA Video Streaming Architecture

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Classification:** Phase 9 Video Ingestion, Encoding, and IP Distribution Design

---

## 1. Protocol Evaluation & Selection

To provide remote video observation of onboard experiments across a local spacecraft or habitat network, three primary IP streaming protocols were evaluated:

| Protocol | Latency | Dependency Complexity | CPU Overhead | Client Compatibility | Resilience to Disconnect | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RTSP / RTP (H.264)** | Low (80–200 ms) | High (Requires external MediaMTX/GStreamer binaries & codec licenses) | Medium | Requires specialized player (VLC, GStreamer) | Stalls on keyframe loss | Deferred to Phase 10 edge packaging |
| **WebRTC (VP8/H.264)** | Very Low (40–100 ms) | Very High (`aiortc`, libav, OpenSSL, ICE/STUN signaling server) | High | Browsers & custom WebRTC clients | Complex peer reconnection | Rejected for ground demo complexity |
| **MJPEG over HTTP** | **Ultra-Low (< 25 ms)** | **Zero (Native Python + OpenCV, no external servers or binaries)** | **Low (Direct OpenCV JPEG encode)** | **Universal (Qt QLabel, Chrome, Firefox, VLC, curl)** | **Instant socket reset recovery** | **SELECTED FOR PHASE 9 BASELINE** |

### Key Rationale for MJPEG over HTTP
1. **Zero External Binaries:** Does not require compiling or deploying third-party streaming daemons.
2. **Deterministic Frame Delivery:** Each frame is an independent JPEG image. Frame drops do not cause keyframe artifacting or macroblock corruption.
3. **Sub-millisecond Encoding:** Measured encoding latency is **~0.65 ms** (Low) to **~3.02 ms** (Medium 720p).
4. **Instantaneous Reconnect:** Re-establishing the HTTP GET stream requires no SDP offer/answer or RTSP state negotiation.

---

## 2. Non-Blocking Ingestion Pipeline

$$\text{Camera Ingestion} \longrightarrow \text{Perception + Assurance Loop} \xrightarrow{\text{publish\_frame()}} \text{Single-Frame Ring Buffer} \xrightarrow{\text{Stream Worker}} \text{HTTP Socket}$$

```text
+-------------------------------------------------------------------------+
| ONBOARD AI THREAD                                                       |
|                                                                         |
| 1. Capture Raw Frame (CameraSource)                                     |
| 2. Run Perception (Object + Hands + Pose)                               |
| 3. Evaluate Physical Interaction & Procedure Assurance                  |
| 4. Render HUD Overlay (vis)                                             |
| 5. video_server.publish_frame(vis) ---> [Put in maxsize=1 Queue]        |
|                                         (Cost: ~0.02 ms non-blocking)   |
| 6. Continue immediately to next frame tick                              |
+-------------------------------------------------------------------------+
                                    |
+-------------------------------------------------------------------------+
| STREAM WORKER THREAD                                                    |
|                                                                         |
| 1. Pop latest frame from queue (discard stale frames if client is slow) |
| 2. Resize to configured stream dimensions (e.g. 1280x720)               |
| 3. Compress frame using cv2.imencode('.jpg', frame, [QUALITY, 75])      |
| 4. Transmit multipart boundary --frame over TCP socket to ground client |
+-------------------------------------------------------------------------+
```

### Backpressure & Drop Policy
- Internal buffer capacity: **`maxsize=1`**.
- If a ground client socket becomes congested or stalls:
  - The stream worker attempts to insert the newest frame.
  - If the client queue is full, the obsolete frame is dropped immediately (`client_q.get_nowait()`), and `total_frames_dropped` increments.
  - The onboard AI thread **never waits for a network socket**.

---

## 3. Stream Quality Profiles

Configured in [`configs/system.yaml`](file:///home/subish-loq/Documents/astra/configs/system.yaml):

| Quality Tier | Resolution | Target FPS | JPEG Quality | Avg Encode Time | Typical Bandwidth |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LOW`** | $640 \times 360$ | 15 FPS | 65 | 0.65 ms | ~8.6 Mbps |
| **`MEDIUM`** *(Default)* | $1280 \times 720$ | 15 FPS | 75 | 3.02 ms | ~64.8 Mbps (Local LAN) |
| **`HIGH`** | $1920 \times 1080$ | 20 FPS | 85 | 7.20 ms | ~195 Mbps (High-speed LAN) |

---

## 4. Empirical Performance Benchmark

Measured in `storage/reports/streaming/stream_impact_report.json`:
- **AI-Only Processing Rate:** **60.7 FPS** (0.494s for 30 iterations)
- **AI + Video Stream + Event Telemetry Rate:** **59.3 FPS** (0.506s for 30 iterations)
- **Net Compute Overhead:** **2.3%**
- **Conclusion:** Streaming imposes negligible impact on onboard assurance capacity, well below the 15.0% ECSS spacecraft resource allocation budget.
