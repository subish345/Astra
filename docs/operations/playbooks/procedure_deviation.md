# Anomaly Playbook: Procedural Protocol Deviation

**Anomaly Code:** `ANOM_PRC_006`  
**Classification:** `PROCEDURAL`  
**Severity:** `WARNING`  
**Standard:** ECSS-E-ST-70C

---

## 1. Symptoms & Detection
- Operator interacts with incorrect physical apparatus (e.g. grasping pipette tip box instead of centrifuge tube).
- Step action executed out of sequence or skipped.
- Assurance engine triggers `DEVIATION_DETECTED`.

## 2. Immediate Safe Autonomous Response
1. Step state transitions to `ANOMALY`.
2. Audio guidance emits immediate corrective directive:
   - *"Warning: Incorrect apparatus. Return pipette box; retrieve centrifuge tube."*
3. Visual HUD displays red deviation card with recovery instructions.
4. Ground Monitor receives `DEVIATION_DETECTED` event with snapshot evidence link.

## 3. Operator Actions
1. **Pause Action:** Immediately halt physical motion.
2. **Acknowledge:** Press `ACKNOWLEDGE` on the HUD.
3. **Execute Recovery:** Follow exact recovery directive (replace wrong object, grasp expected apparatus).
4. **Observe Confirmation:** Assurance engine automatically evaluates recovery; once verified, the HUD turns green `[VERIFIED]` and the next step is presented.

## 4. Evidence to Capture
- Pre-deviation snapshot, deviation snapshot, and recovery verification frame.
- Object detector bounding boxes and class confidence scores.
