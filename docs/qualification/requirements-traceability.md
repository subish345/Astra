# ASTRA-EA: Requirements Traceability Matrix (RTM)

**Classification:** Verification & Quality Assurance Traceability Record  
**Standard:** ECSS-E-ST-10-02C / NASA Systems Engineering Handbook  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. End-to-End Vertical Traceability Architecture

Every requirement in ASTRA-EA traces through five engineering layers:
$$\text{System Requirement} \longrightarrow \text{Design Component} \longrightarrow \text{Implementation File} \longrightarrow \text{Verification Test} \longrightarrow \text{Empirical Evidence}$$

---

## 2. Master Requirements Traceability Table

| Requirement ID | Design Subsystem | Source Implementation | Automated Verification Test | Empirical Evidence Artifact | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **`ASTRA-SYS-001`** | Video Ingestion Engine | `core/camera/webcam.py` | `tests/unit/test_camera.py` | `storage/evidence/live_camera_probe.jpg` | **VERIFIED** |
| **`ASTRA-SYS-002`** | Neural Perception | `core/perception/detection/` | `tests/perception/test_detector.py` | `models/reports/model_evaluation_report.json` | **VERIFIED** |
| **`ASTRA-SYS-003`** | Spatial Interaction | `core/interaction/geometry.py` | `tests/interaction/test_geometry.py` | `final_submission/screenshots/02_live_perception.jpg` | **VERIFIED** |
| **`ASTRA-SYS-004`** | Temporal Activity | `core/activity/temporal.py` | `tests/activity/test_temporal.py` | `final_submission/screenshots/04_evidence_panel.jpg` | **VERIFIED** |
| **`ASTRA-SYS-005`** | Procedure State Engine | `core/procedure/progress.py` | `tests/procedure/test_procedure.py` | `configs/experiments/demo.yaml` | **VERIFIED** |
| **`ASTRA-SYS-006`** | Tri-State Assurance | `core/assurance/engine.py` | `tests/assurance/test_assurance.py` | `data/runs/DEMO_RUN_001/events.json` | **VERIFIED** |
| **`ASTRA-SYS-007`** | Cockpit Voice Engine | `core/assistance/voice.py` | `tests/audio/test_voice.py` | `final_submission/screenshots/05_deviation.jpg` | **VERIFIED** |
| **`ASTRA-SYS-008`** | Recovery Manager | `core/assistance/recovery.py` | `tests/unit/test_recovery.py` | `final_submission/screenshots/06_recovery.jpg` | **VERIFIED** |
| **`ASTRA-PERF-001`**| Runtime Scheduler | `core/optimization/scheduler.py`| `tests/benchmark/test_framework.py`| `reports/benchmark/benchmark_report.json` (34.2 FPS)| **VERIFIED** |
| **`ASTRA-PERF-002`**| End-to-End Pipeline | `core/mission/orchestrator.py` | `tests/system/test_soak.py` | `reports/benchmark/soak_report.json` (26.4 ms P95) | **VERIFIED** |
| **`ASTRA-PERF-003`**| ONNX Model Runtime | `models/checkpoints/` | `tests/optimization/test_runtime.py`| `storage/reports/benchmark/baseline_benchmark.json` | **VERIFIED** |
| **`ASTRA-PERF-004`**| Memory Manager | `core/health/aggregator.py` | `tests/system/test_soak_integration.py`| `final_submission/benchmark/resource_report.html` | **VERIFIED** |
| **`ASTRA-IF-001`** | V4L2 Device Manager | `core/camera/webcam.py` | `tests/camera_views/test_view.py` | `reports/physical/failure_report.html` | **VERIFIED** |
| **`ASTRA-IF-002`** | Vehicle Bus Adapter | `core/integration/bus.py` | `tests/qualification/test_framework.py`| `docs/qualification/interface-control-document.md`| **VERIFIED** |
| **`ASTRA-IF-003`** | Dual-Clock Syncer | `core/mission/clock.py` | `tests/storage/test_storage.py` | `data/runs/DEMO_RUN_001/events.json` | **VERIFIED** |
| **`ASTRA-IF-004`** | Ground Telemetry Pub | `streaming/events/publisher.py` | `tests/streaming/test_events.py` | `final_submission/screenshots/08_ground_monitor.jpg`| **VERIFIED** |
| **`ASTRA-SAF-001`** | Epistemic Guard | `core/assurance/engine.py` | `tests/simulation/test_faults.py` | `storage/reports/simulation/sim_stress_optical.json`| **VERIFIED** |
| **`ASTRA-SAF-002`** | Uncertainty Window | `core/activity/confidence.py` | `tests/simulation/test_faults.py` | `final_submission/demo_videos/04_uncertainty.mp4` | **VERIFIED** |
| **`ASTRA-SAF-003`** | Ingestion Supervisor | `core/camera/webcam.py` | `tests/simulation/test_dropout.py`| `reports/physical/failure_report.html` | **VERIFIED** |
| **`ASTRA-SAF-004`** | Fault Isolation Boundary| `core/mission/orchestrator.py`| `tests/streaming/test_non_blocking.py`| `final_submission/demo_videos/05_offline.mp4` | **VERIFIED** |
| **`ASTRA-REL-001`** | Worker Process Boundary| `core/mission/orchestrator.py`| `tests/system/test_failure_regression.py`| `storage/reports/simulation_matrix_report.json` | **VERIFIED** |
| **`ASTRA-REL-002`** | Model Fallback Engine | `core/perception/detection/` | `tests/models/test_models.py` | `reports/hil/hardware_matrix.html` | **VERIFIED** |
| **`ASTRA-SEC-001`** | Air-Gap Network Engine | `main.py` | `tests/system/test_offline.py` | `data/runs/DEMO_RUN_001/mission_report.json` | **VERIFIED** |
| **`ASTRA-SEC-002`** | SHA-256 Verifier | `core/cli/commands.py` | `tests/streaming/test_security.py`| `competition/CHECKSUMS/SHA256SUMS` | **VERIFIED** |
| **`ASTRA-DAT-001`** | SQLite Storage Manager | `core/mission/database.py` | `tests/storage/test_storage.py` | `storage/astra.db` | **VERIFIED** |
| **`ASTRA-DAT-002`** | Causal Provenance Trace| `final_traceability_example.html`| `tests/procedure/test_traceability.py`| `final_traceability_example.html` | **VERIFIED** |
| **`ASTRA-ENV-001`** | Optical Lux Invariance | `core/hardware/physical_runner.py`| `tests/simulation/test_faults.py` | `reports/physical/physical_validation.html` | **VERIFIED** |
| **`ASTRA-ENV-002`** | Multi-Angle View Engine| `configs/cameras/calibration/` | `tests/camera_views/test_views.py`| `reports/physical/viewpoint_report.html` | **VERIFIED** |
| **`ASTRA-ENV-003`** | Launch Vibration Screen| *Future Space Hardware* | *Environmental Chamber* | *PLANNED (TRL 6 Environmental Test Plan)* | **PLANNED** |
| **`ASTRA-ENV-004`** | Thermal-Vacuum TVAC | *Future Space Hardware* | *TVAC Chamber* | *PLANNED (TRL 6 Environmental Test Plan)* | **PLANNED** |
| **`ASTRA-ENV-005`** | Radiation Screening | *Future Space Hardware* | *Cyclotron / Gamma Cell* | *PLANNED (TRL 6 Environmental Test Plan)* | **PLANNED** |
