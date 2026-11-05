"""Inference Runtime Abstraction for ASTRA-EA Model Execution.

Supports multiple runtime engines:
1. OpenCVDNNRuntime: Zero-dependency portable ONNX runner via OpenCV DNN.
2. ONNXRuntimeEngine: High-performance onnxruntime execution (if installed).
3. PyTorchRuntime: PyTorch tensor execution (if installed).

Allows dynamic configuration and seamless fallback across heterogeneous compute environments.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.common.logging import get_logger
from core.optimization.backend import ComputeBackend, PlatformInspector

logger = get_logger("OPTIMIZATION")


class InferenceRuntime(ABC):
    """Abstract model inference execution runtime."""

    @property
    @abstractmethod
    def runtime_name(self) -> str:
        """Name of the active execution runtime."""
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Whether model weights are loaded and ready for inference."""
        ...

    @abstractmethod
    def load(self, model_path: str | Path) -> bool:
        """Load model file into memory."""
        ...

    @abstractmethod
    def predict(self, image: np.ndarray) -> np.ndarray:
        """Execute forward inference on input image and return raw output tensor."""
        ...

    @abstractmethod
    def get_latency_stats(self) -> Dict[str, Any]:
        """Return load and inference timing metrics."""
        ...


class OpenCVDNNRuntime(InferenceRuntime):
    """Zero-dependency ONNX model runner using OpenCV's DNN module."""

    def __init__(
        self,
        input_size: Tuple[int, int] = (640, 640),
        backend: Optional[ComputeBackend] = None,
    ) -> None:
        self.input_size = input_size
        self.backend = backend or PlatformInspector.create_backend()
        self._net: Optional[cv2.dnn.Net] = None
        self._model_path: Optional[Path] = None
        self._load_duration_ms: float = 0.0
        self._inference_times_ms: List[float] = []

    @property
    def runtime_name(self) -> str:
        return "OpenCVDNN_ONNX"

    @property
    def is_loaded(self) -> bool:
        return self._net is not None

    def load(self, model_path: str | Path) -> bool:
        path = Path(model_path)
        if not path.exists():
            logger.error("ONNX model file not found: %s", path)
            return False

        t0 = time.perf_counter()
        try:
            self._net = cv2.dnn.readNetFromONNX(str(path))
            self._model_path = path

            # Configure OpenCV target device
            if self.backend.is_accelerated:
                try:
                    self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                    self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                    logger.info("Configured OpenCV DNN for CUDA acceleration.")
                except Exception as e:
                    logger.warning("CUDA DNN failed (%s), using CPU target.", e)
                    self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            else:
                self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

            self._load_duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.info("Loaded ONNX model via OpenCV DNN in %.2f ms", self._load_duration_ms)
            return True
        except Exception as exc:
            logger.error("Failed to load ONNX model via OpenCV DNN: %s", exc)
            self._net = None
            return False

    def predict(self, image: np.ndarray) -> np.ndarray:
        if self._net is None:
            raise RuntimeError("Model is not loaded in OpenCVDNNRuntime.")

        t0 = time.perf_counter()
        # Create standard 4D blob: NCHW, normalized 1/255.0, RGB format
        blob = cv2.dnn.blobFromImage(
            image,
            scalefactor=1.0 / 255.0,
            size=self.input_size,
            swapRB=True,
            crop=False,
        )
        self._net.setInput(blob)
        out = self._net.forward()
        dur = (time.perf_counter() - t0) * 1000.0
        self._inference_times_ms.append(dur)
        return out

    def get_latency_stats(self) -> Dict[str, Any]:
        n = len(self._inference_times_ms)
        mean_lat = (sum(self._inference_times_ms) / n) if n > 0 else 0.0
        return {
            "runtime": self.runtime_name,
            "load_time_ms": round(self._load_duration_ms, 2),
            "inference_count": n,
            "mean_inference_ms": round(mean_lat, 3),
            "min_inference_ms": round(min(self._inference_times_ms), 3) if n > 0 else 0.0,
            "max_inference_ms": round(max(self._inference_times_ms), 3) if n > 0 else 0.0,
        }


class ONNXRuntimeEngine(InferenceRuntime):
    """High-performance runtime using onnxruntime library, with OpenCV DNN fallback."""

    def __init__(
        self,
        input_size: Tuple[int, int] = (640, 640),
        backend: Optional[ComputeBackend] = None,
    ) -> None:
        self.input_size = input_size
        self.backend = backend or PlatformInspector.create_backend()
        self._session: Any = None
        self._input_name: str = "images"
        self._load_duration_ms: float = 0.0
        self._inference_times_ms: List[float] = []
        self._fallback_cv: Optional[OpenCVDNNRuntime] = None

    @property
    def runtime_name(self) -> str:
        if self._session is not None:
            return "ONNXRuntime_Native"
        return "ONNXRuntime_OpenCV_Fallback"

    @property
    def is_loaded(self) -> bool:
        return self._session is not None or (self._fallback_cv is not None and self._fallback_cv.is_loaded)

    def load(self, model_path: str | Path) -> bool:
        t0 = time.perf_counter()
        try:
            import onnxruntime as ort  # type: ignore
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if self.backend.is_accelerated else ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(str(model_path), providers=providers)
            self._input_name = self._session.get_inputs()[0].name
            self._load_duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.info("Loaded model via native ONNXRuntime in %.2f ms", self._load_duration_ms)
            return True
        except ImportError:
            logger.info("onnxruntime package not installed. Using portable OpenCVDNNRuntime fallback.")
            self._fallback_cv = OpenCVDNNRuntime(input_size=self.input_size, backend=self.backend)
            ok = self._fallback_cv.load(model_path)
            self._load_duration_ms = self._fallback_cv._load_duration_ms
            return ok
        except Exception as e:
            logger.warning("Native ONNXRuntime loading failed: %s. Using OpenCVDNNRuntime fallback.", e)
            self._fallback_cv = OpenCVDNNRuntime(input_size=self.input_size, backend=self.backend)
            return self._fallback_cv.load(model_path)

    def predict(self, image: np.ndarray) -> np.ndarray:
        if self._session is not None:
            t0 = time.perf_counter()
            resized = cv2.resize(image, self.input_size)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            normalized = rgb.astype(np.float32) / 255.0
            # Transpose HWC to NCHW
            tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]
            outputs = self._session.run(None, {self._input_name: tensor})
            dur = (time.perf_counter() - t0) * 1000.0
            self._inference_times_ms.append(dur)
            return outputs[0]
        elif self._fallback_cv is not None:
            return self._fallback_cv.predict(image)
        raise RuntimeError("No model loaded in ONNXRuntimeEngine.")

    def get_latency_stats(self) -> Dict[str, Any]:
        if self._fallback_cv is not None:
            return self._fallback_cv.get_latency_stats()
        n = len(self._inference_times_ms)
        mean_lat = (sum(self._inference_times_ms) / n) if n > 0 else 0.0
        return {
            "runtime": self.runtime_name,
            "load_time_ms": round(self._load_duration_ms, 2),
            "inference_count": n,
            "mean_inference_ms": round(mean_lat, 3),
        }


class RuntimeFactory:
    """Factory creating configured inference runtime engines."""

    @staticmethod
    def create(
        runtime_type: str = "auto",
        input_size: Tuple[int, int] = (640, 640),
        backend: Optional[ComputeBackend] = None,
    ) -> InferenceRuntime:
        rt = runtime_type.lower()
        if rt == "opencv_dnn":
            return OpenCVDNNRuntime(input_size=input_size, backend=backend)
        elif rt in ("onnx", "onnxruntime"):
            return ONNXRuntimeEngine(input_size=input_size, backend=backend)
        else:  # auto
            return ONNXRuntimeEngine(input_size=input_size, backend=backend)
