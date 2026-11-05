# ASTRA-EA — Final System Architecture

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Product Version:** `1.0.0-RC1`

---

## 1. End-to-End Pipeline Data Flow

The operational core of ASTRA-EA follows a strict, unidirectional data-flow pipeline:

```text
               Optical Camera (/dev/video0 / RTSP / Synthetic Source)
                                        │
                                        ▼
                                 Video Ingestion
                        (Threaded LatestFrameQueue Buffer)
                                        │
                                        ▼
                             Perception Pipeline
                 ┌──────────────────────┼──────────────────────┐
                 │                      │                      │
        Object Detector           Pose Estimator         Hand Detector
       (ONNX / ColorSpatial)   (Upper-Body Keypoints)  (Dual-Space Keypoints)
                 │                      │                      │
                 └──────────────────────┼──────────────────────┘
                                        │
                                        ▼
                               MultiObjectTracker
                        (ByteTrack IoU State Filter)
                                        │
                                        ▼
                            Spatial Interaction Engine
                     (Hand-Object Proximity & Contact Logic)
                                        │
                                        ▼
                            Temporal Activity Engine
                    (Rolling Window Kinematic Action Models)
                                        │
                                        ▼
                           Multimodal Evidence Engine
                     (Explainable Multi-Condition Bundles)
                                        │
                                        ▼
                            Procedure Progress Engine
                     (Graph-Based Step Topology & Matching)
                                        │
                                        ▼
                           Tri-State Assurance Engine
                      (VERIFIED / UNCERTAIN / DEVIATION)
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
             Closed-Loop Recovery Engine       Mission Console
             (Vocal & Visual Assistance)       (PySide6 UI HUD)
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                            Unified Mission Run Store
                         ┌──────────────┼──────────────┐
                         ▼              ▼              ▼
                     SQLite WAL       Video         Evidence
                      Database       Recorder        Store
                                        │
                                        ▼
                           Isolated IP Stream Server
                            (MJPEG :8554, SSE :8765)
                                        │
                                        ▼
                           Independent Ground Monitor
                            (Remote Operator Console)
```

---

## 2. Supporting Subsystems

ASTRA-EA integrates six critical supporting subsystems:

1. **Dataset Studio (`core/dataset/`)**:
   - Synthetic microgravity data generator with reproducible random seeds.
   - Live camera recording session tool.
   - Strict annotation validator, split leakage auditor, and version manager.
2. **Model Registry (`core/models/`)**:
   - Model lifecycle tracking (`CANDIDATE` $\to$ `VALIDATED` $\to$ `DEPRECATED`).
   - Hardware-abstracted inference backends (CPU SIMD, NVIDIA CUDA, ONNX Runtime).
   - Baseline vs learned detector comparative analysis suite.
3. **Simulation & Fault Injection Lab (`core/simulation/`)**:
   - End-to-end hardware-in-the-loop simulation engine.
   - 16 parametric fault operators (wrong object, skipped step, optical stress, sensor dropouts).
   - Automated permutation matrix runner with HTML resilience scorecards.
4. **Unified Health Aggregator (`core/health/`)**:
   - Centralized status manager tracking 11 subsystems with heartbeat monitoring.
   - Enforces failure propagation: critical failures pause/halt verification; non-critical failures trigger graceful degradation.
5. **Storage Management (`core/mission/storage_manager.py`)**:
   - Automated scaffolding of canonical directory hierarchy (`data/runs`, `data/evidence`, `data/recordings`, `data/logs`).
   - Disk space capacity tracking and pre-failure backpressure warnings.
6. **Mission Run & Reporting Engine (`core/mission/run_manager.py`)**:
   - Automated creation of reproducible run bundles with configuration and model snapshots.
   - Generation of self-contained audit packages (`mission_report.json` and `mission_report.html`).

---

## 3. Subsystem Boundary Invariants

* **No AI in Mission Decisions**: Perception models detect objects and hands; the assurance engine evaluates deterministic rules against the experiment procedure definition.
* **Non-Blocking Observability**: Ground streaming servers run in isolated background threads. If network throughput drops or ground links disconnect, the onboard core runtime continues unaffected.
* **Air-Gap Guarantee**: No module imports or calls external network sockets, web endpoints, or telemetry services for primary operation.
