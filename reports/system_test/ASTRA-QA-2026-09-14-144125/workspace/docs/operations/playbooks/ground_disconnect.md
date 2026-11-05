# Anomaly Playbook: Ground Segment Disconnect & State Reconciliation

**Anomaly Code:** `ANOM_GND_007`  
**Classification:** `GROUND`  
**Severity:** `NOTICE`  
**Standard:** ECSS-E-ST-70C

---

## 1. Symptoms & Detection
- Ground Observability Monitor client crashes or is closed and reopened by ground operator.
- Re-established connection receives a modern event sequence number (e.g. `112`) that jumps past the last seen sequence (e.g. `104`).
- Header banner indicates `SYNC: GAP (7)`.

## 2. Immediate Safe Autonomous Response (Section 42, 43, 44)
1. Ground reconciler identifies missed sequence interval `[105, 111]`.
2. Reconciler requests missed batch from onboard telemetry cache.
3. Ingests missed events, appends them to local timeline in strictly sorted sequence, and verifies zero duplicates.
4. Header status restores to `SYNC: OK`.

## 3. Operator Actions
1. Confirm Ground Monitor reconnects to SSE endpoint `http://<payload_ip>:8765/events`.
2. Inspect `SYNC` badge on the top right:
   - If `SYNC: OK`, timeline is fully harmonized.
   - If `SYNC: GAP (N)`, wait 2-3 seconds for automated reconciliation pass.
3. Review any deviations or verified steps that occurred during the disconnect window.

## 4. Evidence to Capture
- Ground sequence reconciliation report with count of recovered events and discarded duplicates.
