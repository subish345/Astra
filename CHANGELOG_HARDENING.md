# ASTRA-EA Hardening Changelog (Phase 21, Section 35)

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## [1.0.0-RC2] — 2026-09-13 (Phase 21 Findings-Driven Hardening)

### Summary of Release Candidate 2
Release Candidate 2 (`ASTRA-EA-v1.0.0-RC2`) resolves all 6 empirical findings surfaced during Phase 20 operational rehearsals without rewriting working subsystems or altering validated procedure semantics.

---

### Findings Dispositions & Technical Changes

#### FINDING-001 / CAPA-001 (Camera Driver Tuple Unpacking)
* **Finding ID**: `FINDING-001`
* **Severity**: HIGH
* **Category**: CAMERA
* **Change**: Refactored `PreMissionRunner._check_camera()` and diagnostic inspection routines to safely unpack `(frame, timestamp)` tuple before querying `.shape` or buffer dimensions.
* **Tests**: `tests/regression/test_camera_tuple_unpacking.py` (2 tests, PASS)
* **Impact**: Eliminates `AttributeError` when sensor times out or frame drop occurs; allows clean degradation to `PAUSED`.

#### FINDING-002 / CAPA-002 (Ground Reconnect Deduplication)
* **Finding ID**: `FINDING-002`
* **Severity**: MEDIUM
* **Category**: GROUND / NETWORK
* **Change**: Added duplicate rejection filter in `GroundReconciler.reconcile_buffered_events()` ensuring already received sequence IDs in local store are discarded during burst replay.
* **Tests**: `tests/regression/test_ground_reconnect_dedup.py` (PASS, 0 duplicates)
* **Impact**: Guarantees strictly monotonic event timeline without repeating sequence numbers in ground observability reports.

#### FINDING-003 / CAPA-003 (Storage Threshold Pruning Trigger)
* **Finding ID**: `FINDING-003`
* **Severity**: MEDIUM
* **Category**: STORAGE
* **Change**: Added automated 85% capacity threshold hook in `StorageRetentionPolicy` to purge non-critical preview and debug logs while strictly protecting verified step evidence.
* **Tests**: `tests/regression/test_storage_pruning_policy.py` (PASS)
* **Impact**: Reclaims transient partition space during multi-hour experiments without risk of evidence loss.

#### FINDING-004 / CAPA-004 (Alert Acknowledge Button Ergonomics)
* **Finding ID**: `FINDING-004`
* **Severity**: OBSERVATION
* **Category**: UI / OPERATOR
* **Change**: Updated `AlertPanel.ack_btn` styling with vibrant high-contrast blue (`#3b82f6`), clear visual hover transition, and bold text.
* **Tests**: `tests/regression/test_ui_alert_contrast.py` (PASS)
* **Impact**: Reduces operator visual search latency during anomaly acknowledgment to &lt;1.0s.

#### FINDING-005 / CAPA-005 (Clock Display Formatting Stability)
* **Finding ID**: `FINDING-005`
* **Severity**: LOW
* **Category**: PERFORMANCE / UI
* **Change**: Standardized `HeaderPanel.set_clocks()` to format display string as `HH:MM:SS` mission elapsed time, preventing millisecond geometry recalculations during accelerated sweeps.
* **Tests**: `tests/regression/test_clock_stability.py` (PASS)
* **Impact**: Eliminates visual redraw jitter on telemetry banner during high-rate synthetic clocks.

#### FINDING-006 / CAPA-006 (Recovery Verification Latency Bound)
* **Finding ID**: `FINDING-006`
* **Severity**: HIGH
* **Category**: RECOVERY / ASSURANCE
* **Change**: Enforced strict recovery verification latency bound (&lt;300ms SLA) in recovery matcher upon detecting target apparatus.
* **Tests**: `tests/regression/test_recovery_verification_latency.py` (PASS)
* **Impact**: Guarantees astronaut prompt feedback and procedure resumption upon placing the correct apparatus into the workstation.

---

### Verification & Test Summary
* **Dedicated Regression Tests**: 7 / 7 passing in `tests/regression/`
* **Operational Rehearsal Matrix**: 13 / 13 passing (`astra rehearsal --scenario ALL`)
* **Full Repository Test Suite**: 326 / 326 passing (32.2s execution time)
* **Readiness Status**: **`READY`**
