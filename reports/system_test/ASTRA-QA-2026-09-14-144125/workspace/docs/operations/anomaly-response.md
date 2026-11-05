# ASTRA-EA — Operational Anomaly Response & Classification

## Phase 19: Mission Operations & Ground Segment Integration (D19.08)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Generic Anomaly Response Workflow (Section 18)

Every operational abnormality detected by ASTRA-EA follows an unambiguous 8-step containment workflow:

```text
1. ANOMALY DETECTED (Visual / Sensor / State Engine)
          ↓
2. CLASSIFY (Procedural, Perception, Hardware, Storage, Network)
          ↓
3. ASSESS (Severity: INFO, NOTICE, WARNING, CRITICAL)
          ↓
4. ACKNOWLEDGE (Operator taps ACKNOWLEDGE on HUD)
          ↓
5. RECOVER / WAIT / ESCALATE (Follow specific Playbook)
          ↓
6. VERIFY (Assurance engine re-evaluates physical apparatus pose)
          ↓
7. RESOLVE (Alert marked RESOLVED; Nominal execution resumed)
          ↓
8. CLOSE & RECORD (Event permanently sealed in audit evidence log)
```

---

## 2. Anomaly Classification Taxonomy (Section 19)

| Anomaly Class | Root Cause Description | Example Scenario |
| :--- | :--- | :--- |
| **`PROCEDURAL`** | Deviation from nominal experiment protocol. | Wrong apparatus selected; step skipped; incorrect order. |
| **`PERCEPTION`** | High uncertainty or occlusion in optical stream. | Hand fully occluding fiducial; low contrast illumination. |
| **`CAMERA`** | Optical sensor driver failure or frame drop. | V4L2 device descriptor lost; frame timeout > 2.0s. |
| **`MODEL`** | Neural network runtime execution error. | ONNX runtime inference exception or tensor shape fault. |
| **`STORAGE`** | Disk partition capacity constraint or I/O error. | Diagnostic partition exceeds 85%; non-volatile write error. |
| **`COMPUTE`** | CPU silicon thermal throttling or memory exhaustion. | Junction temp >= 100°C; RSS memory exceeding margin. |
| **`NETWORK`** | Telemetry ground socket closed unexpectedly. | Ground link severed; Wi-Fi / Spacecraft bus timeout. |
| **`VOICE`** | Audio TTS daemon playback failure. | ALSA / PulseAudio device busy; speaker muted. |
| **`GROUND`** | Ground Monitor disconnect or sequence desynchronization. | Browser / Qt monitor restart; missed telemetry packets. |
| **`CONFIGURATION`**| Hash mismatch or corrupted procedure YAML. | Tampered procedure file; invalid schema format. |
| **`UNKNOWN`** | Uncategorized edge exception. | Unexpected kernel signal; unhandled Python exception. |

---

## 3. Operational Handling Rules (Section 20)

### The Unambiguous Operator Rule
> **An operator must never have to guess: "Is this a warning or a failure?"**
> 
> The Mission Console and Ground Monitor explicitly display:
> 1. **Anomaly Type:** (e.g. `PROCEDURAL: WRONG_APPARATUS`)
> 2. **Severity Tier:** (`CRITICAL` [Red], `WARNING` [Amber], `NOTICE` [Blue], `INFO` [Cyan])
> 3. **Current State:** (`RECEIVED` -> `ACKNOWLEDGED` -> `RESOLVED`)
> 4. **Expected Action:** Clear, non-technical instructions (e.g. *"Return pipette tip box to rack; grasp centrifuge tube"*).

---

## 4. Alert Lifecycle & Acknowledgement Policy (Section 17, 56)

```text
[ANOMALY TRIGGERED] ──► State: RECEIVED (Red Alert Card)
                             │
                             ▼ Operator presses "ACKNOWLEDGE"
                        State: ACKNOWLEDGED (Amber Alert Card)
                             │
                             ▼ Corrective physical action confirmed by AI
                        State: RESOLVED (Green Nominal Card)
```

- **Rule:** `ACKNOWLEDGED` does **NOT** mean `RESOLVED`.
- An acknowledged alert remains visibly tracked on the Ground Monitor until the physical recovery action is positively verified by the assurance engine.
