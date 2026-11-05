# ASTRA-EA — Spacecraft Edge Deployment Guide

## Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
**Product Version:** `1.0.0-RC1`

---

## 1. Hardware Architecture Target

ASTRA-EA is designed to deploy on space-station payload computer form-factors (e.g. Spaceborne Computer, ruggedized payload controller, or embedded x86/ARM64 industrial boards):

* **CPU**: Quad-core x86_64 or ARM64 processor (e.g., Intel Core i5/i7, AMD Ryzen Embedded, or NVIDIA Jetson AGX Orin).
* **RAM**: Minimum 4.0 GB (8.0 GB recommended).
* **Storage**: NVMe or industrial SATA flash storage with at least 5.0 GB free space.
* **Optical Sensor**: USB 2.0/3.0 Video Class (UVC) camera or Gigabit Ethernet RTSP streaming camera.

---

## 2. Air-Gapped Installation Procedure

On an isolated, air-gapped target machine:

```bash
# 1. Clone or unpack repository archive
cd /path/to/astra

# 2. Run automated installer
chmod +x scripts/install.sh
./scripts/install.sh

# 3. Verify deployment doctor readiness
astra deployment doctor

# 4. Perform pre-demonstration final system check
astra final-check
```

---

## 3. Environment Configuration (`.env`)

Copy and configure environment overrides from `.env.example` if needed:

```bash
cp .env.example .env
```

Key environment parameters:
* `ASTRA_DATA_DIR`: Root path for runs, evidence, and recordings (Default: `./data`).
* `ASTRA_CAMERA_SOURCE`: Video device index or RTSP URL (Default: `0`).
* `ASTRA_CAMERA_PROFILE`: Camera perspective profile (`view_left` or `view_right`).
* `ASTRA_LOG_LEVEL`: Logging verbosity (`INFO` or `WARNING`).

---

## 4. Launching the System

### Canonical Launch Commands:
```bash
# Launch One-Command Demonstration (with self-test and nominal/deviation flow)
astra demo

# Launch One-Command Demonstration Headlessly (for CI or automated test harnesses)
astra demo --headless

# Launch Onboard Mission Console (PySide6 Interactive UI)
astra mission

# Launch Independent Ground Monitor Dashboard
astra ground-monitor
```
*(Development fallback `python3 main.py <command>` remains fully supported).*
