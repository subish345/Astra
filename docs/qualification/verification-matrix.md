# ASTRA-EA: Master Qualification Verification Matrix (VCD)

**Classification:** Verification Control Document (VCD)  
**Standard:** ECSS-E-ST-10-02C (Verification)  
**Document ID:** `ASTRA-VCD-001`  
**Milestone:** Phase 15 — Qualification Readiness

---

## 1. Verification Methods & Levels Definition

### Verification Methods
- **`TEST` (T):** Quantitative measurement of functional or performance parameters against explicit numerical criteria.
- **`ANALYSIS` (A):** Verification through mathematical modeling, simulation, timing analysis, or code inspection.
- **`INSPECTION` (I):** Visual or documentary verification of physical, architectural, or configuration properties.
- **`DEMONSTRATION` (D):** Qualitative observation of functional performance without precise measurement.

### Verification Levels
- **`UNIT` / `COMPONENT` / `INTEGRATION` / `SYSTEM` / `HIL` / `PHYSICAL`:** Fully verified in Phase 0–14.
- **`ENVIRONMENTAL`:** Planned for future aerospace qualification facility execution (TRL 6).

---

## 2. Master Verification Control Matrix

| Req ID | Requirement Statement | Method | Test Level | Test Identifier | Verification Result | Evidence Artifact |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| **`ASTRA-SYS-001`** | Ingest $1280 \times 720$ optical video | **T** | Unit / Physical | `test_camera.py` | **VERIFIED** | `storage/evidence/live_camera_probe.jpg` |
| **`ASTRA-SYS-002`** | Detect designated 6 experiment classes | **T** | Component | `test_detector.py` | **VERIFIED** | `models/reports/model_evaluation_report.json` |
| **`ASTRA-SYS-003`** | Calculate spatial proximity ($IoU > 0.05$) | **T** | Component | `test_geometry.py` | **VERIFIED** | `reports/physical/viewpoint_report.html` |
| **`ASTRA-SYS-004`** | Accumulate $\ge 10$ frames temporal dwell | **T** | Component | `test_temporal.py` | **VERIFIED** | `final_submission/screenshots/04_evidence.jpg` |
| **`ASTRA-SYS-005`** | Deterministic procedure state tracking | **T** | Integration | `test_procedure.py` | **VERIFIED** | `configs/experiments/demo.yaml` |
| **`ASTRA-SYS-006`** | Tri-state assurance evaluation | **T** | Integration | `test_assurance.py` | **VERIFIED** | `data/runs/DEMO_RUN_001/events.json` |
| **`ASTRA-SYS-007`** | Cockpit voice guidance & alert HUD | **D** | System | `test_voice.py` | **VERIFIED** | `final_submission/demo_videos/02_wrong_object.mp4` |
| **`ASTRA-SYS-008`** | Closed-loop recovery verification | **T** | System / HIL | `test_recovery.py` | **VERIFIED** | `final_submission/demo_videos/03_recovery.mp4` |
| **`ASTRA-PERF-001`**| Pipeline throughput $\ge 30.0$ FPS | **T** | System | `test_benchmark.py` | **VERIFIED** | `reports/benchmark/benchmark_report.json` (34.2 FPS)|
| **`ASTRA-PERF-002`**| End-to-end P95 latency $\le 50.0$ ms | **T** | System | `test_soak.py` | **VERIFIED** | `reports/benchmark/soak_report.json` (26.4 ms P95) |
| **`ASTRA-PERF-003`**| Neural inference P50 latency $\le 25.0$ ms| **T** | Component | `test_runtime.py` | **VERIFIED** | `storage/reports/benchmark/baseline_benchmark.json` |
| **`ASTRA-PERF-004`**| RAM footprint $\le 1024$ MB (leak-free) | **T** | System | `test_soak_int.py` | **VERIFIED** | `final_submission/benchmark/resource_report.html` |
| **`ASTRA-IF-001`** | V4L2 device timeout handling $\le 100$ ms | **T** | HIL / Physical | `test_dropout.py` | **VERIFIED** | `reports/physical/failure_report.html` |
| **`ASTRA-IF-002`** | Vehicle bus interface abstraction | **I** | Architecture | Code Inspection | **VERIFIED** | `core/integration/bus.py` |
| **`ASTRA-IF-003`** | Dual-clock monotonic / UTC synchronization| **T** | System | `test_storage.py` | **VERIFIED** | `data/runs/DEMO_RUN_001/events.json` |
| **`ASTRA-SAF-001`** | Zero false verification on ambiguity | **T** | HIL | `test_faults.py` | **VERIFIED** | `storage/reports/simulation/sim_stress_optical.json`|
| **`ASTRA-SAF-002`** | Transition to `UNCERTAIN` on occlusion | **T** | Physical | `physical-test` | **VERIFIED** | `reports/physical/physical_validation.html` |
| **`ASTRA-SAF-003`** | Sensor dropout triggers `PAUSED` state | **T** | Physical / HIL | `hil run` | **VERIFIED** | `reports/hil/simulation_vs_physical.html` |
| **`ASTRA-SAF-004`** | Ground / audio failure isolation | **A & T**| System | `test_non_blocking`| **VERIFIED** | `final_submission/demo_videos/05_offline.mp4` |
| **`ASTRA-REL-002`** | Fallback to heuristic color detector | **T** | System | `test_models.py` | **VERIFIED** | `reports/hil/hardware_matrix.html` |
| **`ASTRA-SEC-001`** | 100% offline air-gap execution | **T** | System | `test_offline.py` | **VERIFIED** | `data/runs/DEMO_RUN_001/mission_report.json` |
| **`ASTRA-SEC-002`** | Cryptographic SHA-256 integrity verification| **T** | System | `competition-check`| **VERIFIED** | `competition/CHECKSUMS/SHA256SUMS` |
| **`ASTRA-ENV-001`** | Illumination invariance (45–850 Lux) | **T** | Physical | `physical-test` | **VERIFIED** | `reports/physical/physical_validation.json` |
| **`ASTRA-ENV-002`** | Multi-angle view invariance ($35^\circ-65^\circ$)| **T** | Physical | `physical-test` | **VERIFIED** | `reports/physical/viewpoint_report.html` |
| **`ASTRA-ENV-003`** | Launch random vibration ($14.1\text{ G}_\text{rms}$)| **T** | Environmental | *Shaker Table* | **PLANNED** | *Future Qualification Facility* |
| **`ASTRA-ENV-004`** | Thermal-vacuum cycling ($-20^\circ$ to $+60^\circ\text{C}$)| **T** | Environmental | *TVAC Chamber* | **PLANNED** | *Future Qualification Facility* |
| **`ASTRA-ENV-005`** | Radiation Total Ionizing Dose ($50\text{ krad}$)| **T** | Environmental | *Gamma / Proton Cell*| **PLANNED** | *Future Qualification Facility* |
