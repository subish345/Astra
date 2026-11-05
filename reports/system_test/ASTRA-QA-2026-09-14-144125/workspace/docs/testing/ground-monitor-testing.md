# ASTRA-EA — Ground Monitor Testing Strategy

## Automated and Headless Verification for Ground Observation Console

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Headless Execution Strategy

The Ground Monitor is built using PySide6 (Qt) and designed for continuous remote observability. To support automated CI pipelines and headless validation on headless edge/server environments, the Ground Monitor test suite utilizes Qt's offscreen platform plugin:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ground_monitor/ -v
```

This ensures complete verification of widget layouts, reactive signal-slot propagation, state reconciliation, and visual badge styling without requiring a connected X11/Wayland display server.

---

## 2. Test Suites Overview

| Test Suite | File | Focus Areas |
| :--- | :--- | :--- |
| **State Model Tests** | [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | `GroundMonitorState` dataclass mutation, Qt signal dispatching (`state_changed`, `timeline_added`, `alert_added`), sequence ordering, and timeline trimming. |
| **Header Panel Tests** | [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | Link quality badge styling (`ONLINE`, `DEGRADED`, `OFFLINE`), dual-channel indicators (Video / Telemetry), reconnect counter, and mode banner (`SIMULATION MODE`). |
| **Video Panel Tests** | [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | Video stream display, overlay diagnostics (FPS, bitrate, dropped frames), aspect ratio preservation, and "VIDEO OFFLINE" fallback placeholder. |
| **Mission Panel Tests** | [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | Experiment ID, run ID, step counter badge (`STEP 03 / 04`), verification state (`VERIFIED`, `UNCERTAIN`, `DEVIATED`), and current activity description. |
| **Alert & Timeline Tests** | [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | Active deviation alerts, recovery status banners, chronological event list with filter tabs (`ALL`, `STEPS`, `DEVIATIONS`, `RECOVERY`, `SYSTEM`), onboard vs transit latency display. |
| **Health Panel Tests** | [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | CPU/RAM telemetry gauges, camera sensor status, pipeline FPS, heartbeat age indicator. |
| **Evidence Viewer Tests** | [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | Read-only modal dialog, metadata inspection (step, confidence, bounding boxes), image/video preview, export button safety. |
| **Integration Window Tests**| [`tests/ground_monitor/test_ground_monitor.py`](file:///home/subish-loq/Documents/astra/tests/ground_monitor/test_ground_monitor.py) | `GroundMonitorWindow` full composition, signal dispatching, event server feed ingestion, connection drop UX handling. |

---

## 3. Disconnect & Reconnect Verification

Ground Monitor resilience against network dropouts is verified through automated state simulation:
1. **Link Loss:** Disconnecting event/video channels switches link status to `LINK LOST: RECONNECTING...` while preserving the last known experiment state and timeline.
2. **Reconnection Catch-up:** Restoring connection transitions status to `LINK RESTORED`, triggers `/events/replay?since={seq}` catch-up, and updates current procedure progress without UI tearing.
3. **No State Mutation:** Asserts that no UI buttons or actions trigger mutative calls back to the onboard execution core.

---

## 4. Running Ground Monitor Tests

```bash
# Run all Ground Monitor unit and integration tests
pytest tests/ground_monitor/ -v

# Run full Phase 9 test suite (streaming + ground monitor + network)
pytest tests/streaming/ tests/ground_monitor/ tests/network/ -v

# Launch Ground Monitor in live mode (requires active mission or simulation stream)
python3 main.py ground-monitor --host 127.0.0.1
```
