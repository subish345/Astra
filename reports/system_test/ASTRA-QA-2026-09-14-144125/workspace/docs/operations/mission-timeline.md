# ASTRA-EA — Mission Timeline & Timing Architecture

## Phase 19: Mission Operations & Ground Segment Integration (D19.02)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Timing References & Timekeeping (Section 12, 13)

Operational spacecraft experiments require deterministic, synchronized timekeeping. ASTRA-EA defines two authoritative timing planes:

1. **Onboard Mission Elapsed Time (MET):**
   - Authoritative reference monotonic clock started at mission T-0 (`T_START`).
   - Units: Seconds with millisecond resolution (`00:00:00.000`).
   - Immutable across system restarts or network drops.
   - All step recognitions, deviation alerts, and evidence cryptographic hashes are stamped with onboard MET.

2. **Ground Receipt Time (GRT):**
   - UTC timestamp recorded when a telemetry frame or SSE event is ingested by the Ground Observability Console.
   - Displayed alongside MET on the Ground Monitor banner:
     ```text
     MET: 00:14:22 | GRT: 14:48:31 UTC
     ```
   - Standard Rule: **Ground Receipt Time is never substituted for Mission Elapsed Time in assurance decisions or audit logs.**

---

## 2. Standard Mission Event Sequence

```text
T-300s : PREPARATION
         - Power applied to payload compute
         - Operator runs: astra mission precheck
         - Signed checklist: PRE_MISSION

T-060s : INITIALIZATION
         - Optical camera driver initialized
         - Model weights SHA-256 validated
         - Storage partitions verified (<95% utilized)
         - Clock starts monotonic ticking

T-000s : EXPERIMENT START (T-START)
         - Operator issues START_EXPERIMENT
         - Run ID assigned (e.g. RUN_0001)
         - Event EVT_0001 (EXPERIMENT_STARTED) published to telemetry bus

T+010s : STEP 1 — WORKSTATION APPROACH
         - Operator moves into camera field of view
         - Activity: APPROACH_WORKSTATION recognized
         - Decision: STEP_VERIFIED -> Transition to STEP 2

T+045s : STEP 2 — APPARATUS SELECTION & DEVIATION
         - Operator reaches for wrong object (Pipette Tip Box instead of Centrifuge Tube)
         - Assurance Decision: DEVIATION (Confidence: 0.94)
         - Audio directive: "Warning: Incorrect apparatus. Retrieve centrifuge tube."
         - Ground Monitor displays: CRITICAL / WARNING Alert Card

T+055s : RECOVERY ACTION
         - Operator acknowledges directive and returns pipette box to rack
         - Correct centrifuge tube retrieved and placed into active zone
         - Decision: RECOVERY_VERIFIED -> Transition to STEP 3

T+120s : STEP 3 — VORTEXING
         - Centrifuge vortexing completed and verified

T+180s : STEP 4 — SPECIMEN DEPOSITION
         - Fluid transfer into test tube verified
         - Decision: STEP_VERIFIED

T+195s : COMPLETION (T-END)
         - Final step confirmed nominal
         - Video buffer flushed to disk
         - Event EVT_XXXX (EXPERIMENT_COMPLETED) emitted

T+210s : POST-MISSION
         - Operator executes: astra mission export --run RUN_0001
         - Cryptographic bundle compiled with checksums.sha256
         - Ground science team downloads export package
```

---

## 3. Sequence Numbering & Gap Detection (Section 44)

Every event published by ASTRA-EA carries a strictly monotonic integer `sequence_num` (e.g. 1, 2, 3, ...).

If ground connection drops at sequence `102` and reconnects receiving sequence `108`, Ground Monitor automatically detects the sequence gap `[103, 107]`, marks `SYNC: GAP (5)`, requests the buffered event range from onboard storage, and reconciles the timeline without duplicating records.
