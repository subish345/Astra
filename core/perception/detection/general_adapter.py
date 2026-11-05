"""Offline common-object detection using the existing AstroActAI model."""
from pathlib import Path
import os
import math

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from core.common.config import get_project_root
from core.perception.detection.interface import ObjectDetector
from core.perception.types import BoundingBox, Detection


def filter_detections(detections, width, height, overlap_threshold=0.5):
    """Clip boxes and suppress duplicate same-class results before tracking."""
    kept = []
    for detection in sorted(detections, key=lambda item: item.confidence, reverse=True):
        box = detection.bbox
        if not all(math.isfinite(value) for value in (box.x1, box.y1, box.x2, box.y2, detection.confidence)):
            continue
        detection.bbox = BoundingBox(max(0, box.x1), max(0, box.y1), min(width, box.x2), min(height, box.y2))
        if detection.bbox.area <= 0 or detection.confidence < 0.45:
            continue
        if any(old.class_name == detection.class_name and old.bbox.iou(detection.bbox) >= overlap_threshold for old in kept):
            continue
        kept.append(detection)
    return kept


class GeneralObjectDetector(ObjectDetector):
    def __init__(self):
        root = get_project_root()
        candidates = [
            Path(os.environ.get("ASTRA_OBJECT_MODEL", "models/checkpoints/efficientdet_lite0.tflite")),
            root / "models/checkpoints/efficientdet_lite0.tflite",
            root.parent / "AstroActAi-main/efficientdet_lite0.tflite",
            root.parent / "Codex/AstroActAi-main/efficientdet_lite0.tflite",
        ]
        model = next((p for p in candidates if p.is_file()), None)
        if model is None:
            raise RuntimeError("Live Observe requires efficientdet_lite0.tflite; set ASTRA_OBJECT_MODEL to its local path.")
        self._detector = vision.ObjectDetector.create_from_options(vision.ObjectDetectorOptions(
            base_options=python.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.IMAGE, score_threshold=0.45, max_results=15,
        ))

    def detect(self, frame):
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB))
        result = []
        for item in self._detector.detect(image).detections:
            category = item.categories[0]
            box = item.bounding_box
            result.append(Detection(
                class_name=category.category_name or "unknown object", confidence=category.score,
                bbox=BoundingBox(box.origin_x, box.origin_y, box.origin_x + box.width, box.origin_y + box.height),
                timestamp=frame.timestamp_mono, frame_id=frame.frame_id, source="EFFICIENTDET_LITE0",
            ))
        height, width = frame.image.shape[:2]
        return filter_detections(result, width, height)

    def get_supported_classes(self):
        return ["COCO common objects (not arbitrary tools)"]

    @property
    def model_name(self):
        return "EfficientDet-Lite0"

    def close(self):
        self._detector.close()
