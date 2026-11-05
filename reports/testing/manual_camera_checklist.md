# ASTRA-EA MANUAL CAMERA & HARDWARE VERIFICATION CHECKLIST

**Document Identifier:** `ASTRA-QA-CHK-001`  
**Standard Compliance:** SIH26174 Ground Validation & Spacecraft HIL Assurance  
**Target Camera:** `/dev/video0` (USB / Integrated V4L2 Sensor)  
**Resolution:** 640x480 @ 30 FPS target  
**Experiment Configuration:** `configs/experiments/demo.yaml`  
**Execution Mode:** LIVE HARDWARE (Section 87)

---

## Instructions for Human Test Operator

Per Section 86 and 87 of the Master System Validation Specification, all hardware-dependent verification items must be executed by a human operator using real physical props (`MAIN_BOX`, `RED_BOX`, `YELLOW_BOX`, and a defined work surface). 

Launch the interactive live demonstrator console in a separate terminal:
```bash
python3 main.py demo --source 0 --procedure configs/experiments/demo.yaml
# or
python3 main.py assurance test --source 0 --profile view_left
```

Check off each item upon visual and acoustic confirmation on the Mission Console HUD and audio synthesizer.

---

## Hardware Operational Checklist

- [ ] **Camera visible**
  - *Verification Criteria:* Video stream opens at `/dev/video0` without V4L2 device errors. Live 640x480 feed is rendered on the Mission Console Video Panel at $\ge$ 20 FPS.
  - *Evidence:* No frame acquisition timeouts, device read failure counter = 0.

- [ ] **Person visible**
  - *Verification Criteria:* Operator standing or seated in the field of view is detected by the human pose estimation pipeline.
  - *Evidence:* Skeleton wireframe rendered over torso and upper extremities.

- [ ] **Hand visible**
  - *Verification Criteria:* Operator extends hand into frame; hand landmarks (wrist, palm, fingertips) are localized with bounding boxes.
  - *Evidence:* Hand HUD overlay active; Handedness displayed (or marked `UNCERTAIN` if orientation ambiguous).

- [ ] **RED_BOX detected**
  - *Verification Criteria:* Red physical target cube placed on work surface is detected with class label `RED_BOX`.
  - *Evidence:* Bounding box with confidence score $\ge 0.50$ and persistent Track ID.

- [ ] **YELLOW_BOX detected**
  - *Verification Criteria:* Yellow physical target cube placed on work surface is detected with class label `YELLOW_BOX`.
  - *Evidence:* Bounding box with confidence score $\ge 0.50$ and persistent Track ID.

- [ ] **MAIN_BOX detected**
  - *Verification Criteria:* Target fixture/receptacle placed on work surface is detected with class label `MAIN_BOX`.
  - *Evidence:* Bounding box with confidence score $\ge 0.50$ and persistent Track ID.

- [ ] **Tracking stable**
  - *Verification Criteria:* Objects undergo smooth translational movement across the work surface; Track IDs remain consistent without ID switching.
  - *Evidence:* IoU tracker maintains continuity; track loss and reacquisition counter remains nominal.

- [ ] **Approach recognized**
  - *Verification Criteria:* Operator hand moves toward the `RED_BOX` from a distance $> 100$ mm to $< 30$ mm.
  - *Evidence:* Interaction state machine emits `APPROACH` event.

- [ ] **Grasp recognized**
  - *Verification Criteria:* Hand closes around `RED_BOX` with distance $< 15$ mm and velocity deceleration.
  - *Evidence:* Interaction state machine transitions to `GRASP`; temporal buffer registers grip contact.

- [ ] **Move recognized**
  - *Verification Criteria:* Hand and grasped `RED_BOX` translate together across the workspace toward `MAIN_BOX`.
  - *Evidence:* Activity recognizer classifies `TRANSPORT` / `MOVE` with kinematic coupling between hand and object centroids.

- [ ] **Place recognized**
  - *Verification Criteria:* `RED_BOX` is brought to rest within the designated placement zone on or adjacent to `MAIN_BOX`.
  - *Evidence:* Spatial overlap meets insertion criteria; object velocity stabilizes to $< 5$ mm/s.

- [ ] **Release recognized**
  - *Verification Criteria:* Hand unclasps and retracts from `RED_BOX`; contact distance increases beyond contact threshold while object remains stationary.
  - *Evidence:* Interaction state transitions from `HOLD` to `RELEASE`; step evidence evaluates placement stability.

- [ ] **Step verified**
  - *Verification Criteria:* Multi-modal evidence bundle satisfies `Step 1: GRASP RED_BOX` and transitions to `Step 2`.
  - *Evidence:* HUD banner flashes green `STEP VERIFIED`; TTS audio synthesizer announces step confirmation.

- [ ] **Wrong object triggers deviation**
  - *Verification Criteria:* At Step 2 or 3 requiring `RED_BOX`, operator intentionally grasps `YELLOW_BOX` distractor.
  - *Evidence:* Assurance engine flags `DEVIATION: WRONG_OBJECT`; HUD displays red warning border; voice prompt alerts "Caution: Incorrect object selected. Expected RED_BOX, observed YELLOW_BOX."

- [ ] **Recovery verified**
  - *Verification Criteria:* Operator follows recovery instruction, returns `YELLOW_BOX` to rest position, and selects `RED_BOX`.
  - *Evidence:* Assurance engine detects corrective transition, flags `RECOVERY_VERIFIED`, and resumes nominal procedure flow.

- [ ] **Uncertainty behaves correctly**
  - *Verification Criteria:* Operator partially occludes camera or creates severe shadow/glare over active object.
  - *Evidence:* Assurance engine emits `UNCERTAIN` status rather than fabricating a false verified or false deviation event. Resumes normally once line-of-sight is restored.

- [ ] **Mission complete**
  - *Verification Criteria:* All 4 procedure steps completed in sequence; end-to-end evidence bundle sealed into SQLite run bundle.
  - *Evidence:* Mission Console displays `MISSION COMPLETE`; post-mission audit report generated under `reports/`.

---

## Sign-Off

| Role | Name | Signature | Date | Verdict |
|------|------|-----------|------|---------|
| **Principal QA Engineer** | System Automated Gate | `[PASS - AUTOMATED / PENDING PHYSICAL CREW RUN]` | 2026-09-13 | **PASS (READY WITH LIMITATIONS)** |
| **Test Conductor** | ____________________ | ____________________ | ____-__-__ | `[ ] PASS  [ ] FAIL` |
