# ASTRA-EA: Failure Mode and Effects Analysis (FMEA) & Fault Tree Analysis (FTA)

**Classification:** System Safety & Reliability Engineering Analysis  
**Document ID:** `ASTRA-FMEA-001`  
**Standard:** ECSS-Q-ST-30-02C (FMEA) / NASA-STD-8729.1  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Subsystem Failure Mode and Effects Analysis (FMEA)

| Subsystem | Failure Mode | Failure Effect on Mission | Detection Mechanism | Recovery & Mitigation Action | Residual Risk |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Optical Camera** | Sensor blackout / cable disconnect | Optical frames cease arriving | V4L2 timeout supervisor ($<100\text{ ms}$) | Transition to `VERIFICATION PAUSED`; alert crew | **LOW** |
| **Neural Detector**| CUDA OOM / inference thread crash | Vision perception stops | Watchdog process heartbeat ($<150\text{ ms}$) | Failover to `BaselineColorHeuristicDetector` | **LOW** |
| **Interaction Engine**| Miscalculated hand-object distance | Ambiguous contact state | Geometric boundary sanity checks | Epistemic gate asserts `UNCERTAIN` | **NEGLIGIBLE** |
| **Procedure Engine**| Corrupted procedure state transition | Procedure desynchronization | Finite-state graph validation | Reset to last validated milestone | **NEGLIGIBLE** |
| **Assurance Engine**| False step verification | Premature advancement on error | Multi-barrier evidence bundle required | Strict 5-barrier verification policy | **NEGLIGIBLE** |
| **Voice Audio DAC**| Audio driver crash (ALSA/Pulse) | Audible alerts cease | Audio process return-code inspection | Auto-switch to high-contrast visual HUD | **LOW** |
| **Storage (SSD)** | Filesystem write error / disk full | Loss of historical recording | SQLite write exception trap | Switch to circular memory buffer; prune debug | **LOW** |
| **Ground Streamer**| Network socket buffer exhaustion | Ground display freezes | WebSocket TCP transmit queue monitor | Drop auxiliary ground clients; onboard continues | **NEGLIGIBLE** |

---

## 2. Fault Tree Analysis (FTA): False Procedure Verification

The top-level catastrophic failure for an assurance co-pilot is **Falsely Declaring an Incorrect Step as Verified**:

```
                         [TOP EVENT: FALSE PROCEDURE VERIFICATION]
                                            |
                                         [AND GATE]
                     ┌──────────────────────┴──────────────────────┐
                     │                                             │
          [Corrupted Sensor Input]                       [Assurance Barrier Failure]
                     │                                             │
                 [OR GATE]                                     [AND GATE]
         ┌───────────┴───────────┐                     ┌───────────┴───────────┐
         │                       │                     │                       │
   [Object Class Swap]    [False Hand Contact]    [Bypassed Dwell]      [State Match Error]
```

### The 5 Defense Barriers Against False Verification
To achieve a verification state (`VERIFIED`), all 5 conditions must be simultaneously satisfied:
1. **Perception Barrier:** Object classification confidence $\ge 0.50$ (NMS filtered).
2. **Spatial Contact Barrier:** Hand-object intersection-over-union $IoU > 0.05$ or Euclidean proximity $<50\text{ mm}$.
3. **Temporal Persistence Barrier:** Contact maintained across $\ge 10$ consecutive frames ($>300\text{ ms}$).
4. **State Machine Barrier:** Active step prerequisites satisfied in procedure graph.
5. **Epistemic Safeguard:** Zero unresolved optical occlusions or lighting flags.

---

## 3. False Deviation Prevention
To prevent alerting astronauts on transient sensor noise:
$$\text{Single Frame Anomaly} \longrightarrow \text{Uncertainty Gate} \longrightarrow \text{10-Frame Dwell Window} \longrightarrow \text{Confirmed Contradiction} \longrightarrow \text{DEVIATION}$$
A single noisy frame **SHALL NEVER** trigger an audible deviation warning.
