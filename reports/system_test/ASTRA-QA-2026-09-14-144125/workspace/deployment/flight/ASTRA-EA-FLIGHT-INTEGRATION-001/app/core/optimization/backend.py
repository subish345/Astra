"""Compute hardware abstraction and device execution backends for ASTRA-EA.

Decouples the flight core from specific workstation hardware (e.g. RTX 5060)
providing clean, extensible ComputeBackend interfaces for CPU, CUDA, and future
edge accelerators (Jetson Orin, Hailo-8, Google Coral) with zero-crash fallbacks.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import psutil

from core.common.logging import get_logger

logger = get_logger("OPTIMIZATION")


@dataclass
class PlatformTelemetry:
    """Detailed hardware and operating system profile."""
    os_name: str
    os_release: str
    architecture: str
    cpu_model: str
    cpu_cores_physical: int
    cpu_cores_logical: int
    total_ram_gb: float
    gpu_name: str
    gpu_available: bool
    vram_total_mb: Optional[int]
    active_backend: str
    python_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_name": self.os_name,
            "os_release": self.os_release,
            "architecture": self.architecture,
            "cpu_model": self.cpu_model,
            "cpu_cores_physical": self.cpu_cores_physical,
            "cpu_cores_logical": self.cpu_cores_logical,
            "total_ram_gb": round(self.total_ram_gb, 2),
            "gpu_name": self.gpu_name,
            "gpu_available": self.gpu_available,
            "vram_total_mb": self.vram_total_mb,
            "active_backend": self.active_backend,
            "python_version": self.python_version,
        }


class ComputeBackend(ABC):
    """Abstract compute execution backend interface."""

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Type of backend: 'cpu', 'cuda', or 'edge'."""
        ...

    @property
    @abstractmethod
    def device_name(self) -> str:
        """Human-readable identifier for the compute device."""
        ...

    @property
    @abstractmethod
    def is_accelerated(self) -> bool:
        """Whether hardware acceleration (GPU/NPU/TPU) is active."""
        ...

    @abstractmethod
    def memory_info(self) -> Dict[str, Any]:
        """Return memory allocation statistics for this backend."""
        ...

    @abstractmethod
    def synchronize(self) -> None:
        """Block until all outstanding compute operations complete."""
        ...


class CPUBackend(ComputeBackend):
    """Deterministic host CPU compute backend."""

    def __init__(self) -> None:
        self._name = platform.processor() or "Host CPU"

    @property
    def backend_type(self) -> str:
        return "cpu"

    @property
    def device_name(self) -> str:
        return self._name

    @property
    def is_accelerated(self) -> bool:
        return False

    def memory_info(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        proc = psutil.Process()
        return {
            "backend": "cpu",
            "process_rss_mb": round(proc.memory_info().rss / (1024 * 1024), 2),
            "system_available_ram_gb": round(mem.available / (1024**3), 2),
            "system_total_ram_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
        }

    def synchronize(self) -> None:
        # CPU operations execute synchronously on the calling thread
        pass


class CUDABackend(ComputeBackend):
    """NVIDIA CUDA GPU execution backend with graceful fallback."""

    def __init__(self, device_id: int = 0) -> None:
        self.device_id = device_id
        self._cuda_available = False
        self._gpu_name = "NVIDIA CUDA (Uninitialized)"
        self._vram_total_mb: Optional[int] = None
        self._initialize()

    def _initialize(self) -> None:
        """Discover CUDA hardware via PyTorch or nvidia-smi."""
        try:
            import torch  # type: ignore
            if torch.cuda.is_available() and torch.cuda.device_count() > self.device_id:
                self._cuda_available = True
                self._gpu_name = torch.cuda.get_device_name(self.device_id)
                self._vram_total_mb = int(
                    torch.cuda.get_device_properties(self.device_id).total_memory / (1024 * 1024)
                )
                logger.info("Initialized PyTorch CUDA backend: %s", self._gpu_name)
                return
        except ImportError:
            pass

        # Fallback inspection via nvidia-smi
        smi = shutil.which("nvidia-smi")
        if smi:
            try:
                out = subprocess.check_output(
                    [smi, f"--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                    text=True,
                    timeout=2,
                ).strip()
                lines = out.splitlines()
                if lines and len(lines) > self.device_id:
                    parts = [p.strip() for p in lines[self.device_id].split(",")]
                    if len(parts) >= 2:
                        self._gpu_name = parts[0]
                        self._vram_total_mb = int(parts[1])
                        # Note: Hardware exists on host, but active Python environment
                        # might lack torch/onnx GPU runtime wheels.
                        logger.info("Discovered host GPU hardware: %s (%d MB)", self._gpu_name, self._vram_total_mb)
            except Exception as e:
                logger.debug("nvidia-smi check failed: %s", e)

    @property
    def backend_type(self) -> str:
        return "cuda"

    @property
    def device_name(self) -> str:
        return self._gpu_name

    @property
    def is_accelerated(self) -> bool:
        return self._cuda_available

    def memory_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "backend": "cuda",
            "device_name": self._gpu_name,
            "cuda_available": self._cuda_available,
            "vram_total_mb": self._vram_total_mb,
            "vram_used_mb": None,
        }

        # Try torch memory queries
        try:
            import torch  # type: ignore
            if self._cuda_available:
                info["vram_allocated_mb"] = round(torch.cuda.memory_allocated(self.device_id) / (1024 * 1024), 2)
                info["vram_reserved_mb"] = round(torch.cuda.memory_reserved(self.device_id) / (1024 * 1024), 2)
        except Exception:
            pass

        # Query nvidia-smi if available
        smi = shutil.which("nvidia-smi")
        if smi:
            try:
                out = subprocess.check_output(
                    [smi, "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                    text=True,
                    timeout=1,
                ).strip()
                parts = [p.strip() for p in out.split(",")]
                if len(parts) >= 2:
                    info["vram_used_mb"] = int(parts[0])
                    info["gpu_utilization_percent"] = int(parts[1])
            except Exception:
                pass

        return info

    def synchronize(self) -> None:
        """Synchronize CUDA compute streams if available."""
        if self._cuda_available:
            try:
                import torch  # type: ignore
                t0 = time.perf_counter()
                torch.cuda.synchronize(self.device_id)
                self._last_sync_ms = (time.perf_counter() - t0) * 1000.0
            except Exception:
                pass


class FutureEdgeBackend(ComputeBackend):
    """Extensible abstraction for specialized edge accelerators (NPU, TPU, DSP)."""

    def __init__(self, accelerator_name: str = "GenericEdgeNPU", api_type: str = "generic") -> None:
        self._name = accelerator_name
        self._api = api_type

    @property
    def backend_type(self) -> str:
        return "edge"

    @property
    def device_name(self) -> str:
        return f"{self._name} ({self._api})"

    @property
    def is_accelerated(self) -> bool:
        return True

    def memory_info(self) -> Dict[str, Any]:
        return {
            "backend": "edge",
            "accelerator": self._name,
            "status": "READY_FOR_INTEGRATION",
        }

    def synchronize(self) -> None:
        pass


class PlatformInspector:
    """Inspects and profiles host environment without vendor lock-in."""

    @classmethod
    def get_telemetry(cls, preferred_backend: str = "auto") -> PlatformTelemetry:
        """Inspect host platform and resolve best available compute backend."""
        cpu_model = "Unknown CPU"
        try:
            if platform.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            cpu_model = line.split(":", 1)[1].strip()
                            break
        except Exception:
            pass

        cores_phys = psutil.cpu_count(logical=False) or 1
        cores_log = psutil.cpu_count(logical=True) or 1
        ram_gb = psutil.virtual_memory().total / (1024**3)

        cuda_backend = CUDABackend()
        gpu_name = cuda_backend.device_name
        gpu_avail = cuda_backend.is_accelerated
        vram = cuda_backend._vram_total_mb

        pref = preferred_backend.lower()
        if pref == "cuda" and gpu_avail:
            active_backend = "cuda"
        elif pref == "edge":
            active_backend = "edge"
        elif pref == "auto":
            active_backend = "cuda" if gpu_avail else "cpu"
        else:
            active_backend = "cpu"

        return PlatformTelemetry(
            os_name=platform.system(),
            os_release=platform.release(),
            architecture=platform.machine(),
            cpu_model=cpu_model,
            cpu_cores_physical=cores_phys,
            cpu_cores_logical=cores_log,
            total_ram_gb=ram_gb,
            gpu_name=gpu_name,
            gpu_available=gpu_avail,
            vram_total_mb=vram,
            active_backend=active_backend,
            python_version=platform.python_version(),
        )

    @classmethod
    def create_backend(cls, requested: str = "auto") -> ComputeBackend:
        """Factory method resolving ComputeBackend instance."""
        req = requested.lower()
        if req == "cuda":
            backend = CUDABackend()
            if not backend.is_accelerated:
                logger.warning("CUDA requested but unavailable in Python runtime. Falling back to CPU.")
                return CPUBackend()
            return backend
        elif req == "edge":
            return FutureEdgeBackend()
        elif req == "cpu":
            return CPUBackend()
        else:  # auto
            cuda = CUDABackend()
            if cuda.is_accelerated:
                return cuda
            return CPUBackend()
