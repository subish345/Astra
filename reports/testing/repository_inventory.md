# ASTRA-EA Repository Inventory (Step 0)

### Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. System Inventory Metadata

| Component | Path / Configuration | Verification Status |
| :--- | :--- | :--- |
| **Entry Point** | `main.py` | Executable Python script launching CLI dispatch |
| **Canonical CLI** | `astra` (`core.cli.commands:cli`) | Installed entrypoint in PATH (`/home/subish-loq/.local/bin/astra` & `python3 main.py`) |
| **Python Version** | Python 3.14.7 (GCC 16.1.1 on Linux 7.1.12-200.fc44.x86_64) | Meets requirement (>= 3.11) |
| **Config Root** | `configs/` | System YAML (`system.yaml`), experiments (`configs/experiments/demo.yaml`), cameras, deployment, rehearsal |
| **Model Root** | `models/checkpoints/` | ONNX and PyTorch checkpoints (`ASTRA_OBJECT_DETECTOR_v0.1.0.onnx`, `ASTRA_OBJECT_DETECTOR_v0.1.0.meta.json`) |
| **Database** | `storage/database/astra.db` | SQLite 3.51.2 database with WAL journaling (15 core tables, migrations: 1) |
| **Camera System** | `core/camera/` | Direct V4L2 device `/dev/video0` (640x480 @ 30 FPS), OpenCV VideoCapture, SimulatedCameraSource |
| **Mission Runtime** | `core/ui/main_window.py`, `core/operations/rehearsal.py` | PySide6 Qt GUI Mission Console & Headless Flight Orchestrator |
| **Ground Runtime** | `apps/ground_monitor/` | Read-only PySide6 telemetry & video observability console (`apps/ground_monitor/app.py`) |
| **Test Framework** | `pytest 7.4.x` / `pytest-asyncio` | 332 automated tests across 24 test suites |

---

## 2. Canonical Commands Matrix (Verified against `core/cli/commands.py`)

```bash
# System Diagnostics & Hardware Verification
astra doctor
astra deployment doctor

# Hardware & Subsystem Tests
astra camera list
astra camera test --source 0 --frames 60
astra perception test --source 0
astra interaction test --source 0
astra activity test --source 0
astra procedure test --source 0
astra assurance test --source 0 --camera-profile view_left
astra voice test

# Flight Demonstrations & Missions
astra demo                      # Interactive Mission Console Demo
astra demo --headless           # Pure Terminal Automated Demo
astra mission                   # Astronaut Cockpit UI
astra mission precheck          # 9-Subsystem Pre-Mission Verification Matrix
astra ground-monitor            # Ground Control Observability Console

# Operational Rehearsals (Phase 20)
astra rehearsal --scenario GOLDEN_MISSION --speed ACCELERATED
astra dress-rehearsal --speed ACCELERATED
astra rehearsal-scorecard

# Findings-Driven Hardening (Phase 21)
astra hardening findings
astra hardening analyze <ID>
astra hardening reproduce <ID>
astra hardening regression
astra hardening readiness

# Automated Regression Test Suite
pytest tests/ -v
astra system-test
```
