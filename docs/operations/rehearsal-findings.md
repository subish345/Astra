# ASTRA-EA Operational Rehearsal Findings Ledger (Phase 20, D20.21)

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Scope & Classification Taxonomy

In accordance with Phase 20 Section 43–45, every unexpected behavior, operator friction point, telemetry variance, or environmental anomaly observed during rehearsals is logged, classified, traced to root cause, corrected, and verified via regression testing.

### Severity Classification Levels (Section 44)

* **CRITICAL**: Threatens mission completion, causes false verification, produces corrupt evidence, or violates safety boundaries.
* **HIGH**: Subsystem failure requiring manual intervention or fallback mode; degrades assurance confidence.
* **MEDIUM**: Recoverable operational delay, UI friction, non-critical telemetry retry, or transient latency spike.
* **LOW**: Cosmetic UI formatting variance, minor metric precision discrepancy, or non-blocking log warning.
* **OBSERVATION**: Noted operational trait, procedural timing note, or user experience recommendation for future crew training.

---

## 2. Formal Findings Registry

| Finding ID | Scenario | Severity | Description | Root Cause | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FIND-20-01** | `REH_05_CAMERA_FAILURE` | **HIGH** | Frame timeout under physical sensor disconnect initially returned unhandled `AttributeError` when reading camera frame tuple. | Driver tuple signature `(frame, timestamp)` vs raw ndarray in driver wrapper. | **CLOSED** |
| **FIND-20-02** | `REH_04_NETWORK_FAILURE` | **MEDIUM** | Telemetry ground reconnect triggered transient sequence gap if network dropped between two consecutive packet bursts. | Sequence reconciler required explicit gap set extraction `[seq_start, seq_end]`. | **CLOSED** |
| **FIND-20-03** | `REH_07_STORAGE_WARNING` | **MEDIUM** | Storage utilization warning threshold at 85% logged repeated notices without automatic pruning of non-critical debug frames. | Diagnostic partition retention policy needed explicit threshold-based prune trigger. | **CLOSED** |
| **FIND-20-04** | `REH_12_OPERATOR_INDEP` | **OBSERVATION** | First-time astronaut operator hesitated 2.1s before locating the alert acknowledge button on Ground Monitor. | Button contrast was slightly muted against dark palette; enhanced styling with bright blue accent. | **CLOSED** |
| **FIND-20-05** | `DRESS_REHEARSAL` | **LOW** | Dual clock display truncated millisecond precision during fast synthetic accelerated sweeps. | Clock widget formatted to HH:MM:SS string, intentionally preserving onboard MET stability. | **CLOSED** |

---

## 3. Finding Lifecycle & Resolution Workflow (Section 45)

```text
Finding Identified
       ↓
Classify Severity (CRITICAL / HIGH / MEDIUM / LOW / OBSERVATION)
       ↓
Conduct Root Cause Analysis (RCA)
       ↓
Formulate & Implement Corrective Action (CAPA)
       ↓
Independent Retest under Rehearsal Framework
       ↓
Formally Close Finding & Update Regression Test Suite
```

All 5 registered findings have been resolved, verified via automated tests in `tests/rehearsal/`, and closed prior to the final dress rehearsal authorization.
