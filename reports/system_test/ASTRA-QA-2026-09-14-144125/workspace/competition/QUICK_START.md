# ASTRA-EA: Operator Quick Start Guide

**Audience:** Demonstration operators, evaluators, and judges.  
**Requirement:** Zero prior knowledge of the codebase. All actions use native CLI commands.

---

## The 6-Step Demonstration Workflow

```
[1. POWER ON] ──> [2. CONNECT CAMERA] ──> [3. RUN CHECK]
                                                 │
                                                 ▼
[6. START RUN] <── [5. VERIFY READY] <── [4. RUN ASTRA-EA]
```

---

### Step 1: Power On & Terminal
1. Boot the workstation / laptop.
2. Open a terminal and navigate to the project directory:
   ```bash
   cd ~/Documents/astra
   ```

---

### Step 2: Connect Hardware
1. Connect the primary USB webcam to any high-speed USB 3.0 port.
2. Ensure audio output (speakers or headphones) is active and unmuted.
3. Place experiment items on the workspace:
   - `specimen_tube` (green cap / standard test tube)
   - `centrifuge_tube` (blue cap / conical tube)
   - `pipette` (micropipette tool)
   - `tube_rack` (holding rack)

---

### Step 3: Run Environment & Readiness Check
Run the automated pre-flight readiness audit:
```bash
astra competition-check
```
*Expected output: All 15 subsystems report `PASS`, culminating in `STATUS: READY`.*

If testing live camera nodes specifically, run:
```bash
astra final-check
```
*Expected output: `SYSTEM: READY FOR DEMONSTRATION`.*

---

### Step 4: Launch ASTRA-EA Demonstration
Launch the integrated demonstration session:
```bash
astra demo
```
*Behind the scenes, this loads `configs/deployment/final_demo.yaml`, initializes video ingestion, loads the frozen neural model, starts the Mission Console at `http://127.0.0.1:8000`, and starts Ground Monitor streaming at `http://127.0.0.1:8080`.*

---

### Step 5: Verify System "READY" Status
1. Open your browser to the Mission Console:
   ```
   http://127.0.0.1:8000
   ```
2. Verify the top status banner displays:
   - **System State:** `READY` (Cyan)
   - **Camera Stream:** Active 30+ FPS optical feed
   - **Model:** `ASTRA_OBJECT_DETECTOR_v1.0`
   - **Procedure:** `DEMO_EXP_001` (Step 1 Pending)

---

### Step 6: Start Experiment & Follow On-Screen Guidance
1. Click **"Start Mission"** on the Mission Console UI (or press spacebar).
2. Follow the verbal and visual cues:
   - **Nominal Step 1:** Pick up the `specimen_tube`. The console will chime and show `STEP 1 VERIFIED`.
   - **Deviation Step 2:** Pick up the `centrifuge_tube` instead of the pipette. The system triggers `DEVIATION: WRONG OBJECT` with voice guidance.
   - **Recovery Step 2:** Return the tube and pick up the `pipette`. The system validates `RECOVERY VERIFIED` and advances.
3. At the end of the procedure, review the automatically generated mission report.
