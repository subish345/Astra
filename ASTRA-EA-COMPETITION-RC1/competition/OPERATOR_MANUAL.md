# ASTRA-EA: Comprehensive Operator Manual

**Classification:** Standard Operating Procedure (SOP)  
**System:** Autonomous Spacecraft Experiment Assurance & Assistance  
**Build:** `ASTRA-EA-COMPETITION-RC1`

---

## 1. System Startup & Initialization

### 1.1 Cold Boot Procedure
1. Power on the demonstration workstation.
2. Confirm the user environment has the `astra` executable in `$PATH`:
   ```bash
   which astra
   ```
3. Run the automated pre-flight audit:
   ```bash
   astra competition-check
   ```
4. If any item reports `FAIL`, consult Section 13 (Troubleshooting).

### 1.2 Starting the Demonstration Runtime
Execute the unified demo launcher:
```bash
astra demo
```
Options:
- `--headless`: Executes in terminal mode without launching GUI web workers (ideal for low-power or remote testing).
- `--camera <device_id>`: Overrides camera source (e.g. `--camera 0` or `--camera 2`).
- `--config <path>`: Overrides configuration profile (defaults to `configs/deployment/final_demo.yaml`).

---

## 2. System Shutdown & Clean Exit

### 2.1 Graceful Termination
1. In the terminal running `astra demo`, issue an interrupt signal:
   ```bash
   Ctrl + C
   ```
2. The runtime initiates a coordinated shutdown sequence:
   - Finalizes active SQLite WAL database transactions.
   - Flushes pending video frames to disk and finalizes MP4 headers.
   - Closes WebSocket connections and shuts down HTTP server threads.
   - Logs `MISSION COMPLETED / TERMINATED` with final duration.

---

## 3. Experiment Operations Lifecycle

### 3.1 Starting an Experiment Run
1. Navigate to the Mission Console at `http://127.0.0.1:8000`.
2. Ensure the video feed is displaying live optical frames with detected object bounding boxes.
3. Click the **"BEGIN EXPERIMENT"** button on the cockpit header.
4. The system transitions state: `READY` $\to$ `STARTING` $\to$ `RUNNING`.
5. Step 1 (`select_specimen_tube`) becomes active, indicated by an amber glowing card with target object icons.

### 3.2 Resetting an Experiment Run
If an experiment must be restarted due to operator missteps:
1. Click the **"RESET RUN"** button on the top-right control cluster.
2. Confirm the reset dialog.
3. The previous run state is archived to `data/runs/RUN_ARCHIVE_<timestamp>/`.
4. The procedure state machine resets to Step 1 without restarting the application processes.

---

## 4. Optical Camera Setup & Viewpoints

### 4.1 Physical Positioning
- **Height & Distance:** Mount the camera 40–60 cm above the experiment surface, angled downward at $35^\circ–45^\circ$.
- **Field of View (FoV):** Ensure the entire tool workspace (test tube rack, micropipette holder, and active manipulation zone) is visible within the 1080p frame.
- **Lighting:** Maintain uniform diffused lighting. Avoid direct spotlighting that causes glare on transparent glassware.

### 4.2 Switching Viewpoint Profiles
ASTRA-EA supports calibrated viewpoint transformations:
- **Lateral Left (`VIEW_LEFT`):** Default demonstration profile.
- **Lateral Right (`VIEW_RIGHT`):** Configured via:
  ```bash
  astra demo --config configs/deployment/view_right.yaml
  ```
The spatial interaction engine preserves contact topology across both perspectives.

---

## 5. Model Selection & Fallback Operation

### 5.1 Active Production Model
- **Primary:** `ASTRA_OBJECT_DETECTOR_v1.0` (PyTorch/ONNX neural detector, 94.8% precision, 14.8 ms latency).
- **Secondary Fallback:** `BaselineColorHeuristicDetector` (Rule-based HSV color segmenter).

### 5.2 Engaging Fallback
If the neural model encounters hardware memory limits:
```bash
astra demo --fallback-baseline
```
The system will log `PERCEPTION: RUNNING IN BASELINE FALLBACK` and continue procedure verification.

---

## 6. Offline Air-Gap Operation

ASTRA-EA is 100% offline-native:
1. Disconnect Ethernet cables and disable WiFi interfaces.
2. Launch `astra demo`.
3. The Mission Console operates via `http://localhost:8000`.
4. Perception, pose estimation, procedure tracking, audio alerts, and MP4 video recording run locally with zero network traffic.

---

## 7. Ground Monitor Streaming

### 7.1 Accessing the Ground Station UI
While `astra demo` is running, open a secondary browser tab or an external computer on the local network:
```
http://<workstation-ip>:8080
```
### 7.2 Monitored Telemetry
- **Video:** Low-bandwidth MJPEG live feed with ground telemetry overlay.
- **State:** Current active procedure step and countdown timer.
- **Alert Stream:** Instant notification of any `DEVIATION` or `RECOVERY` events.

---

## 8. Procedural Deviation & Recovery Handling

### 8.1 Deviation Trigger
When an operator interacts with an incorrect object (e.g., picking up a centrifuge tube instead of a micropipette during Step 2):
1. The system detects the anomaly ($IoU > 0.05$ with non-target object).
2. The UI flashes an amber/red alert banner: `DEVIATION: WRONG OBJECT`.
3. The Voice Engine announces: *« Incorrect object selected. Please replace the centrifuge tube and select the micropipette. »*

### 8.2 Executing Recovery
1. Replace the incorrect tool in its holding rack.
2. Grasp the correct `pipette`.
3. The system confirms contact with the designated recovery target.
4. The UI transitions to `RECOVERY VERIFIED` (Green), clears the alert, and automatically resumes the nominal sequence.

---

## 9. Evidence Review & Audit Traceability

### 9.1 Live Evidence Drawer
1. On the Mission Console, click the **"EVIDENCE LOG"** tab.
2. Select any completed or deviated step.
3. Review:
   - Microsecond timestamp of interaction.
   - Hand bounding box coordinates and object track ID.
   - Spatial contact score ($IoU$).
   - High-resolution snapshot image highlighting the contact point.

### 9.2 Standalone Traceability Audit
To view the complete vertical causal trace in an external browser:
```bash
xdg-open final_traceability_example.html
```

---

## 10. Log Files & Storage Management

All mission records are preserved under `data/runs/`:
- `config_snapshot.yaml`: Effective configuration parameters.
- `model_snapshot.json`: Exact model checksum and threshold settings.
- `events.json`: Microsecond-timestamped JSON envelope events.
- `timeline.json`: Human-readable chronological milestones.
- `mission_report.json` & `.html`: Post-mission summary audit report.
- SQLite Database: Persistent audit trail stored in `storage/astra.db`.
