# ASTRA-EA: Known Issues & Operational Caveats

**System:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Release:** 1.0.0-RC1  
**Category:** Operational Engineering Documentation

This document logs verified non-fatal issues, environmental caveats, edge behaviors, and recommended operational workarounds identified during Phase 10–12 testing. None of these issues compromise core procedural assurance safety.

---

## 1. Audio System & Headless Linux Environments

### 1.1 ALSA / PulseAudio Initialization in Headless / CI Containers
- **Issue Description:**  
  In headless Linux environments, remote SSH sessions, or Docker containers lacking an active PulseAudio/PipeWire daemon, the Pygame/TTS audio output driver may log warnings such as `ALSA lib pcm.c:... Unknown PCM default` or fail to open the audio hardware device.
- **System Behavior:**  
  The Voice Engine cleanly catches the audio initialization exception and automatically falls back to `SIMULATED_AUDIO` mode. Speech events are formatted, printed to stdout, logged to the structured event bus, and displayed on the Mission Console UI.
- **Operational Impact:**  
  Zero impact on procedural assurance, deviation detection, or recovery logic.
- **Workaround:**  
  When testing in headless environments, launch with the `--headless` flag or configure `configs/deployment/final_demo.yaml` with `voice.enabled: false` or `voice.backend: "dummy"`.

---

## 2. Optical Sensor & Camera Ingestion

### 2.1 Linux Kernel `/dev/video*` Device Index Shifts
- **Issue Description:**  
  On modern Linux distributions, single physical USB webcams frequently register multiple V4L2 device nodes (e.g., `/dev/video0` for raw video stream and `/dev/video1` for metadata/H.264 streams). When connecting multiple webcams, device indices may shift across system reboots.
- **Workaround:**  
  Use `astra deployment doctor` to discover active camera devices and specify the exact video node or use simulated synthetic video injection:
  ```bash
  astra demo --camera 0
  ```
  For persistent industrial setups, configure udev rules to symlink the device node (e.g., `/dev/v4l/by-id/...`).

### 2.2 Extreme Low Light (<15 Lux) Color Fallback Sensitivity
- **Issue Description:**  
  The secondary fallback detector (`BaselineColorHeuristicDetector`) relies on HSV color segmentation. In extreme low-light conditions (<15 Lux) with high sensor gain noise, color boundaries shift, resulting in lower detection confidence for translucent specimen tubes.
- **System Behavior:**  
  The primary neural detector (`ASTRA_OBJECT_DETECTOR_v1.0`) is invariant to illumination drops down to 10 Lux. If fallback is engaged under near-total darkness, the system safely transitions to `UNCERTAIN` rather than false deviation.

---

## 3. Ground Monitor & Network Streaming

### 3.1 Browser MJPEG Client Ingestion Delays
- **Issue Description:**  
  When viewing the Ground Monitor live MJPEG video stream on high-latency wireless networks or resource-constrained mobile browsers, client-side buffer accumulation may introduce a 150–300 ms display lag relative to the live onboard console.
- **System Behavior:**  
  The onboard runtime processes frames in real-time ($<25$ ms latency) without buffering. Telemetry metadata transmitted over WebSockets remains synchronized using UTC timestamps.
- **Workaround:**  
  For low-latency ground monitoring, connect via Gigabit Ethernet or reduce streaming resolution in `final_demo.yaml` (`streaming.quality: 75`).

---

## 4. SQLite Telemetry & Storage Management

### 4.1 SQLite Multi-Process Concurrency under High Logging Rates
- **Issue Description:**  
  During high-rate stress tests (>60 FPS synthetic injection), concurrent read queries from external tools while the mission recorder is committing rapid batched transactions can occasionally trigger `sqlite3.OperationalError: database is locked`.
- **System Behavior:**  
  The SQLite storage adapter operates with WAL (Write-Ahead Logging) mode enabled and a 5.0-second busy timeout retry policy. No telemetry packets or mission events are lost.
- **Workaround:**  
  Ensure all external analytics access the telemetry database using read-only connection URIs (`file:mission.db?mode=ro`).

---

## 5. Summary Matrix of Caveats

| Subsystem | Condition | Manifestation | Mitigation / System Action |
| :--- | :--- | :--- | :--- |
| **Audio** | Headless container / no soundcard | Audio init warning | Auto-switches to visual guidance & simulated TTS |
| **Vision** | Extreme lighting flare | Confidence drops | Transitions to `UNCERTAIN` dwell window |
| **Camera** | Disconnected during run | Frame timeout | Instantly enters `VERIFICATION PAUSED` |
| **Network** | Physical link drop | Ground stream paused | Onboard core continues 100% uninterrupted |
| **Storage** | Disk threshold < 500 MB | Storage warning flag | Gracefully purges old debug caches; preserves mission log |
