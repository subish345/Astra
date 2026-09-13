"""ASTRA-EA Machine Learning Environment Diagnostics (ML Doctor).

Provides comprehensive verification of:
- Python runtime
- PyTorch availability and version
- CUDA driver and runtime status
- CUDA device count, device names, and VRAM capacities
- CUDA visible devices environment
- Torch GPU tensor allocation / computation test
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional


def query_host_nvidia_smi() -> Optional[Dict[str, Any]]:
    """Query host nvidia-smi tool for hardware specifications if available."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None

    try:
        query_cmd = [
            nvidia_smi,
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits",
        ]
        out = subprocess.check_output(query_cmd, text=True, timeout=5).strip()
        if not out:
            return None
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if not lines:
            return None

        # Parse first GPU
        parts = [p.strip() for p in lines[0].split(",")]
        return {
            "gpu_count": len(lines),
            "gpu_name": parts[0] if len(parts) > 0 else "NVIDIA GPU",
            "vram_total_mib": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None,
            "vram_free_mib": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None,
            "driver_version": parts[3] if len(parts) > 3 else "Unknown",
        }
    except Exception:
        return None


def inspect_ml_environment() -> Dict[str, Any]:
    """Inspect and return ML runtime diagnostics dictionary."""
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "Not explicitly set (defaults to all)")

    report: Dict[str, Any] = {
        "python_version": py_ver,
        "cuda_visible_devices": cuda_visible,
        "pytorch_available": False,
        "pytorch_version": None,
        "cuda_available": False,
        "cuda_device_count": 0,
        "gpu_name": None,
        "vram_total_mb": None,
        "tensor_test": "NOT_RUN",
        "status": "BLOCKED",
        "message": "",
    }

    # First check host GPU via nvidia-smi
    smi_info = query_host_nvidia_smi()
    if smi_info:
        report["gpu_name"] = smi_info["gpu_name"]
        report["vram_total_mb"] = smi_info["vram_total_mib"]
        report["driver_version"] = smi_info.get("driver_version")
        report["host_gpu_count"] = smi_info["gpu_count"]

    # Try importing PyTorch
    try:
        import torch  # type: ignore

        report["pytorch_available"] = True
        report["pytorch_version"] = torch.__version__

        cuda_avail = torch.cuda.is_available()
        report["cuda_available"] = cuda_avail

        if cuda_avail:
            device_count = torch.cuda.device_count()
            report["cuda_device_count"] = device_count
            curr_dev = torch.cuda.current_device()
            dev_name = torch.cuda.get_device_name(curr_dev)
            report["gpu_name"] = dev_name

            props = torch.cuda.get_device_properties(curr_dev)
            total_vram_mb = int(props.total_memory / (1024 * 1024))
            report["vram_total_mb"] = total_vram_mb

            # Perform live GPU tensor computation test
            try:
                x = torch.randn(100, 100, device="cuda")
                y = torch.matmul(x, x)
                torch.cuda.synchronize()
                report["tensor_test"] = "PASS"
                report["status"] = "AVAILABLE"
                report["message"] = "PyTorch with CUDA GPU acceleration is operational."
            except Exception as ex:
                report["tensor_test"] = f"FAIL ({ex})"
                report["status"] = "DEGRADED"
                report["message"] = f"CUDA device detected but tensor computation failed: {ex}"
        else:
            # CPU Fallback
            try:
                x = torch.randn(50, 50)
                y = torch.matmul(x, x)
                report["tensor_test"] = "PASS (CPU)"
                report["status"] = "CPU_FALLBACK"
                report["message"] = (
                    "PyTorch is installed with CPU support only. "
                    "CUDA runtime is not detected in the current PyTorch build."
                )
            except Exception as ex:
                report["tensor_test"] = f"FAIL ({ex})"
                report["status"] = "DEGRADED"
                report["message"] = f"CPU tensor computation failed: {ex}"

    except ImportError:
        report["pytorch_available"] = False
        report["status"] = "BLOCKED"
        if smi_info:
            report["message"] = (
                f"PyTorch is not installed in the active environment ({sys.executable}). "
                f"Host hardware has {smi_info['gpu_name']} ({smi_info['vram_total_mib']} MiB VRAM). "
                "Install PyTorch with CUDA support to enable GPU training."
            )
        else:
            report["message"] = (
                f"PyTorch is not installed in the active environment ({sys.executable}). "
                "Install PyTorch to enable model training."
            )

    return report


def run_ml_doctor() -> int:
    """Run interactive ML diagnostic check and print formatted report."""
    print("=" * 60)
    print("ASTRA-EA ML ENVIRONMENT DIAGNOSTIC")
    print("=" * 60)

    info = inspect_ml_environment()

    print(f"Python:\n  {info['python_version']} ({sys.executable})\n")

    if info["pytorch_available"]:
        print(f"PyTorch:\n  AVAILABLE (v{info['pytorch_version']})\n")
    else:
        print("PyTorch:\n  MISSING (ModuleNotFoundError)\n")

    if info["cuda_available"]:
        print(f"CUDA:\n  AVAILABLE ({info['cuda_device_count']} device(s))\n")
    else:
        print("CUDA:\n  UNAVAILABLE (in active PyTorch runtime)\n")

    if info["gpu_name"]:
        vram_str = f"{info['vram_total_mb']} MiB" if info["vram_total_mb"] else "Unknown"
        print(f"GPU:\n  {info['gpu_name']} (VRAM: {vram_str})\n")
    else:
        print("GPU:\n  No GPU detected\n")

    print(f"CUDA Visible Devices:\n  {info['cuda_visible_devices']}\n")
    print(f"GPU Tensor Test:\n  {info['tensor_test']}\n")
    print("-" * 60)
    print(f"ML ENVIRONMENT STATUS:\n  {info['status']}")
    print(f"Diagnostics:\n  {info['message']}")
    print("=" * 60)

    if info["status"] == "AVAILABLE":
        return 0
    elif info["status"] == "CPU_FALLBACK":
        print("\n[NOTE] CPU fallback training is functional but GPU acceleration is recommended.")
        return 0
    else:
        print("\n[NOTE] See docs/development/ml-environment.md for PyTorch/CUDA setup instructions.")
        return 1
