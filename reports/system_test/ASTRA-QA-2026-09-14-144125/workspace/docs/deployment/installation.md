# ASTRA-EA Deployment & Installation Guide

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Product Version**: `v1.0.0`

---

## 1. System Requirements

* **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+, or lightweight embedded Linux).
* **Python Runtime**: Python `>= 3.11` (Tested and validated on Python 3.14).
* **Memory (RAM)**: `>= 4 GB` (8 GB recommended for 60 FPS full pipeline).
* **Disk Storage**: `>= 5 GB` free space for models, datasets, evidence, and run recordings.
* **Camera Sensor**: USB Video Class (UVC) webcam, IP RTSP stream, or synthetic file source.
* **Hardware Acceleration**: Optional ONNX Runtime CPU SIMD, CUDA, or TensorRT.

---

## 2. Quick Installation

Execute the automated local installer from the repository root:

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

Or install manually via editable pip packaging:

```bash
# 1. Install virtual environment dependencies
python3 -m pip install -e .

# 2. Verify native CLI availability
astra version
```

---

## 3. Pre-Flight System Audit (Deployment Doctor)

Before initiating a mission or demonstration, execute the deployment doctor:

```bash
astra deployment doctor
```

Expected readiness output:
```text
================================================================================
 ASTRA-EA DEPLOYMENT READINESS AUDIT (DOCTOR) — v1.0.0
================================================================================
COMPONENT                  DETAILS                                    VERDICT   
--------------------------------------------------------------------------------
Python Runtime             v3.14.7 (>= 3.11 required)                 PASS      
Dependencies               Core libraries installed                   PASS      
Model Checkpoints          ASTRA_OBJECT_DETECTOR_v0.1.0.onnx presen   PASS      
SQLite Database            storage/database/astra.db (WAL enabled)    PASS      
Storage Subsystem          191.3 GB free on root partition            PASS      
Optical Sensor (Cam 0)     Device /dev/video0 responsive              PASS      
Display Environment        GUI Display active (:0)                    PASS      
Compute Hardware           Host CPU SIMD backend active (Zero GPU d   PASS      
Configuration Hierarchy    configs/system.yaml & deployment profile   PASS      
Streaming Network          Ports 8554 (Video) & 8765 (Events) free    PASS      
================================================================================
DEPLOYMENT STATUS: DEPLOYMENT READY
================================================================================
```

---

## 4. Canonical Product Commands

| Command | Purpose |
| :--- | :--- |
| `astra demo` | Launch one-command autonomous flight demonstration (nominal, deviation, recovery, report). |
| `astra demo --headless` | Run complete demonstration sequence headlessly in CI or automated terminal environments. |
| `astra mission` | Launch primary on-board Mission Console runtime. |
| `astra mission --profile validation` | Launch mission runtime in validation mode with comprehensive audit assertions. |
| `astra ground-monitor` | Launch independent ground observability dashboard. |
| `astra doctor` | Perform comprehensive core subsystem health checks. |
| `astra simulation run-all` | Execute complete batch simulation matrix (6 resilience scenarios). |
| `astra benchmark baseline` | Measure real-time FPS and latency profile across perception pipeline. |

*Note: The development fallback syntax (`python3 main.py <command>`) remains 100% backward-compatible.*
