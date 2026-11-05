"""GPU and Accelerator Hardware Abstraction for ASTRA-EA (Phase 18)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class GPUCapabilities:
    has_gpu: bool
    accelerator_type: str  # CUDA, TENSORRT, NPU, NONE
    device_name: str
    total_memory_mb: float
    used_memory_mb: float
    free_memory_mb: float
    driver_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_gpu": self.has_gpu,
            "accelerator_type": self.accelerator_type,
            "device_name": self.device_name,
            "total_memory_mb": self.total_memory_mb,
            "used_memory_mb": self.used_memory_mb,
            "free_memory_mb": self.free_memory_mb,
            "driver_version": self.driver_version,
        }


class GPUMonitor:
    """Monitors GPU/NPU accelerator presence and VRAM usage."""

    def __init__(self) -> None:
        self._smi_path = shutil.which("nvidia-smi")

    def get_capabilities(self) -> GPUCapabilities:
        # Check NVIDIA GPU via nvidia-smi
        if self._smi_path:
            try:
                cmd = [
                    self._smi_path,
                    "--query-gpu=name,memory.total,memory.used,memory.free,driver_version",
                    "--format=csv,noheader,nounits",
                ]
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=2.0).decode("utf-8")
                lines = [line.strip() for line in out.splitlines() if line.strip()]
                if lines:
                    parts = [p.strip() for p in lines[0].split(",")]
                    name = parts[0]
                    total_m = float(parts[1]) if len(parts) > 1 else 0.0
                    used_m = float(parts[2]) if len(parts) > 2 else 0.0
                    free_m = float(parts[3]) if len(parts) > 3 else 0.0
                    drv = parts[4] if len(parts) > 4 else None
                    return GPUCapabilities(
                        has_gpu=True,
                        accelerator_type="CUDA",
                        device_name=name,
                        total_memory_mb=total_m,
                        used_memory_mb=used_m,
                        free_memory_mb=free_m,
                        driver_version=drv,
                    )
            except Exception:
                pass

        # Check Jetson Tegra / Tegrastats or sysfs for Orin/Xavier
        if os.path.exists("/sys/devices/gpu.0"):
            return GPUCapabilities(
                has_gpu=True,
                accelerator_type="TENSORRT",
                device_name="NVIDIA Orin Integrated GPU",
                total_memory_mb=16384.0,  # Unified memory
                used_memory_mb=0.0,
                free_memory_mb=16384.0,
                driver_version="JetPack L4T",
            )

        # Fallback CPU-only
        return GPUCapabilities(
            has_gpu=False,
            accelerator_type="NONE",
            device_name="None (Host CPU Inference)",
            total_memory_mb=0.0,
            used_memory_mb=0.0,
            free_memory_mb=0.0,
            driver_version=None,
        )
