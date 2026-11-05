"""Unit tests for YOLOAdapter ONNX parsing, format compatibility, and NMS handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from core.camera.interface import FrameData
from core.perception.detection.yolo_adapter import YOLOAdapter


@pytest.fixture
def mock_onnx_model(tmp_path):
    """Create a temporary dummy weights file."""
    fake_model = tmp_path / "dummy_yolo.onnx"
    fake_model.write_bytes(b"dummy_onnx_content")
    return fake_model


@patch("cv2.dnn.readNetFromONNX")
def test_yolo_adapter_initialization(mock_read_net, mock_onnx_model):
    """Verify clean initialization and CPU fallback without crashing."""
    mock_net = MagicMock()
    mock_read_net.return_value = mock_net

    adapter = YOLOAdapter(
        model_path=mock_onnx_model,
        classes=["ASTRONAUT", "RED_BOX"],
        device="auto",
    )
    assert adapter.classes == ["ASTRONAUT", "RED_BOX"]
    assert "YOLOAdapter" in adapter.model_name
    mock_read_net.assert_called_once_with(str(mock_onnx_model))


@patch("cv2.dnn.readNetFromONNX")
def test_yolo_adapter_v8_anchor_free_decoding(mock_read_net, mock_onnx_model):
    """Verify YOLOv8/v11 anchor-free format: [1, 4 + num_classes, anchors]."""
    mock_net = MagicMock()
    mock_read_net.return_value = mock_net

    # Shape: [1, 6, 2] -> 4 bbox coords + 2 classes, 2 anchors
    # Anchor 0: cx=320, cy=240, w=100, h=100, class0=0.9, class1=0.1
    # Anchor 1: cx=100, cy=100, w=50, h=50, class0=0.2, class1=0.85
    output = np.zeros((1, 6, 2), dtype=np.float32)
    output[0, :, 0] = [320, 240, 100, 100, 0.9, 0.1]
    output[0, :, 1] = [100, 100, 50, 50, 0.2, 0.85]
    mock_net.forward.return_value = output

    adapter = YOLOAdapter(
        model_path=mock_onnx_model,
        classes=["ASTRONAUT", "RED_BOX"],
        confidence_threshold=0.5,
    )

    fake_img = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = FrameData(frame_id=1, image=fake_img, timestamp_mono=100.0, timestamp_wall=100.0, source_id="test_cam")

    detections = adapter.detect(frame)
    assert len(detections) >= 1
    class_names = [d.class_name for d in detections]
    assert "ASTRONAUT" in class_names or "RED_BOX" in class_names


@patch("cv2.dnn.readNetFromONNX")
def test_yolo_adapter_v5_objectness_decoding(mock_read_net, mock_onnx_model):
    """Verify YOLOv5 format: [1, anchors, 5 + num_classes] with objectness."""
    mock_net = MagicMock()
    mock_read_net.return_value = mock_net

    # Shape: [1, 2, 7] -> 4 bbox + 1 objectness + 2 classes
    output = np.zeros((1, 2, 7), dtype=np.float32)
    # Anchor 0: cx=320, cy=240, w=80, h=80, obj=0.95, cls0=0.05, cls1=0.90 -> class 1 score = 0.95 * 0.90 = 0.855
    output[0, 0] = [320, 240, 80, 80, 0.95, 0.05, 0.90]
    output[0, 1] = [10, 10, 20, 20, 0.10, 0.90, 0.10]
    mock_net.forward.return_value = output

    adapter = YOLOAdapter(
        model_path=mock_onnx_model,
        classes=["ASTRONAUT", "RED_BOX"],
        confidence_threshold=0.5,
    )

    fake_img = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = FrameData(frame_id=1, image=fake_img, timestamp_mono=100.0, timestamp_wall=100.0, source_id="test_cam")

    detections = adapter.detect(frame)
    assert len(detections) == 1
    assert detections[0].class_name == "RED_BOX"
    assert detections[0].confidence == pytest.approx(0.855, rel=1e-2)


@patch("cv2.dnn.NMSBoxes")
@patch("cv2.dnn.readNetFromONNX")
def test_yolo_adapter_nms_tuple_return(mock_read_net, mock_nms, mock_onnx_model):
    """Verify that when cv2.dnn.NMSBoxes returns a Python tuple, no AttributeError is raised."""
    mock_net = MagicMock()
    mock_read_net.return_value = mock_net

    output = np.zeros((1, 6, 1), dtype=np.float32)
    output[0, :, 0] = [320, 240, 100, 100, 0.9, 0.1]
    mock_net.forward.return_value = output

    # Simulate OpenCV returning a Python tuple (not ndarray)
    mock_nms.return_value = (0,)

    adapter = YOLOAdapter(
        model_path=mock_onnx_model,
        classes=["ASTRONAUT", "RED_BOX"],
        confidence_threshold=0.5,
    )

    fake_img = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = FrameData(frame_id=1, image=fake_img, timestamp_mono=100.0, timestamp_wall=100.0, source_id="test_cam")

    detections = adapter.detect(frame)
    assert len(detections) == 1
    assert detections[0].class_name == "ASTRONAUT"
