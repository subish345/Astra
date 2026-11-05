# ASTRA-EA: Final Judge Demonstration Guide & Script

**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Track:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Profile:** `configs/deployment/final_demo.yaml`  
**Execution Command:** `astra demo`

---

## 1. Demonstration Overview & Setup

The ASTRA-EA Judge Demonstration is a deterministic, 5–8 minute structured presentation designed to prove end-to-end edge-AI autonomy, zero network dependence for mission-critical functions, explainable evidence tracing, real-time procedural assurance, and rapid deviation recovery.

### Pre-Demo Verification
Run the system self-test before inviting judges to observe:
```bash
astra final-check
```
*Expected output: All 13 subsystems verified, ending with `SYSTEM: READY FOR DEMONSTRATION`.*

Launch the unified demo session:
```bash
astra demo
```
*Loads `configs/deployment/final_demo.yaml`, initializes camera ingestion, loads `ASTRA_OBJECT_DETECTOR_v1.0`, binds the local SQLite telemetry database, starts the Mission Console at `http://127.0.0.1:8000`, and streams telemetry to Ground Monitor at `http://127.0.0.1:8080`.*

---

## 2. 5–8 Minute Judge Demonstration Script

```
                +----------------------------------------+
                |          1. THE PROBLEM (1m)           |
                |   Astronaut cognitive load & isolated  |
                |        microgravity experiment errors  |
                +-------------------+--------------------+
                                    |
                                    v
                +----------------------------------------+
                |          2. THE SOLUTION (1m)          |
                |  Observe -> Understand -> Verify ->   |
                |            Assist -> Record            |
                +-------------------+--------------------+
                                    |
                                    v
                +----------------------------------------+
                |     3. NORMAL OPERATION STEP 1 (1m)    |
                |    Select Specimen Tube -> VERIFIED    |
                +-------------------+--------------------+
                                    |
                                    v
                +----------------------------------------+
                |    4. EXPLAINABLE INTELLIGENCE (1m)    |
                |  Hand-object IoU, bounding box trace,  |
                |      temporal activity accumulator     |
                +-------------------+--------------------+
                                    |
                                    v
                +----------------------------------------+
                |       5. INTENTIONAL ERROR (1m)        |
                | Grab Centrifuge Tube instead ->        |
                |         DEVIATION TRIGGERED            |
                +-------------------+--------------------+
                                    |
                                    v
                +----------------------------------------+
                |     6. AUDIO ASSISTANCE & RECOVERY     |
                | Voice: "Incorrect object selected..."  |
                |    Select Pipette -> RECOVERY VERIFIED |
                +-------------------+--------------------+
                                    |
                                    v
                +----------------------------------------+
                |   7. OFFLINE RESILIENCE & TELEMETRY    |
                |   Sever link -> Core System ACTIVE     |
                | Reconnect -> Ground Monitor synchronized|
                +-------------------+--------------------+
                                    |
                                    v
                +----------------------------------------+
                |        8. TRACEABILITY AUDIT           |
                | Open final_traceability_example.html   |
                | Run-ID locked causal chain to frame    |
                +----------------------------------------+
```

### Minute 1: The Problem
- **Presenter Statement:**  
  *"During orbital laboratory missions, astronauts perform intricate biological and material experiments under intense cognitive load and strict protocols. In microgravity, selecting the wrong vial or skipping an incubation step invalidates months of research. Because communication latency with ground stations can exceed 20 minutes on exploration missions, experiment assurance cannot rely on Earth-bound operators or cloud AI."*
- **Visual:** Point to the Mission Console standby screen showing zero active cloud dependencies.

### Minute 2: The Solution
- **Presenter Statement:**  
  *"ASTRA-EA solves this with an edge-native cognitive loop: Observe, Understand, Verify, Assist, and Record. It turns overhead optical sensors into an active assurance co-pilot that watches physical interactions, evaluates them against formal state-machine protocols, provides immediate vocal guidance upon mistakes, and produces an unalterable audit log."*

### Minute 3: Normal Operation (Step 1)
- **Action:** Operator reaches into the experiment workspace and grasps the `specimen_tube`.
- **System Behavior:**
  - Perception detects `hand` and `specimen_tube` with bounding boxes.
  - Interaction engine detects spatial contact ($IoU > 0.05$).
  - Activity engine classifies `holding_tube` ($confidence > 0.85$).
  - Procedure engine transitions Step 1: `select_specimen_tube` $\to$ `IN_PROGRESS` $\to$ `VERIFIED`.
  - Mission Console displays green verification badge with timestamp.
- **Presenter Statement:**  
  *"Notice the immediate transition. The system doesn't guess from raw video pixels; it builds an evidence chain connecting human pose, object detection, and spatial overlap."*

### Minute 4: Explainable Intelligence
- **Action:** Pause briefly on the Mission Console Evidence Drawer.
- **Presenter Statement:**  
  *"Every decision is transparent. We can inspect the exact evidence bundle: the hand track ID, the object classification score, the temporal dwell window, and the procedure condition. Zero black-box hallucinations."*

### Minute 5: Intentional Error (Deviation)
- **Action:** Step 2 calls for `select_pipette`. The operator deliberately reaches for `centrifuge_tube` instead.
- **System Behavior:**
  - Interaction engine registers `holding_centrifuge_tube`.
  - Assurance engine evaluates state against procedure expectations.
  - State machine triggers `DEVIATION` (Severity: `WARNING`, Deviation Type: `WRONG_OBJECT`).
  - Mission Console flashes amber alert with full contextual explanation: *"Expected pipette, observed centrifuge_tube"*.

### Minute 6: Assistance & Recovery
- **System Audio:**
  - Voice engine announces through cockpit audio:  
    *« Alert. Incorrect object selected. Please replace the centrifuge tube and select the micropipette. »*
- **Action:** Operator returns the centrifuge tube and picks up the correct `pipette`.
- **System Behavior:**
  - Recovery handler evaluates corrective action.
  - Assurance engine records `RECOVERY_VERIFIED`.
  - Procedure resumes normal progression to Step 3.
- **Presenter Statement:**  
  *"ASTRA-EA doesn't just halt on error; it guides the astronaut back to the nominal path and formally verifies that the corrective action occurred before allowing the experiment to proceed."*

### Minute 7: Offline Resilience & Ground Sync
- **Action:** Physically unplug the ethernet/WiFi interface or disable network bridge.
- **System Behavior:**
  - Ground telemetry link shows `DISCONNECTED`.
  - Mission Console and Onboard Ingestion HUD show `CORE SYSTEM: ACTIVE (OFFLINE)`.
  - Complete Step 3 (`dispense_reagent`) while offline. Evidence is recorded to local SQLite.
- **Action:** Reconnect network.
- **System Behavior:**
  - Ground Monitor at `http://localhost:8080` immediately resynchronizes state, catches up missed events, without duplicating runs or dropping telemetry.
- **Presenter Statement:**  
  *"Critical science assurance never stops for network outages. The spacecraft core remains 100% autonomous."*

### Minute 8: Traceability Audit
- **Action:** Open `final_traceability_example.html` in browser.
- **Presenter Statement:**  
  *"Finally, post-mission science verification requires absolute accountability. Here is our end-to-end causal trace: from the high-level Deviation flag, down through the expected step, observed activity, interaction bundle, bounding box coordinates, and raw camera frame index. Every step is cryptographically hash-verifiable and tied to the exact model and procedure versions."*

---

## 3. Comprehensive Judge Q&A Preparation (Section 45)

### Q1: Why not just use a generic Human Activity Recognition (HAR) dataset?
**Answer:**  
Generic HAR datasets (like UCF101, Kinetics, or Charades) focus on broad whole-body coarse actions like walking, jumping, or cooking. Laboratory science experiments require fine-grained hand-object affordances, precise object identity differentiation (e.g., distinguishing a specimen tube from a centrifuge tube of similar shape), spatial contact thresholds, and strict sequential ordering constraints. A generic HAR model lacks object class specificity and temporal state-machine awareness required for formal procedure verification.

### Q2: Why synthetic data?
**Answer:**  
Spacecraft experiments involve rare, safety-critical failure modes—such as dropped sample vials, cross-contamination, incorrect sequence execution, and severe camera lighting flares—which cannot be captured abundantly or ethically in physical lab sessions. Our synthetic pipeline systematically renders controlled variations in viewpoint angles ($\pm 30^\circ$), lighting drops (down to 10 lux), and anomalous object swaps, ensuring the model generalizes across environmental edge cases before touching real hardware.

### Q3: Why offline?
**Answer:**  
Deep-space exploration platforms operate outside the coverage of constant low-latency communication networks (TDRS or DSN). Cloud-based inference models introduce unacceptable latencies (seconds to tens of minutes), transmission bandwidth costs, and single points of failure. ASTRA-EA runs entirely locally on edge hardware (P50 latency 14.8 ms on GPU, 32.1 ms on CPU), guaranteeing zero mission disruption during signal blackouts.

### Q4: What happens when the AI is uncertain?
**Answer:**  
ASTRA-EA implements an explicit three-state epistemic model: `VERIFIED`, `UNCERTAIN`, and `DEVIATION`. If optical occlusions, low lighting, or marginal detection scores occur, the system classifies the state as `UNCERTAIN` and initiates an observation dwell window. It will *never* prematurely declare a false deviation or falsely verify a step. Only if the uncertainty window expires without resolution does it prompt the user for visual re-acquisition.

### Q5: What happens when the astronaut makes a mistake?
**Answer:**  
When an unexpected object or incorrect sequence action is registered with high confidence, the Assurance Engine transitions to `DEVIATION`. It instantly generates a structured anomaly record, provides localized voice feedback explaining exactly what went wrong, displays visual guidance on the Mission Console, and arms an active recovery condition that verifies the corrective action before progressing.

### Q6: What happens if the network fails?
**Answer:**  
The network boundary in ASTRA-EA is strictly one-way and decoupled. Perception, interaction, activity classification, procedure state tracking, voice assistance, and video recording all run as local UNIX processes communicating via in-memory queues and local SQLite databases. A network drop only pauses the Ground Monitor streaming adapter; onboard operations continue without dropped frames or degraded FPS. Upon reconnection, backlogged events are automatically synchronized.

### Q7: What happens if the camera fails?
**Answer:**  
The Ingestion Health Monitor detects frame freeze or sensor disconnect within 3 frames ($<100$ ms). It immediately transitions the procedure engine into `VERIFICATION PAUSED` and alerts the operator. Crucially, no procedure steps are ever falsely verified during camera blackout. When the video stream is re-established, the system verifies camera stability before prompting the operator to resume the active step.

### Q8: What happens if the model fails?
**Answer:**  
ASTRA-EA features a dual-tier perception architecture with an automated fallback policy. If the learned neural detector (`ASTRA_OBJECT_DETECTOR_v1.0`) crashes or throws an inference exception, the Runtime Supervisor logs the failure, raises a telemetry alert, and falls back to the deterministic, rule-based baseline detector (`BaselineColorHeuristicDetector`). If all vision fails, the system enters a graceful `PERCEPTION DEGRADED` state, preventing ungrounded procedure state transitions.

### Q9: How do you explain an AI decision?
**Answer:**  
Decisions are never black boxes. Every procedure step verification or deviation event references an immutable `evidence_id`. This ID links directly to the spatial bounding boxes of the detected hands and objects, the mathematical intersection-over-union ($IoU$) contact score, the temporal duration of the interaction, the specific procedure step rule that was evaluated, and the raw video frame timestamp. This complete causal tree is viewable in both the Mission Console and the standalone `final_traceability_example.html`.

### Q10: Can the experiment procedure change?
**Answer:**  
Yes. ASTRA-EA is completely decoupled from any hardcoded experiment. Procedures are defined declaratively in validated YAML schemas (specifying step keys, required objects, action types, prerequisite steps, timeout durations, and recovery conditions). Introducing a new experiment requires only authoring a YAML file and running `astra procedure validate --config <file>`. No C++ or Python code changes are required.

### Q11: Can the model change?
**Answer:**  
Yes. The perception engine adheres to an abstract `BaseDetector` interface registered via our Model Registry. New architectures (e.g., YOLOv8, MobileNet-SSD, or custom PyTorch models) can be packaged with standardized metadata, registered with `astra model register`, and activated without altering the downstream interaction or assurance engines.

### Q12: Does camera angle matter?
**Answer:**  
Our system has been explicitly tested across multiple physical perspectives, including lateral views (`VIEW_LEFT`, `VIEW_RIGHT`) and top-down angles. Because the interaction engine relies on relative spatial proximity, hand-object contact topology, and temporal action accumulation rather than absolute 2D coordinate positions, it achieves semantic consistency across viewpoints even when raw optical bounding boxes differ.

### Q13: Is this flight-ready?
**Answer:**  
**No.** We state clearly that ASTRA-EA is an **engineering-grade ground demonstrator (TRL 4)**. While its software architecture follows aerospace patterns (decoupled processes, deterministic state machines, bounded memory, fault-isolated subsystems), it has not undergone radiation hardening, thermal-vacuum qualification, vibration testing, zero-gravity parabolic flight validation, or ISRO/NASA flight certification. It provides the validated algorithmic foundation for future flight payload engineering.
