# ASTRA-EA — Maintenance Operations & Safety Interlocks

## Phase 19: Mission Operations & Ground Segment Integration (D19.15)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Maintenance Mode Concept (Section 37, 38)

To support payload servicing, optical recalibration, and storage scrubbing without risking unintended live mission starts, ASTRA-EA defines a dedicated **`MAINTENANCE`** operational mode strictly segregated from **`MISSION`** mode.

```text
       ┌────────────────────────┐
       │ OPERATIONAL MISSION    │
       │ (Live Experimentation) │
       └───────────┬────────────┘
                   │
         Cannot enter while
         experiment is RUNNING
                   │
                   ▼
       ┌────────────────────────┐
       │    MAINTENANCE MODE    │
       │ (Diagnostics & Tuning) │
       └───────────┬────────────┘
                   │
         Live experiment starts
         are HARD BLOCKED
```

---

## 2. Maintenance Operations CLI Commands

### 1. Check Status
```bash
astra maintenance status
```
Output:
```text
============================================================
 ASTRA-EA SYSTEM OPERATIONAL MODE STATUS
============================================================
Active Mode:     MAINTENANCE MODE (or OPERATIONAL MISSION MODE)
Live Starts:     BLOCKED (or PERMITTED)
============================================================
```

### 2. Enter Maintenance Mode
```bash
astra maintenance enter --operator "SYSTEM_ENGINEER" --reason "Optical sensor alignment"
```

### 3. Run Camera Loopback Diagnostic
```bash
astra maintenance test-camera
```

### 4. Run Storage Scrub & Partition Diagnostic
```bash
astra maintenance test-storage
```

### 5. Exit Maintenance Mode
```bash
astra maintenance exit --operator "SYSTEM_ENGINEER"
```

---

## 3. Safety Interlocks (Section 38)

1. **Live Start Interlock:** If an operator attempts to execute `START_EXPERIMENT` while the system is in `MAINTENANCE MODE`, the startup sequence immediately aborts with:
   ```text
   START_EXPERIMENT REJECTED: System is currently locked in MAINTENANCE MODE.
   ```
2. **Experiment Running Interlock:** If an experiment is actively in progress (`RUNNING`), entering maintenance mode is rejected.
