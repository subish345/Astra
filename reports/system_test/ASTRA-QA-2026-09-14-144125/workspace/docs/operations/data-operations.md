# ASTRA-EA — Mission Data Operations & Retention

## Phase 19: Mission Operations & Ground Segment Integration (D19.10)
**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Partitioned Storage Architecture (Section 25, 26)

ASTRA-EA enforces strict segregation of mission data from diagnostic and training artifacts:

```text
flight_data/
├── mission/          # Active state, event sequences, and completion summaries
├── evidence/         # Cryptographically signed decision frames and clips
├── telemetry/        # Periodic platform metric logs (CPU, memory, FPS)
├── reports/          # Post-mission audit reports (JSON & HTML)
└── diagnostics/      # Rotating Bounded Logs (flight.log, maintenance_state.json)
```

**Rule:** The Dataset Studio, synthetic image synthesizers, and training scripts **never write** to or read from `flight_data/`.

---

## 2. Retention Hierarchy & Storage Pruning Policy (Section 27, 28)

Under storage capacity pressure, data is pruned strictly according to Section 28 priority:

```text
PRIORITY RANKING:
1. MISSION EVENTS      (Permanent, Never Pruned)
2. ASSURANCE EVENTS    (Permanent, Never Pruned)
3. EVIDENCE CLIPS      (Permanent, Never Pruned)
4. MISSION VIDEO       (Pruned only if non-critical segments)
5. DIAGNOSTIC LOGS     (Rotated & Truncated at 10 MB bound)
6. DEBUG LOGS          (Purged first on warning threshold)
```

- When storage reaches **85% utilization**, the system enters `STORAGE_WARNING` and purges Level 6 (debug) and Level 5 (old diagnostics).
- Mission-critical decision events and cryptographic evidence snapshots are **never deleted**.

---

## 3. Mission Data Export CLI (Section 28, 29)

To export a completed mission run for ground science distribution:

```bash
astra mission export --run RUN_0001 --output-dir exports/
```

### Export Bundle Contents:
```text
RUN_0001/
├── report.json             # Structured audit report
├── report.html             # Self-contained standalone visual report
├── events.json             # Complete sequence of emitted telemetry events
├── evidence/               # Snapshots and clips referenced by run events
├── timeline.json           # Time-indexed MET and GRT milestones
├── health.json             # Final platform health snapshot
├── configuration/          # Exact system and experiment YAML used
├── manifest.json           # Cryptographic export manifest
└── checksums.sha256        # SHA-256 signatures for every file in the bundle
```

### Export Immutability Rule (Section 29)
Export operations are **read-only** copies. The source records in `flight_data/` remain untouched and un-mutated.
