# ASTRA-EA Perception Development Guide

## 1. Perception Configuration
All perception parameters are centralized in `configs/system.yaml`:

```yaml
perception:
  device: "auto"                    # "auto", "cuda", or "cpu"
  detector_backend: "color_spatial" # "color_spatial" or "yolo"
  yolo_model_path: "models/checkpoints/detector.onnx"
  confidence_threshold: 0.45
  iou_threshold: 0.25
  max_lost_frames: 20               # Grace period before dropping occluded tracks
  tracking_interval: 1              # Run tracking every frame
  detection_interval: 1             # Run detector every frame
  pose_interval: 1                  # Run pose estimator every frame
  hand_interval: 1                  # Run hand detector every frame
  quality_interval: 2               # Run quality check every 2 frames
```

---

## 2. CLI Perception Operations

### 2.1 Discover Cameras
```bash
# List local hardware camera devices and probe resolutions
python3 main.py camera list
```

### 2.2 Test Camera Feed
```bash
# Test camera 0 capture and measure frame drops
python3 main.py camera test --source 0 --frames 30
```

### 2.3 Run Live Perception Test
```bash
# Live camera with default color detector and debug overlays
python3 main.py perception test --source 0 --frames 100

# Terminal-only mode (headless)
python3 main.py perception test --source 0 --frames 100 --no-display

# Run against a simulation video file
python3 main.py perception test --source simulation/recordings/demo.mp4 --no-display

# Execute performance benchmarking
python3 main.py perception test --source 0 --frames 100 --benchmark
```

---

## 3. Adding a New Object Detector
To integrate a custom deep-learning model:
1. Export model weights to ONNX format (e.g. `models/checkpoints/custom_detector.onnx`).
2. Implement or subclass `ObjectDetector` in `core/perception/detection/`:
```python
from core.camera.interface import FrameData
from core.perception.detection.interface import ObjectDetector
from core.perception.types import Detection

class MyCustomDetector(ObjectDetector):
    def detect(self, frame: FrameData) -> List[Detection]:
        # Process frame.image with your model
        ...
        return detections
```
3. Register model metadata in `models/configs/custom_detector.yaml`.
4. Point `configs/system.yaml` to the new detector backend.
