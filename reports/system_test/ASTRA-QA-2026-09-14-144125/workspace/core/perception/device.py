"""Compute hardware and device selection manager for ASTRA-EA perception.

Inspects CUDA, GPU accelerators, and memory availability, providing clean CPU fallback
without crashing when GPU hardware or drivers are unavailable.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from core.common.logging import get_logger

logger = get_logger("PERCEPTION")


@dataclass
class DeviceInfo:
    """Detailed hardware acceleration profile."""
    backend: str  # "cuda" or "cpu"
    device_name: str
    cuda_available: bool
    vram_total_mb: Optional[int] = None
    vram_used_mb: Optional[int] = None

    @property
    def is_cuda(self) -> bool:
        return self.backend == "cuda" and self.cuda_available


class DeviceManager:
    """Manages inference device selection and hardware inspection."""

    @classmethod
    def get_device_info(cls, requested: str = "auto") -> DeviceInfo:
        """Resolve target compute device based on host hardware and configuration.

        Args:
            requested: "auto", "cuda", or "cpu".

        Returns:
            Resolved DeviceInfo object.
        """
        cuda_avail = False
        gpu_name = "Host CPU"
        vram_total = None
        vram_used = None

        # 1. Attempt PyTorch CUDA check if torch is present
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                cuda_avail = True
                gpu_name = torch.cuda.get_device_name(0)
                vram_total = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
        except ImportError:
            pass

        # 2. If torch CUDA wasn't detected, check nvidia-smi for host hardware
        if not cuda_avail:
            smi = shutil.which("nvidia-smi")
            if smi:
                try:
                    out = subprocess.check_output(
                        [smi, "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
                        text=True,
                        timeout=2,
                    ).strip()
                    parts = [p.strip() for p in out.split(",")]
                    if len(parts) >= 3:
                        gpu_name = parts[0]
                        vram_total = int(parts[1])
                        vram_used = int(parts[2])
                        # Note: Host GPU exists, but Python framework runtime may still be CPU-only
                        # if torch/onnx GPU wheels are not installed.
                except Exception:
                    pass

        # 3. Resolve selection
        req_lower = requested.lower()
        if req_lower == "cuda":
            if cuda_avail:
                selected_backend = "cuda"
            else:
                logger.warning("CUDA requested but not available in active Python runtime. Falling back to CPU.")
                selected_backend = "cpu"
        elif req_lower == "cpu":
            selected_backend = "cpu"
        else:  # "auto"
            selected_backend = "cuda" if cuda_avail else "cpu"

        logger.info(
            "Perception compute device resolved: %s (CUDA: %s, Hardware: %s)",
            selected_backend.upper(),
            cuda_avail,
            gpu_name,
        )

        return DeviceInfo(
            backend=selected_backend,
            device_name=gpu_name,
            cuda_available=cuda_avail,
            vram_total_mb=vram_total,
            vram_used_mb=vram_used,
        )
