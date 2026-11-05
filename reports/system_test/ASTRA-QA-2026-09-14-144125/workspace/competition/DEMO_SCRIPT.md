# ASTRA-EA: Timed Judge Demonstration Script (5–8 Minutes)

**Track:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Target Duration:** 7 Minutes 30 Seconds  
**Demonstration Profile:** `configs/deployment/final_demo.yaml`  
**Presenters:** Operator (Hands-on physical workspace) & Presenter (Narrative & slide/console reference)

---

## Chronological Demonstration Flow

```
0:00 ──── 0:30 ──── 1:00 ──── 1:30 ──── 3:00 ──── 4:00 ──── 5:00 ──── 6:00 ──── 7:00 ──── 7:30
  │         │         │         │         │         │         │         │         │         │
Problem   Arch     Launch    Nominal  Deviation  Recovery  Offline  Traceable Ground   Summary
```

---

### [0:00 – 0:30] The Operational Problem
- **Presenter:**  
  *"Respected judges, during scientific missions on the Bharatiya Antariksh Station, astronauts perform critical bio-assay and materials experiments under severe cognitive load. An accidental tool swap or an omitted incubation step invalidates months of research. Because deep-space communication delays make real-time guidance from Earth impossible, astronauts need an autonomous, offline co-pilot that watches the experiment, understands what is happening, verifies protocol compliance, and helps them recover immediately if an error occurs. That is ASTRA-EA."*

---

### [0:30 – 1:00] The Core Architecture
- **Presenter:**  
  *"ASTRA-EA does not treat procedure monitoring as a black-box video classification problem. We decouple probabilistic computer vision from deterministic state assurance:*
  $$\text{Camera} \longrightarrow \text{Perception} \longrightarrow \text{Interaction} \longrightarrow \text{Activity} \longrightarrow \text{Evidence} \longrightarrow \text{Procedure Engine} \longrightarrow \text{Assurance}$$
  *The AI observes physical contact; the procedure engine knows what should happen; the assurance engine formally verifies whether it did."*

---

### [1:00 – 1:30] System Startup & Pre-Flight Check
- **Operator Action:** Execute in terminal:
  ```bash
  astra final-check
  ```
- **Presenter:**  
  *"Notice our automated pre-flight audit: 13 subsystems—from camera ingestion to SQLite WAL storage and edge neural weights—verified in under 2 seconds. The system confirms `READY FOR DEMONSTRATION`."*
- **Operator Action:** Launch demo:
  ```bash
  astra demo
  ```
  Open browser to `http://localhost:8000`.

---

### [1:30 – 3:00] Normal Experiment Execution (Step 1)
- **Presenter:**  
  *"Let us begin the experiment. Step 1 requires the astronaut to select the specimen tube."*
- **Operator Action:** Reach into the workspace and grasp the `specimen_tube`.
- **System Behavior:**
  - Optical bounding boxes track hand and tube.
  - Hand-object contact detected ($IoU > 0.05$).
  - Temporal accumulator confirms sustained interaction ($>10$ frames).
  - Mission Console chimes and displays **`STEP 1 VERIFIED`** (Green).
- **Presenter:**  
  *"Notice the immediate transition. The system didn't guess; it established an explicit evidence bundle: hand track ID, tube class score, and spatial contact duration."*

---

### [3:00 – 4:00] Intentional Procedural Deviation (Wrong Object)
- **Presenter:**  
  *"Now, let us introduce an intentional human error. Step 2 requires the micropipette. Instead, the operator mistakenly picks up a conical centrifuge tube."*
- **Operator Action:** Grasp the `centrifuge_tube`.
- **System Behavior:**
  - The Assurance Engine compares observed contact (`centrifuge_tube`) against the required target (`pipette`).
  - Anomaly detected: **`DEVIATION: WRONG OBJECT`**.
  - Cockpit Voice Engine speaks:  
    *« Alert. Incorrect object selected. Please replace the centrifuge tube and select the micropipette. »*
  - Console flashes amber warning banner.
- **Presenter:**  
  *"ASTRA-EA immediately intercepts the error before the experiment is compromised, explains the exact mistake, and gives explicit recovery instructions."*

---

### [4:00 – 5:00] Active Recovery Verification
- **Presenter:**  
  *"A critical differentiator: ASTRA-EA doesn't just alert; it arms a recovery state and watches to ensure the mistake is actually rectified."*
- **Operator Action:** Replace the centrifuge tube and pick up the `pipette`.
- **System Behavior:**
  - Contact with `pipette` confirmed.
  - Console transitions to **`RECOVERY VERIFIED`** (Green).
  - Procedure safely advances to Step 3 (`dispense_reagent`).
- **Presenter:**  
  *"The anomaly is resolved and logged. No manual operator override was needed."*

---

### [5:00 – 6:00] Offline Air-Gap Operation
- **Presenter:**  
  *"Can this survive deep-space signal loss? Let us sever the network entirely."*
- **Operator Action:** Unplug ethernet / disconnect WiFi.
- **System Behavior:**
  - Ground link indicator shows `DISCONNECTED`.
  - Onboard console banner shows: **`CORE SYSTEM: ACTIVE (OFFLINE)`**.
- **Operator Action:** Perform Step 3 (`dispense_reagent`).
- **Presenter:**  
  *"Perception, interaction tracking, procedure state transitions, and local video recording continue at a steady 34 FPS. Zero dependency on cloud servers or ground telemetry."*

---

### [6:00 – 7:00] Traceability Audit & Ground Synchronization
- **Operator Action:** Reconnect network. Open `http://localhost:8080` (Ground Monitor) and `final_traceability_example.html`.
- **System Behavior:**
  - Ground Monitor automatically resynchronizes state without duplicate events.
- **Presenter:**  
  *"Here is our post-mission audit trail. In `final_traceability_example.html`, we trace the deviation event back through the expected step, observed activity, hand-object contact score, bounding box, and the raw camera frame. Every record is SHA-256 hash verified and locked to this exact git commit."*

---

### [7:00 – 7:30] Final Conclusion
- **Presenter:**  
  *"In summary:  
  **The camera sees.**  
  **The AI understands.**  
  **The procedure engine knows what should happen.**  
  **The assurance engine decides whether it did.**  
  **The assistant helps recover.**  
  **The evidence record explains why.**  
  ASTRA-EA provides the engineering foundation for autonomous experiment assurance aboard the Bharatiya Antariksh Station. We welcome your questions."*
