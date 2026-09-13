# Anomaly Playbook: Ground Telemetry Link Loss

**Anomaly Code:** `ANOM_NET_004`  
**Classification:** `NETWORK`  
**Severity:** `WARNING`  
**Standard:** ECSS-E-ST-70C

---

## 1. Symptoms & Detection
- Ground telemetry streaming socket receives `ConnectionResetError` or EOF.
- SSE / WebSocket heartbeat exceeds 5.0 seconds without acknowledgement.
- Ground Monitor flags `LINK: OFFLINE`.

## 2. Immediate Safe Autonomous Response (Section 45, 46)
1. Onboard flight software marks ground link as degraded.
2. **Onboard autonomous experiment execution continues uninterrupted.**
3. Onboard event dispatcher diverts outgoing telemetry into local non-volatile ring buffer `flight_data/telemetry/`.

## 3. Operator Actions
1. **Astronaut Crew:** Continue experiment according to HUD visual guidance and audio cues; no immediate action required.
2. **Ground Controllers:** Investigate local ground network router / antenna link.
3. **Reconnection:** Upon link restoration, Ground Monitor automatically syncs missed sequence gaps.

## 4. Evidence to Capture
- Start and end timestamps of communication blackout.
- Total count of buffered telemetry events.
