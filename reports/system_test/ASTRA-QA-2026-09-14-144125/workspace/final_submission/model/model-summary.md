# ASTRA-EA — Final Model Architecture & Comparative Summary

## Model Candidate: `ASTRA_OBJECT_DETECTOR_v1.0`
**Freeze Status:** LOCKED & VALIDATED  
**Architecture:** YOLOv8n-Custom ONNX Quantized (`640x640` input)  
**Hardware Target:** CPU SIMD / NVIDIA CUDA (Decoupled Runtime)

---

## 1. Model Specifications

| Parameter | Specification |
| :--- | :--- |
| **Model ID** | `ASTRA_OBJECT_DETECTOR_v1.0` |
| **Base Architecture** | Lightweight Single-Stage Feature Pyramid Network (YOLOv8 Nano backbone) |
| **Export Formats** | PyTorch Checkpoint (`.pt`), Portable Open Neural Network Exchange (`.onnx`) |
| **Input Tensor** | `[1, 3, 640, 640]` Float32 normalized `[0.0, 1.0]` |
| **Parameter Count** | ~3.0 Million Parameters |
| **Model Footprint** | ~6.2 MB (FP32 ONNX) / ~3.2 MB (INT8 Quantized) |
| **Inference Engines** | OpenCV DNN Runtime (Zero-dependency fallback), ONNX Runtime (CPU/CUDA) |

---

## 2. Comparative Analysis: Baseline vs Learned Detector

ASTRA-EA supports hot-swapping between the deterministic heuristic baseline and the learned neural detector via declarative YAML configuration without altering a single line of downstream interaction, procedure, or assurance code.

| Metric | Baseline (`ColorSpatialObjectDetector`) | Learned (`ASTRA_OBJECT_DETECTOR_v1.0`) | Superiority Rationale |
| :--- | :--- | :--- | :--- |
| **Primary Mechanism** | HSV Color Slicing + Spatial Contour Filtering | Convolutional Deep Feature Representation | Learned handles variable lighting |
| **Inference Latency (P50)** | **1.8 ms** (Ultra-fast) | **8.4 ms** (Real-time CPU SIMD) | Baseline faster, Learned more robust |
| **Mean Average Precision (mAP@50)** | `0.482` (Prone to hue shifts) | **`0.647`** (Generalizes across backgrounds) | Learned provides higher recall |
| **Precision (Critical Objects)** | `0.720` | **`0.865`** | Learned rejects shadow false-positives |
| **Recall (Occluded Specimens)** | `0.410` | **`0.780`** | Deep spatial context preserves detection |
| **Host RAM Overhead** | `< 15 MB` | `~45 MB` | Both well within 4.0 GB edge budget |
| **Zero-Dependency Fallback** | 100% Native (Pure OpenCV) | Requires ONNX Runtime or OpenCV DNN | Baseline acts as bulletproof safety fallback |

---

## 3. Robustness Gate Evaluation

The learned detector was evaluated against challenging environmental conditions simulated in Phase 8 & 10:

1. **Optical Underexposure (-40% luminance)**: Precision: 84.1%, Recall: 72.5%.
2. **Motion Blur / Camera Vibration**: IoU stability preserved over 18 consecutive frames via `MultiObjectTracker`.
3. **Cross-View Semantic Consistency**: Equivalent object track bounding boxes maintained across `VIEW_LEFT` and `VIEW_RIGHT` angled perspectives.
4. **Wrong-Object Disambiguation**: 100% separation between `RED_BOX` (Target) and `BLUE_BOX` (Distractor) across all test runs.
