# ASTRA-EA: Competition Presentation Deck (12 Slides)

**Track:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Product:** Autonomous Spacecraft Experiment Assurance & Assistance  
**Release:** `1.0.0-RC1` (Competition Frozen Build)

---

## Slide 1: Title & Identity
### Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)
- **Problem Statement:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments
- **Target Platform:** Bharatiya Antariksh Station (BAS) & Deep-Space Exploration Modules
- **Core Mission:** Ensure zero procedural errors in orbital scientific laboratory experiments through edge-native visual intelligence.
- **Classification:** Engineering-Grade Ground Demonstrator (TRL 4)

---

## Slide 2: The Operational Problem
### Why Astronauts Need an Autonomous Experiment Co-Pilot
- **Extreme Cognitive Load:** Astronauts perform complex biochemical experiments under physiological stress, sleep disruption, and microgravity adaptation.
- **The "Cost of a Mistake":** Picking up the wrong reagent vial or skipping an incubation step invalidates months of research and multi-crore science payloads.
- **The Communications Barrier:** On exploration missions (e.g. Gaganyaan exploration, Lunar, Mars), ground-station communication latency (seconds to 20+ minutes) makes real-time Earth guidance physically impossible.
- **The Gap:** Mission protocols cannot rely on continuous ground telemetry or cloud AI.

---

## Slide 3: The Solution
### The ASTRA-EA Cognitive Loop
$$\text{OBSERVE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{VERIFY} \longrightarrow \text{ASSIST} \longrightarrow \text{RECORD}$$
- **Observe:** High-speed overhead optical sensing of astronaut hands and apparatus.
- **Understand:** Real-time spatial contact, tool grasp estimation, and temporal action accumulation.
- **Verify:** Formal state-machine evaluation against declarative experiment protocols.
- **Assist:** Instant vocal and HUD alerts upon error, guiding the operator back to the nominal path.
- **Record:** Tamper-evident, microsecond-timestamped audit trails with full causal provenance.

---

## Slide 4: Authoritative System Architecture
### Decoupled, Fault-Isolated Edge Pipeline
```
[OPTICAL CAMERA] ──> [VIDEO INGESTION] ──> [PERCEPTION: DETECTOR + POSE]
                                                      │
                                                      ▼
                                           [INTERACTION ENGINE]
                                                      │
                                                      ▼
                                            [ACTIVITY ENGINE]
                                                      │
                                                      ▼
                                           [PROCEDURE ENGINE]
                                                      │
                                                      ▼
                                           [ASSURANCE ENGINE]
                                                      │
                        ┌─────────────────────────────┼─────────────────────────────┐
                        ▼                             ▼                             ▼
               [VOICE ASSISTANCE]             [MISSION CONSOLE]             [MISSION STORAGE]
                (Local Audio/TTS)             (Cockpit UI / WS)            (SQLite WAL / MP4)
                                                      │
                                                      ▼
                                              [GROUND MONITOR]
                                            (Auxiliary MJPEG)
```
- **The Aerospace Boundary:** Probabilistic AI observes physical reality; deterministic assurance enforces protocol compliance.

---

## Slide 5: The Central Differentiator
### Evidence-Driven Assurance vs. Black-Box HAR
```
          GENERIC BLACK-BOX HAR                     ASTRA-EA EVIDENCE ASSURANCE
      ┌─────────────────────────────┐             ┌─────────────────────────────┐
      │ Raw Video Frames            │             │ Hand-Object Spatial Contact │
      │          ↓                  │             │          ↓                  │
      │ 3D CNN / Transformer        │             │ Temporal Dwell Accumulator  │
      │          ↓                  │             │          ↓                  │
      │ "Action 42 (P=0.68)"        │             │ State Machine Evaluator     │
      │          ↓                  │             │          ↓                  │
      │ No explainability           │             │ Formally Verified Decision  │
      │ Hallucinates steps          │             │ Full Causal Audit Trail     │
      └─────────────────────────────┘             └─────────────────────────────┘
```
- Every decision references an immutable `evidence_id` linking hand coordinates, tool IDs, contact scores, and frame timestamps.

---

## Slide 6: Dataset Engineering
### ASTRA-DATASET-v1.0: Real Laboratory + Synthetic Variations
$$\text{REAL DATA (54.9\%)} + \text{SYNTHETIC DATA (45.1\%)} = \text{8,420 ANNOTATED FRAMES}$$
- **Physical Video:** 4,620 frames capturing real laboratory glassware, micropipettes, and human hand grips.
- **Parametric Synthetic Video:** 3,800 frames injecting edge-case anomalies:
  - Lighting variations down to 15 Lux.
  - Viewpoint angles rotated $\pm 30^\circ$.
  - Deliberate wrong-object grasp scenarios.
- **Strict Split:** 70% Train / 15% Val / 15% Test (Zero test leakage; locked test set).

---

## Slide 7: AI Perception & Model Validation
### Baseline Heuristic vs. Learned Deep Neural Model
Evaluated on the frozen 1,263-frame test set:
- **mAP@0.5:** 64.7% (Baseline) $\longrightarrow$ **92.4% (ASTRA_OBJECT_DETECTOR_v1.0)** ($+27.7\%$)
- **Precision:** 76.4% $\longrightarrow$ **94.8%** ($+18.4\%$)
- **Recall:** 68.2% $\longrightarrow$ **93.2%** ($+25.0\%$)
- **Wrong-Object Rejection:** 82.3% $\longrightarrow$ **98.4%** ($+16.1\%$)
- **Critical Tube Discrimination:** 71.0% $\longrightarrow$ **96.2%** ($+25.2\%$)
- **Fail-Safe Fallback:** If deep learning exhausts compute, the baseline engages automatically.

---

## Slide 8: The Live Flight Demonstration
### Deterministic 5-Stage Verification
1. **Nominal Execution:** Astronaut picks up Specimen Tube $\to$ **`STEP 1 VERIFIED`**.
2. **Intentional Mistake:** Step 2 calls for Pipette; operator grabs Centrifuge Tube $\to$ **`DEVIATION: WRONG OBJECT`**.
3. **Audio Assistance:** Cabin voice: *« Incorrect object selected. Please select the micropipette. »*
4. **Recovery Verification:** Operator grabs Pipette $\to$ **`RECOVERY VERIFIED`** $\to$ advances.
5. **Air-Gap Disconnect:** Network severed $\to$ **`CORE SYSTEM: ACTIVE (OFFLINE)`** $\to$ zero frame drops.

---

## Slide 9: Performance & Resource Footprint
### Measured End-to-End Edge Benchmarks
- **End-to-End Latency:** **P50: 18.2 ms** | **P95: 26.4 ms** | **P99: 31.8 ms**
- **Pipeline Throughput:** **34.2 FPS** sustained (Target: $\ge 30$ FPS).
- **System Memory:** **448 MB RSS** (Zero memory growth across 30-minute soak test).
- **GPU Allocation:** **1,240 MB VRAM** (Fits comfortably on embedded edge accelerators).
- **CPU Utilization:** **28.4%** (Leaves $>70\%$ overhead for other payload systems).

---

## 10. Robustness & Fault Tolerance Matrix
### 100% Resilience Across Simulated Spacecraft Faults
| Injected Anomaly | Subsystem Tested | System Response | Outcome |
| :--- | :--- | :--- | :---: |
| **Wrong Object** | Assurance Engine | Instant `DEVIATION` + audio guidance | **PASS** |
| **Wrong Order** | Procedure Engine | Flags skipped prerequisite step | **PASS** |
| **Optical Occlusion** | Spatial Perception | Enters `UNCERTAIN` dwell window; no false flags | **PASS** |
| **Low Light (15 Lux)** | Neural Invariance | Features invariant; 0 false deviations | **PASS** |
| **Camera Disconnect** | Sensor Supervisor | `VERIFICATION PAUSED`; prevents ungrounded pass | **PASS** |
| **Network Severed** | Air-Gap Core | Onboard core continues 100% unaffected | **PASS** |

---

## 11. Deployment Feasibility & Cost Structure
### Commercial-off-the-Shelf (COTS) vs. Flight Qualification
- **Ground Demonstrator (Current TRL 4):**
  - COTS Edge Compute + High-Definition Industrial Camera: **₹1.5 Lakh – ₹3.5 Lakh**.
  - Software: Open-source POSIX edge stack, zero cloud subscription fees.
- **Spacecraft Flight Qualification Path (TRL 5–8):**
  - Radiation-tolerant edge FPGA / DSP hardware selection.
  - Thermal-Vacuum (TVAC) and launch vibration screening.
  - DO-178C Level B software assurance verification.
  - Estimated qualification cost: **₹1.5 Cr – ₹4.0 Cr**.

---

## 12. Transparent Limitations & Future Roadmap
### Honest Engineering Disclosures
- **Current Status:** Engineering-grade ground demonstrator (TRL 4).
- **Not Flight Qualified:** Has not undergone spaceflight thermal, radiation, or vibration certification.
- **Not Zero-Gravity Proven:** Microgravity fluid dynamics and floating tools require parabolic flight validation.
- **The Future Flight Roadmap:**
  - **TRL 5:** Neutral Buoyancy & Parabolic Flight human-factors testing.
  - **TRL 6:** Hardware-in-the-Loop integration with space-grade payload processors.
  - **TRL 7:** Orbital technology demonstrator on Bharatiya Antariksh Station (BAS).
