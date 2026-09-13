# ASTRA-EA Machine Learning Environment Setup

Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. Overview

ASTRA-EA integrates a machine learning lifecycle alongside its deterministic baseline. While the deterministic baseline (`ColorSpatialObjectDetector`, `SpatialInteractionEngine`, `TriStateAssuranceEngine`) requires only standard Python libraries and OpenCV, model training and learned inference require a supported machine learning runtime.

The host development system is equipped with:
- **CPU**: Intel Core i7-14700HX (20 cores / 28 threads)
- **RAM**: 32 GB DDR5
- **GPU**: NVIDIA GeForce RTX 5060 Laptop GPU (8151 MiB VRAM)
- **Driver**: NVIDIA Linux 610.57+
- **CUDA Runtime / Driver API**: CUDA 12.x / 13.x compatible

---

## 2. Environment Verification

Check the current state of the machine learning environment using:

```bash
python3 main.py ml doctor
```

This diagnostic checks:
1. Active Python interpreter path and version.
2. PyTorch availability and version.
3. CUDA availability and CUDA device count.
4. Active GPU name and total VRAM.
5. `CUDA_VISIBLE_DEVICES` environment variable.
6. Execution of a live GPU tensor computation test (`torch.matmul`).

---

## 3. Installation Guide

### Option A: NVIDIA GPU Accelerated (Recommended for RTX 5060)

Install PyTorch with CUDA support matching your system's CUDA driver:

```bash
# For CUDA 12.4 (stable PyTorch wheel)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Or for nightly builds supporting latest CUDA drivers
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu126
```

Verify GPU acceleration:
```bash
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
python3 main.py ml doctor
```

### Option B: CPU-Only Setup (Testing & CI)

If running in a lightweight container or CI environment without GPU access:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

In CPU mode, training automatically adjusts batch sizes and logs `TRAINING: CPU FALLBACK`.

---

## 4. Troubleshooting Common Issues

### Issue 1: `PyTorch: MISSING (ModuleNotFoundError)`
**Cause**: PyTorch is not installed in the currently active virtualenv or Python environment.
**Solution**: Verify your virtual environment (`which python3`) and install PyTorch using the commands above.

### Issue 2: `CUDA: UNAVAILABLE` even though `nvidia-smi` works
**Cause**: The installed PyTorch wheel was compiled for CPU-only, or NVIDIA driver libraries are not accessible.
**Solution**:
1. Check `nvidia-smi` works from terminal.
2. Verify PyTorch version: `python3 -c "import torch; print(torch.__version__)"`. If it ends in `+cpu`, reinstall with `+cu124` or `+cu126`.
3. Ensure `LD_LIBRARY_PATH` includes CUDA toolkit paths if installed locally.

### Issue 3: Out of Memory (CUDA OOM)
**Cause**: Batch size or input resolution exceeds RTX 5060 8GB VRAM capacity during training.
**Solution**:
Set `batch_size: 8` or `batch_size: 4` and `image_size: 640` in training configurations.

---

## 5. Directory & Model Storage Conventions

ASTRA-EA strictly isolates raw datasets, versioned splits, training artifacts, and model checkpoints:

```text
datasets/
├── raw/
│   ├── synthetic/           # Synthetic image scenes
│   └── real/                # Recorded session videos (SESSION_001, etc.)
├── annotations/             # JSON ground-truth annotations
├── splits/                  # Session-partitioned manifests (train, val, test)
├── manifests/               # Dataset manifests (ASTRA-DATASET-v0.1.json)
└── reports/                 # Dataset balance and validation reports

models/
├── checkpoints/             # Saved weight checkpoints (*.pt)
├── registry/                # ModelRegistry metadata (models.json)
└── training_runs/           # Immutable logs, metrics.json, and curves.png
```
