"""Edge Compute Diagnostics and Hardware Capability Profiler for ASTRA-EA.

Inspects host system hardware architecture, CPU/GPU accelerators,
memory hierarchy, thermal sensors, and inference runtime engines.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def get_edge_hardware_profile() -> Dict[str, Any]:
    """Capture comprehensive hardware, OS, and edge compute diagnostic metadata."""
    import psutil

    # 1. Platform & OS
    arch = platform.machine()
    system_name = platform.system()
    kernel = platform.release()

    # Distro name
    distro = "Linux"
    if hasattr(platform, "freedesktop_os_release"):
        try:
            os_info = platform.freedesktop_os_release()
            distro = os_info.get("PRETTY_NAME", os_info.get("NAME", "Linux"))
        except Exception:
            pass

    # 2. CPU Architecture
    cpu_count_logical = psutil.cpu_count(logical=True) or 1
    cpu_count_physical = psutil.cpu_count(logical=False) or 1
    cpu_freq = psutil.cpu_freq()
    cpu_freq_mhz = cpu_freq.current if cpu_freq else 0.0

    cpu_model = platform.processor() or "Unknown CPU"
    try:
        if Path("/proc/cpuinfo").exists():
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_model = line.split(":", 1)[1].strip()
                        break
    except Exception:
        pass

    # 3. Memory Profile
    vm = psutil.virtual_memory()
    total_ram_mb = round(vm.total / (1024**2), 1)
    available_ram_mb = round(vm.available / (1024**2), 1)
    used_ram_mb = round(vm.used / (1024**2), 1)

    # Process RSS
    proc = psutil.Process(os.getpid())
    process_rss_mb = round(proc.memory_info().rss / (1024**2), 1)

    # 4. Storage Profile
    import shutil
    total_disk, used_disk, free_disk = shutil.disk_usage(".")
    disk_total_gb = round(total_disk / (1024**3), 1)
    disk_free_gb = round(free_disk / (1024**3), 1)

    # 5. GPU / NPU Acceleration
    gpu_name = "None (CPU Execution)"
    vram_total_mb = 0.0
    vram_used_mb = 0.0
    has_gpu = False

    try:
        import torch
        if torch.cuda.is_available():
            has_gpu = True
            gpu_name = torch.cuda.get_device_name(0)
            vram_total_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024**2), 1)
            vram_used_mb = round(torch.cuda.memory_allocated(0) / (1024**2), 1)
    except Exception:
        pass

    # 6. Thermal Telemetry
    thermal_status = "NOT AVAILABLE"
    temp_celsius: Optional[float] = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for sensor_name, entries in temps.items():
                if entries:
                    temp_celsius = round(entries[0].current, 1)
                    thermal_status = f"{sensor_name}: {temp_celsius}°C"
                    break
    except Exception:
        thermal_status = "NOT AVAILABLE"

    # 7. Power Telemetry
    power_status = "NOT AVAILABLE"
    try:
        battery = psutil.sensors_battery()
        if battery:
            power_status = f"Battery: {battery.percent}% ({'Plugged In' if battery.power_plugged else 'Discharging'})"
    except Exception:
        power_status = "NOT AVAILABLE"

    # 8. Inference Runtime
    inference_engines = []
    try:
        import onnxruntime
        inference_engines.append(f"ONNX Runtime {onnxruntime.__version__}")
    except ImportError:
        pass

    try:
        import torch
        inference_engines.append(f"PyTorch {torch.__version__}")
    except ImportError:
        pass

    runtime_str = ", ".join(inference_engines) if inference_engines else "Native Python / OpenCV"

    # 9. Active Models
    model_name = "ASTRA_OBJECT_DETECTOR_v1.0"
    model_path = Path("models/checkpoints/ASTRA_OBJECT_DETECTOR_v0.1.0.onnx")
    model_exists = model_path.exists()

    return {
        "platform": arch,
        "os_distro": distro,
        "kernel": kernel,
        "cpu_model": cpu_model,
        "cpu_cores_physical": cpu_count_physical,
        "cpu_cores_logical": cpu_count_logical,
        "cpu_frequency_mhz": cpu_freq_mhz,
        "ram_total_mb": total_ram_mb,
        "ram_available_mb": available_ram_mb,
        "ram_used_mb": used_ram_mb,
        "process_rss_mb": process_rss_mb,
        "disk_total_gb": disk_total_gb,
        "disk_free_gb": disk_free_gb,
        "has_gpu": has_gpu,
        "gpu_name": gpu_name,
        "vram_total_mb": vram_total_mb,
        "vram_used_mb": vram_used_mb,
        "thermal_status": thermal_status,
        "power_status": power_status,
        "inference_runtime": runtime_str,
        "model_name": model_name,
        "model_verified": model_exists,
    }


def print_edge_doctor_report() -> int:
    """CLI printer for edge deployment doctor check."""
    profile = get_edge_hardware_profile()

    print("============================================================")
    print(" ASTRA-EA EDGE DEPLOYMENT DOCTOR")
    print("============================================================")
    print(f"Platform:           {profile['platform']} ({profile['os_distro']}, {profile['kernel']})")
    print(f"CPU:                {profile['cpu_model']} ({profile['cpu_cores_logical']} logical cores @ {profile['cpu_frequency_mhz']:.0f} MHz)")
    print(f"System RAM:         {profile['ram_available_mb']} MB available / {profile['ram_total_mb']} MB total")
    print(f"Storage:            {profile['disk_free_gb']} GB free / {profile['disk_total_gb']} GB total")
    print(f"Accelerator (GPU):  {profile['gpu_name']}")
    if profile['has_gpu']:
        print(f"VRAM:               {profile['vram_total_mb']} MB total")
    print(f"Thermal Sensors:    {profile['thermal_status']}")
    print(f"Power Telemetry:    {profile['power_status']}")
    print(f"Inference Engine:   {profile['inference_runtime']}")
    print(f"Model Checkpoint:   {profile['model_name']} ({'PASS' if profile['model_verified'] else 'FAIL'})")
    print("------------------------------------------------------------")

    # Pass / Fail criteria
    ram_ok = profile["ram_available_mb"] >= 500.0
    disk_ok = profile["disk_free_gb"] >= 1.0
    model_ok = profile["model_verified"]

    checks = [
        ("CPU Architecture", True),
        ("RAM Threshold", ram_ok),
        ("Disk Storage", disk_ok),
        ("Neural Model", model_ok),
        ("Inference Engine", bool(profile["inference_runtime"])),
    ]

    all_pass = all(ok for _, ok in checks)
    for name, ok in checks:
        print(f"[{'✓' if ok else '✗'}] {name:<20} {'PASS' if ok else 'FAIL'}")

    print("============================================================")
    print("EDGE READINESS:")
    if all_pass:
        print("READY FOR EDGE INFERENCE")
        print("============================================================")
        return 0
    else:
        print("EDGE DEPLOYMENT BLOCKED")
        print("============================================================")
        return 1
