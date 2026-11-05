# ASTRA-EA — Final Product Overview

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Product Version:** `1.0.0-RC1`  
**Classification:** Engineering-Grade Ground Demonstrator  
**Problem Statement:** AI Human Activity Recognition for On-board BAS Experiments

---

## 1. The Challenge

Astronauts aboard crewed space habitats (such as the International Space Station or future orbital stations) perform complex biological, chemical, and physical science experiments under high cognitive and physiological workloads. In microgravity:
* Minor procedural missteps (e.g., selecting the wrong reagent buffer, omitting a mandatory incubation step, or placing a specimen on an ungrounded work surface) can invalidate multi-million dollar science payloads.
* Constant ground-control voice supervision is constrained by orbital communication blackouts, orbital tracking delays, and bandwidth limits.
* Existing computer vision tools either rely on cloud connectivity, assume pristine laboratory camera angles, or report unexplainable neural network confidence scores without deterministic safety guarantees.

---

## 2. The ASTRA-EA Solution

**ASTRA-EA** is an edge-native, 100% offline spacecraft experiment assurance platform that:
1. **Observes** the astronaut and experimental apparatus through an onboard optical camera.
2. **Understands** anatomical hand-object proximity, grasps, releases, and spatial kinematics.
3. **Knows** what should happen by referencing an external, declarative YAML procedure definition.
4. **Decides** compliance via an explainable, deterministic Tri-State Assurance Engine (`VERIFIED`, `UNCERTAIN`, `DEVIATION`).
5. **Assists** the crew with local, low-latency text-to-speech audio guidance and visual HUD cues.
6. **Records** an immutable, timestamped local audit package (`SQLite`, `JSON`, `HTML`, `MP4`).

```text
THE CAMERA SEES.
      ↓
THE AI UNDERSTANDS.
      ↓
THE PROCEDURE ENGINE KNOWS WHAT SHOULD HAPPEN.
      ↓
THE ASSURANCE ENGINE DECIDES WHETHER IT DID.
      ↓
THE ASSISTANT HELPS RECOVER.
      ↓
THE EVIDENCE RECORD EXPLAINS WHY.
```

---

## 3. Core Product Differentiators

* **100% Offline Air-Gapped Autonomy**: Operates entirely on spacecraft edge compute. Zero external cloud API calls, zero telemetry dependencies.
* **Deterministic Assurance vs AI Hallucination**: AI is strictly relegated to perception and observation. Safety decisions are made by deterministic state machines. Raw neural network confidence never becomes mission ground truth.
* **Tri-State Safety Model**: Visual ambiguities (e.g., hand occlusion or lighting shifts) produce `UNCERTAIN` rather than false deviations, preventing unwarranted crew distraction.
* **Closed-Loop Astronaut Guidance**: Deviations immediately trigger actionable voice instructions (`EXPLAIN` $\to$ `RECOMMEND`), and the system actively verifies corrective actions before resuming the procedure.
* **Decoupled Ground Observability**: An independent Ground Monitor streams lightweight IP video and telemetry without blocking or degrading onboard assurance cycle rates.
