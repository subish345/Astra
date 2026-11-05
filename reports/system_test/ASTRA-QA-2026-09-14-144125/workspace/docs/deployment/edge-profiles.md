# Edge Deployment Profiles & Hardware Compatibility

## 1. Overview

ASTRA-EA features a multi-tiered, configuration-driven deployment architecture. Configurations are located in `configs/deployment/` and govern perception resolution, inference cadences, streaming bitrates, and hardware resource limits.

---

## 2. Standard Deployment Profiles

### A. `development.yaml` (`PROFILE_DEV`)
- **Target Platform**: Workstation / Development Laptop (e.g., Intel Core i7-14700HX + RTX 5060).
- **Goal**: Comprehensive debugging, maximum telemetry logging, full visual overlays.
- **Cadence**: All modules run 1:1 on every frame.
- **Queue**: FIFO buffer (depth 10).
- **Resource Budget**: 8.0 GB RAM, 6.0 GB VRAM, 90% CPU.

### B. `balanced.yaml` (`PROFILE_BALANCED`)
- **Target Platform**: Nominal operational ground demonstrator or standard edge PC.
- **Goal**: Balanced real-time assurance targeting 30 FPS.
- **Cadence**: Detection 1:1, Pose 1:1, Hands 1:1, Tracking 1:1.
- **Queue**: Latest-frame drop-oldest (depth 5).
- **Resource Budget**: 4.0 GB RAM, 4.0 GB VRAM, 85% CPU.

### C. `realtime.yaml` (`PROFILE_REALTIME`)
- **Target Platform**: High-frame-rate tracking systems targeting 60+ FPS.
- **Goal**: Minimize end-to-end decision latency without sacrificing step assurance.
- **Cadence**: Tracking 1:1, Detection 1:1, Pose 1:2 (interleaved), Hands 1:1.
- **Queue**: Strict latest-frame drop-oldest (depth 2).
- **Resource Budget**: 4.0 GB RAM, 4.0 GB VRAM, 80% CPU.

### D. `low_resource.yaml` (`PROFILE_LOW_RESOURCE`)
- **Target Platform**: Power-constrained embedded avionics, micro-rovers, or degraded mode.
- **Goal**: Maximum energy efficiency and minimal CPU/memory footprint.
- **Cadence**: Tracking 1:1, Detection 1:2, Pose 1:3, Hands 1:2.
- **Resolution**: 320x320.
- **Stream**: Disabled.
- **Queue**: Strict latest-frame drop-oldest (depth 2).
- **Resource Budget**: 2.0 GB RAM, 1.0 GB VRAM, 65% CPU.

---

## 3. Hardware Compatibility Matrix

Verified on host platform (`Intel Core i7-14700HX`, Linux 7.1.12 x86_64):

| Model Identifier | Model Type | Host CPU | NVIDIA CUDA | ONNX DNN Runtime | Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `ColorSpatialObjectDetector` | Algorithmic Baseline | ✓ | — | — | **OPERATIONAL** |
| `ASTRA_OBJECT_DETECTOR_v0.1.0` | Learned Checkpoint | ✓ | — | — | **OPERATIONAL** |
| `ASTRA_OBJECT_DETECTOR_v0.1.0.onnx` | Exported ONNX Graph | ✓ | — | ✓ | **VALIDATED** |

---

## 4. Resource Allocation & Telemetry

When launching ASTRA-EA in production or benchmark mode, the active configuration is applied via `DeploymentProfileManager`:

```python
from core.optimization.profiles import DeploymentProfileManager
config = DeploymentProfileManager.load_profile("realtime")
```

The system continuously checks memory and CPU consumption via `BudgetMonitor`. If resource ceilings are breached, the system initiates degraded mode adaptation, safeguarding procedural assurance.
