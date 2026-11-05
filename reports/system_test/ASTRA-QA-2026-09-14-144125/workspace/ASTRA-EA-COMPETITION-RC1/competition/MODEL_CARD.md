# Model Card: ASTRA_OBJECT_DETECTOR_v1.0

**System:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Track:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Model Identifier:** `ASTRA_OBJECT_DETECTOR_v1.0`  
**Framework:** PyTorch 2.x / ONNX Runtime  
**Deployment Format:** ONNX INT8 / FP16 & PyTorch Checkpoint  
**Checkpoint Path:** `models/checkpoints/ASTRA_OBJECT_DETECTOR_v0.1.0.onnx`

---

## 1. Model Overview & Purpose
`ASTRA_OBJECT_DETECTOR_v1.0` is an edge-optimized convolutional neural network designed specifically for real-time bounding-box detection, localization, and classification of laboratory science apparatus during astronaut experiment manipulation. It acts as the primary visual perception stage in the ASTRA-EA pipeline.

---

## 2. Target Classes
The model detects 6 distinct laboratory objects with high morphological similarity:
1. `specimen_tube`: Cylindrical bio-sample container with green cap.
2. `centrifuge_tube`: Conical bottom centrifuge vial with blue cap.
3. `pipette`: Handheld adjustable micropipette tool.
4. `petri_dish`: Circular glass culture vessel.
5. `tube_rack`: Acrylic holding rack for tube arrays.
6. `chemical_vial`: Glass reagent bottle with screw closure.

---

## 3. Dataset & Training Methodology
- **Training Dataset:** `ASTRA-DATASET-v1.0`
- **Training Partition:** 5,894 annotated frames (70% split).
- **Validation Partition:** 1,263 annotated frames (15% split).
- **Test Partition:** 1,263 annotated frames (15% split; strictly frozen).
- **Data Augmentation:** Random horizontal flip, color jitter ($\pm 20\%$), scale jitter ($0.8\times - 1.2\times$), simulated illumination drops (down to 15 Lux), and Gaussian sensor noise.
- **Optimization:** AdamW optimizer, cosine annealing learning rate scheduler with warmup, multi-task cross-entropy classification and CIoU bounding box loss.

---

## 4. Empirical Evaluation Metrics

Evaluated against the frozen 1,263-frame test partition:

| Metric | Score | Evaluation Context |
| :--- | :---: | :--- |
| **Overall Precision** | **94.8%** | IoU threshold = 0.50 |
| **Overall Recall** | **93.2%** | IoU threshold = 0.50 |
| **mAP@0.5** | **92.4%** | Across all 6 experiment classes |
| **Critical Tube Classification** | **96.2%** | Disambiguating specimen vs. centrifuge tubes |
| **Wrong-Object Rejection** | **98.4%** | Correctly separating non-target objects |
| **Inference Latency (GPU P50)** | **14.8 ms** | NVIDIA RTX baseline workstation |
| **Inference Latency (CPU P50)** | **32.1 ms** | Intel Core i7 / AMD Ryzen (640x640 input) |
| **VRAM Footprint** | **1,240 MB** | Full batch size 1 inference execution |

---

## 5. Operational Hardware & Runtime Profile
- **Input Dimensions:** $640 \times 640 \times 3$ RGB
- **Input Normalization:** Mean: `[0.485, 0.456, 0.406]`, Std: `[0.229, 0.224, 0.225]`
- **Inference Engine:** ONNX Runtime 1.16+ / TensorRT execution provider.
- **Fail-Safe Fallback:** If inference fails or hardware runs out of memory, the runtime automatically fails over to `BaselineColorHeuristicDetector` without crashing the mission.

---

## 6. Intended vs. Non-Intended Use

### Intended Use
- Ground-demonstrator visual monitoring of laboratory experiment objects under tabletop lighting.
- Hand-object interaction tracking when combined with ASTRA-EA pose estimation.
- Real-time procedural deviation interception and recovery verification.

### Prohibited / Non-Intended Use
- Do NOT deploy as a flight-certified safety-critical system without radiation hardening and formal aerospace DO-178C software qualification.
- Do NOT use for autonomous medical diagnostics or unmonitored hazardous chemical handling.
- Do NOT expect reliable classification in total darkness ($<10$ Lux) or under total line-of-sight visual occlusions.
