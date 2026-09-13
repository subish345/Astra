# ASTRA-EA: Configuration Management & Change Control Plan

**Classification:** Aerospace Configuration Management & Data Assurance Plan  
**Document ID:** `ASTRA-CMP-001`  
**Standard:** ECSS-M-ST-40C / NASA Configuration Management Guidance  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Data Classification Hierarchy

Payload telemetry and operational data are partitioned into five discrete retention tiers:

| Data Tier | Examples | Storage Target | Retention Policy | Integrity Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **`MISSION_CRITICAL`** | Procedure step transitions, deviations, recovery events, system health status | Local SQLite WAL DB | **Permanent Retention** (Never overwritten) | Sequence number, UTC SCET, SHA-256 hash |
| **`MISSION_IMPORTANT`** | Compressed MP4 video stream, evidence snapshot images | NVMe SSD Video Partition | Circular FIFO (72-hour rolling buffer) | Frame index timestamp linkage |
| **`DIAGNOSTIC`** | P95 latency distributions, CPU/RAM telemetry, FPS measurements | `reports/` directory | 30-day rolling archive | JSON schema validation |
| **`DEBUG`** | Verbose optical bounding box tracks, raw MediaPipe landmark arrays | Memory buffer / temporary logs | Cleared at mission completion | Ring buffer (discarded on exit) |
| **`TRAINING`** | Curated edge-case frames for post-mission dataset expansion | `datasets/` partition | Preserved with full operator session metadata | Cryptographic dataset card hash |

---

## 2. Configuration Identification & Snapshotting

Every experiment execution creates an immutable, self-contained run archive under `data/runs/RUN_XXXX/` capturing the complete system state:
1. `config_snapshot.yaml`: Complete YAML configuration snapshot (camera parameters, thresholds, procedure rules).
2. `model_snapshot.json`: Exact model identifier, weights file path, input dimensions, and SHA-256 checksum.
3. `version_metadata.json`: Software version, active Git commit hash, Python version, OS kernel, and CPU architecture.
4. `run_metadata.json`: Mission start/end timestamps, duration, exit state, and operator identifier.

---

## 3. Aerospace Change Control Impact Tiers

After qualification baseline establishment, all proposed engineering modifications must be classified into one of five impact tiers:

```
[TIER 1: COSMETIC] ──> [TIER 2: NON-FUNCTIONAL] ──> [TIER 3: FUNCTIONAL] ──> [TIER 4: ASSURANCE-IMPACTING] ──> [TIER 5: INTERFACE-IMPACTING]
```

| Change Tier | Definition | Review & Verification Requirement | Regression Scope |
| :--- | :--- | :--- | :--- |
| **Tier 1: Cosmetic** | Documentation typos, UI color adjustments | Peer review only | Unit tests |
| **Tier 2: Non-Functional** | Code refactoring, test additions, comments | Systems engineer sign-off | Full unit + integration suite |
| **Tier 3: Functional** | Non-critical UI additions, diagnostic CLI flags | Technical review board | Full integration + HIL test |
| **Tier 4: Assurance-Impacting**| Changes to neural weights, IoU contact thresholds, or state machine transitions | Formal Qualification Authority Review | Complete 6-scenario simulation matrix + physical rig re-validation |
| **Tier 5: Interface-Impacting**| Changes to camera V4L2 protocols, telemetry schemas, or vehicle data bus ICD | Spacecraft Joint Interface Board | Full Hardware-in-the-Loop (HIL) qualification suite |
