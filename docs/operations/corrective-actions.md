# ASTRA-EA Rehearsal Corrective Actions Log (Phase 20, D20.22)

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Overview & Traceability

This document records the Corrective and Preventive Actions (CAPA) executed in response to operational findings registered during Phase 20 rehearsals, ensuring complete traceability and prevention of recurring anomalies.

---

## 2. Corrective Action Records

### CAPA-20-01 (Addressing FIND-20-01)
* **Associated Finding**: `FIND-20-01` (Camera Frame Tuple Unpacking)
* **Severity**: HIGH
* **Root Cause**: `CameraDriver.read_frame()` returns `Optional[Tuple[np.ndarray, FrameTimestamp]]`. Callers assuming a bare NumPy array threw `'tuple' object has no attribute 'shape'` during sensor drop handling.
* **Action Taken**: Refactored `PreMissionRunner` and `MaintenanceModeManager` to safely unpack `read_res` into `(frame, ts)` before querying array dimensions.
* **Verification**: `tests/operations/test_precheck.py` and `tests/rehearsal/test_rehearsal_scenarios.py` execute 100% cleanly without type errors.
* **Disposition**: **CLOSED & VERIFIED**

---

### CAPA-20-02 (Addressing FIND-20-02)
* **Associated Finding**: `FIND-20-02` (Ground Reconnect Sequence Gap Replay)
* **Severity**: MEDIUM
* **Root Cause**: When ground link dropped during multi-event transmission, the ground reconciler did not filter out sequence numbers already present in the local database.
* **Action Taken**: Implemented duplicate suppression filter `set(buffered_events) - set(received_events)` in `core/operations/reconciliation.py`.
* **Verification**: `REH_04_NETWORK_FAILURE` test passes with `duplicate_count == 0`.
* **Disposition**: **CLOSED & VERIFIED**

---

### CAPA-20-03 (Addressing FIND-20-03)
* **Associated Finding**: `FIND-20-03` (Storage Diagnostic Pruning)
* **Severity**: MEDIUM
* **Root Cause**: Automated storage warning triggered without triggering non-critical frame pruning.
* **Action Taken**: Added prune hook to `StorageRetentionPolicy` triggered when utilization exceeds 85%, retaining all verified step evidence frames while purging transient preview buffers.
* **Verification**: Storage warning drill passes without dropping critical audit frames.
* **Disposition**: **CLOSED & VERIFIED**

---

### CAPA-20-04 (Addressing FIND-20-04)
* **Associated Finding**: `FIND-20-04` (Alert Acknowledge Button Ergonomics)
* **Severity**: OBSERVATION
* **Root Cause**: Button styling in `AlertPanel` blended slightly with the panel background.
* **Action Taken**: Restyled `btn_ack` with `#0284c7` border, high-contrast cyan font, and clear visual hover transition.
* **Verification**: Independent operator successfully located and acknowledged alert in &lt;1.2s.
* **Disposition**: **CLOSED & VERIFIED**

---

### CAPA-20-05 (Addressing FIND-20-05)
* **Associated Finding**: `FIND-20-05` (Clock Formatting Stability)
* **Severity**: LOW
* **Root Cause**: Synthetic acceleration caused millisecond jitter on the telemetry header clock.
* **Action Taken**: Standardized display string to `HH:MM:SS` mission elapsed time, retaining fractional seconds in the machine-readable telemetry stream.
* **Verification**: Ground Monitor UI tested under accelerated rehearsal without layout shifts.
* **Disposition**: **CLOSED & VERIFIED**
