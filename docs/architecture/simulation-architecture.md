# ASTRA-EA Simulation & Fault Injection Architecture

Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Executive Overview

The **ASTRA-EA Simulation & Fault Injection Platform** (Phase 8) provides an automated mission simulation and stress-testing harness designed to validate system resilience under extreme non-ideal spaceflight conditions without requiring physical spaceflight hardware or human actors.

Every simulated run executes the **full, unmodified production pipeline**—ensuring that synthetic or degraded frames traverse the real `CameraSource`, `PerceptionPipeline`, `SpatialInteractionEngine`, `TemporalBuffer`, `MultimodalEvidenceEngine`, `ProcedureProgressManager`, and `TriStateAssuranceEngine`.

```
                        SIMULATION ARCHITECTURE
                        
 +-------------------------------------------------------------------------+
 |                      SimulationScenario (YAML)                          |
 |  - Scenario ID, target FPS, duration, camera viewpoint                  |
 |  - Timed FaultTriggers (Optical, Behavioral, Perception, Viewpoint)     |
 +-------------------------------------------------------------------------+
                                    │
                                    ▼
 +-------------------------------------------------------------------------+
 |                      SimulatedCameraSource                              |
 |  - Implements CameraSource contract                                     |
 |  - Dynamic procedural scene renderer (SyntheticDatasetGenerator)        |
 |  - FaultInjectors (low light, glare, smudge, noise, black frame, drop)  |
 |  - Dynamic viewpoint switching (VIEW_LEFT <-> VIEW_RIGHT)               |
 +-------------------------------------------------------------------------+
                                    │
                               FrameData
                                    │
                                    ▼
 +-------------------------------------------------------------------------+
 |                        ASTRA-EA Pipeline Core                           |
 |                                                                         |
 |  [Perception Pipeline] ──> Color/Learned Detector + Tracker + Pose      |
 |           │                                                             |
 |           ▼                                                             |
 |  [Interaction Engine]  ──> Spatial contact & proximity analysis         |
 |           │                                                             |
 |           ▼                                                             |
 |  [Temporal Activity]   ──> Sliding-window primitive/composite engine    |
 |           │                                                             |
 |           ▼                                                             |
 |  [Evidence Engine]     ──> Multimodal evidence bundle synthesis         |
 |           │                                                             |
 |           ▼                                                             |
 |  [Assurance Engine]    ──> Tri-State decision (VERIFIED/UNCERTAIN/DEV)  |
 |           │                                                             |
 |           ▼                                                             |
 |  [Recovery Manager]    ──> Closed-loop astronaut guidance generation    |
 +-------------------------------------------------------------------------+
                                    │
                        SimulationDecisionRecord
                                    │
                                    ▼
 +-------------------------------------------------------------------------+
 |                    SimulationEngine & Matrix Runner                     |
 |  - Mean Time To Detect (MTTD) calculation                               |
 |  - False-positive deviation tracking under optical stress               |
 |  - Pipeline crash immunity verification                                 |
 |  - Resilience Score Calculation (0 - 100%)                              |
 |  - Visual HTML and structured JSON Scorecards                           |
 +-------------------------------------------------------------------------+
```

---

## 2. Injected Fault Taxonomies

Faults are injected dynamically according to active simulation clock triggers:

| Category | Fault Type | Physical Mechanism & Simulation Impact |
| :--- | :--- | :--- |
| **Optical / Environmental** | `LOW_LIGHT` | Exponential luminance attenuation simulating cabin power drop / eclipse. |
| | `GLARE` | Additive Gaussian saturation bloom simulating direct solar glare or reflections. |
| | `OCCLUSION` | Opaque spatial mask simulating an obstructed camera lens or physical obstacle. |
| | `LENS_SMUDGE` | Localized multi-scale Gaussian blurring simulating cabin dust or grease smudge. |
| | `NOISE_CORRUPTION` | High-variance zero-mean Gaussian noise simulating sensor EM interference. |
| | `MOTION_BLUR` | Directional linear convolution filter simulating spacecraft vibration or jitter. |
| | `BLACK_FRAME` | Complete zeroing of pixel arrays simulating sensor disconnect or blackout. |
| | `FRAME_DROP` | Intermittent frame omission (`CameraSource.read()` yields `None`). |
| | `FRAME_FREEZE` | Repeated buffer transmission simulating a hung camera hardware FIFO. |
| **Behavioral / Operator** | `WRONG_OBJECT` | Operator interacts with distractor specimen (e.g. `YELLOW_BOX` instead of `RED_BOX`). |
| | `WRONG_ORDER` | Procedure actions executed out of order (e.g. transfer before acquisition). |
| | `SKIPPED_STEP` | Mandatory intermediate procedure step omitted entirely. |
| | `INCOMPLETE_ACTION`| Physical action terminated before fulfilling stabilization/placement criteria. |
| **Perception & Telemetry**| `LATENCY_SPIKE` | Artificial compute delay simulating onboard thermal throttling or CPU contention. |
| | `BBOX_JITTER` | Stochastic bounding box perturbation testing tracker association resilience. |
| | `DETECTOR_DROPOUT`| Stochastic omission of detections simulating detector misfire. |
| **System & Viewpoint** | `VIEWPOINT_SWITCH`| Dynamic perspective re-orientation between `VIEW_LEFT` and `VIEW_RIGHT`. |
| | `STORAGE_FAILURE` | Simulated failure of local evidence storage filesystem. |

---

## 3. Resilience Scoring & Safety Principles

### 3.1 Zero False Deviation Policy under Optical Degradation

A fundamental tenet of spaceflight assurance is that **optical degradation must never produce false deviation alerts**. If lighting drops, glare blooms, or the lens is smudged:
- Detection confidence drops.
- The `TriStateAssuranceEngine` classifies the state as `UNCERTAIN`.
- Verification pauses safely until optical conditions recover.
- Any procedure `DEVIATION` triggered purely during optical faults incurs a severe penalty (-10% per instance).

### 3.2 Resilience Score Formula

Each simulation scenario is scored on a $[0, 100\%]$ scale:

$$\text{Resilience} = 100\% - \text{Penalties}$$

Where:
- **Unhandled Crash Penalty**: $-20\%$ per unhandled pipeline exception (capped at $-50\%$).
- **False Positive Deviation Penalty**: $-10\%$ per false deviation under optical stress (capped at $-30\%$).
- **Undetected Behavioral Deviation Penalty**: $-40\%$ if an expected behavioral deviation was missed.
- **False Deviation in Nominal Scenario Penalty**: $-30\%$ if deviation flagged during nominal run.

**Passing Criterion**:
$$\text{Verdict} = \text{PASS} \iff \text{Resilience} \ge 75.0\% \quad \text{AND} \quad \text{Unhandled Crashes} = 0$$

### 3.3 Mean Time To Detect (MTTD)

For behavioral faults (`WRONG_OBJECT`, `WRONG_ORDER`, `SKIPPED_STEP`):

$$\text{MTTD} = t_{\text{first\_deviation}} - t_{\text{fault\_trigger\_start}}$$

The system guarantees sub-second MTTD across all standard behavioral test scenarios.
