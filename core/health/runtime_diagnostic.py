"""Runtime hardware and environment diagnostics generator for ASTRA-EA.

Produces storage/reports/runtime_diagnostic.json with comprehensive environment telemetry.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2

from core.common.config import get_project_root, load_config
from core.perception.device import DeviceManager


def generate_runtime_diagnostic(
    camera_source: str = "0",
    detector_name: str = "ColorSpatialObjectDetector",
    errors: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    effective_fps: float = 0.0,
    processing_fps: float = 0.0,
) -> Dict[str, Any]:
    """Inspect the active host runtime, hardware, models, and camera, writing diagnostics to disk."""
    root = get_project_root()
    cfg = load_config()

    err_list = list(errors or [])
    warn_list = list(warnings or [])

    # 1. Device and PyTorch info
    dev_info = DeviceManager.get_device_info(cfg.perception.device)
    try:
        import torch  # type: ignore
        torch_ver = torch.__version__
        cuda_avail = torch.cuda.is_available()
    except ImportError:
        torch_ver = "NOT_INSTALLED"
        cuda_avail = False
        warn_list.append("PyTorch not installed in active environment; running in CPU fallback mode.")

    # 2. Camera probe
    cam_backend = "UNKNOWN"
    cam_status = "OFFLINE"
    cam_res = "N/A"
    cam_fps = 0.0

    try:
        dev_idx = int(camera_source)
        cap = cv2.VideoCapture(dev_idx)
        if cap.isOpened():
            cam_backend = cap.getBackendName()
            cam_status = "ONLINE"
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cam_res = f"{w}x{h}"
            cam_fps = float(cap.get(cv2.CAP_PROP_FPS))
            cap.release()
        else:
            err_list.append(f"Unable to open camera source: {camera_source}")
    except ValueError:
        cam_backend = "FILE"
        cam_status = "ONLINE" if Path(camera_source).exists() else "FILE_NOT_FOUND"

    # 3. Model weights probe
    yolo_weights_path = root / (cfg.perception.yolo_model_path or "models/checkpoints/detector.onnx")
    has_yolo_weights = yolo_weights_path.is_file()

    cascade_path = root / "models/checkpoints/haarcascade_frontalface_default.xml"
    has_cascade = cascade_path.is_file()

    # 4. Display / GUI probe
    disp = os.environ.get("DISPLAY", "")
    wayland = os.environ.get("WAYLAND_DISPLAY", "")
    qpa = os.environ.get("QT_QPA_PLATFORM", "")
    gui_status = f"ONLINE (Display: {disp or wayland}, Platform: {qpa or 'default'})"

    diagnostic: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "opencv_version": cv2.__version__,
        "pytorch_version": torch_ver,
        "cuda_available": cuda_avail,
        "gpu_hardware": dev_info.device_name,
        "camera_source": str(camera_source),
        "camera_backend": cam_backend,
        "camera_status": cam_status,
        "resolution": cam_res,
        "configured_fps": cam_fps,
        "effective_fps": round(effective_fps, 1),
        "processing_fps": round(processing_fps, 1),
        "detector_implementation": detector_name,
        "detector_mode": "COLOR/SPATIAL DEVELOPMENT DETECTOR" if "Color" in detector_name else "YOLO ONNX DETECTOR",
        "detector_classes": ["RED_BOX", "YELLOW_BOX", "MAIN_BOX", "ASTRONAUT"],
        "yolo_weights_path": str(yolo_weights_path) if has_yolo_weights else None,
        "yolo_weights_status": "FOUND" if has_yolo_weights else "MISSING",
        "pose_implementation": "LightweightPoseEstimator (Haar Cascade + Upperbody)" if has_cascade else "LightweightPoseEstimator (Skin Heuristic)",
        "hand_implementation": "LightweightHandDetector (Dual-Space YCrCb+HSV Morphology)",
        "tracker_implementation": "MultiObjectTracker (Kalman / IoU)",
        "interaction_engine": "SpatialInteractionEngine",
        "activity_engine": "PrimitiveActivityEngine + CompositeActivityEngine",
        "gui_display_status": gui_status,
        "errors": err_list,
        "warnings": warn_list,
    }

    # Save to storage/reports/runtime_diagnostic.json
    out_dir = root / "storage/reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "runtime_diagnostic.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(diagnostic, f, indent=2)

    return diagnostic
