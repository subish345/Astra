"""YOLO-family object detector adapter using OpenCV DNN backend.

Supports ONNX weights exported from YOLO architectures with CPU/CUDA execution targets.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np

from core.camera.interface import FrameData
from core.common.logging import get_logger
from core.perception.detection.interface import ObjectDetector
from core.perception.types import BoundingBox, Detection

logger = get_logger("PERCEPTION")


class YOLOAdapter(ObjectDetector):
    """OpenCV DNN runner for YOLO ONNX models."""

    def __init__(
        self,
        model_path: str | Path,
        classes: Optional[List[str]] = None,
        confidence_threshold: float = 0.45,
        nms_threshold: float = 0.45,
        input_size: int = 640,
        device: str = "auto",
    ):
        self.model_path = Path(model_path)
        self.classes = classes or ["ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX"]
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size
        self.device = device.lower()

        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model weights file not found: {self.model_path}")

        logger.info("Loading YOLO ONNX network from %s...", self.model_path)
        self._net = cv2.dnn.readNetFromONNX(str(self.model_path))

        if self.device in ("cuda", "gpu"):
            self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            logger.info("YOLO DNN target set to CUDA.")
        else:
            self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            logger.info("YOLO DNN target set to CPU.")

    def detect(self, frame: FrameData) -> List[Detection]:
        """Run YOLO inference and extract detections."""
        img = frame.image
        orig_h, orig_w = img.shape[:2]

        blob = cv2.dnn.blobFromImage(
            img,
            scalefactor=1.0 / 255.0,
            size=(self.input_size, self.input_size),
            swapRB=True,
            crop=False,
        )
        self._net.setInput(blob)
        outputs = self._net.forward()

        # Handle YOLOv8/v11 output shape [1, 4 + num_classes, num_anchors]
        if len(outputs.shape) == 3 and outputs.shape[1] < outputs.shape[2]:
            outputs = np.transpose(outputs[0], (1, 0))
        elif len(outputs.shape) == 3:
            outputs = outputs[0]

        boxes = []
        confidences = []
        class_ids = []

        x_factor = orig_w / self.input_size
        y_factor = orig_h / self.input_size

        for row in outputs:
            classes_scores = row[4:]
            max_score = float(np.max(classes_scores))
            if max_score >= self.confidence_threshold:
                class_id = int(np.argmax(classes_scores))
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                left = int((cx - 0.5 * w) * x_factor)
                top = int((cy - 0.5 * h) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)

                boxes.append([left, top, width, height])
                confidences.append(max_score)
                class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.nms_threshold)

        detections: List[Detection] = []
        if len(indices) > 0:
            for idx in indices.flatten():
                bx, by, bw, bh = boxes[idx]
                cid = class_ids[idx]
                class_name = self.classes[cid] if cid < len(self.classes) else f"class_{cid}"
                conf = confidences[idx]

                bbox = BoundingBox(
                    x1=float(max(0, bx)),
                    y1=float(max(0, by)),
                    x2=float(min(orig_w, bx + bw)),
                    y2=float(min(orig_h, by + bh)),
                )

                detections.append(
                    Detection(
                        class_name=class_name,
                        confidence=round(conf, 3),
                        bbox=bbox,
                        timestamp=frame.timestamp_mono,
                        frame_id=frame.frame_id,
                        source="YOLO_ONNX",
                    )
                )

        return detections

    def get_supported_classes(self) -> List[str]:
        return list(self.classes)

    @property
    def model_name(self) -> str:
        return f"YOLOAdapter({self.model_path.name})"
