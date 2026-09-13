# Anomaly Playbook: Optical Camera Failure

**Anomaly Code:** `ANOM_CAM_001`  
**Classification:** `CAMERA`  
**Severity:** `CRITICAL`  
**Standard:** ECSS-E-ST-70C

---

## 1. Symptoms & Detection
- Optical camera driver fails to deliver a new frame within timeout horizon (>2.0 seconds).
- Drop counter increments rapidly (`consecutive_drops >= 5`).
- System health monitor logs `CAMERA: FAILED`.

## 2. Immediate Safe Autonomous Response (Section 15)
1. Driver transitions to `CAMERA_FAILED`.
2. Perception transitions to `PERCEPTION_DEGRADED`.
3. Experiment progression is paused (`PROCEDURE_VERIFICATION_PAUSED`).
4. **Absolute Rule:** Stale or frozen frames are **never** evaluated to verify procedure steps.

## 3. Operator Actions
1. **Acknowledge Alert:** Tap `ACKNOWLEDGE` on the Mission Console HUD.
2. **Physical Check:** Verify physical USB/CSI camera cable connection and camera power LED.
3. **Software Recovery:**
   - Attempt camera restart via Console Settings -> *Re-initialize Camera*.
   - Or enter maintenance mode to run loopback:
     ```bash
     astra maintenance test-camera
     ```
4. **Escalation:** If unresolved after 60 seconds, escalate to Level 2 (System Engineer).

## 4. Evidence to Capture
- Last 3 frames captured before failure.
- `flight_data/diagnostics/flight.log` kernel V4L2 entries.
