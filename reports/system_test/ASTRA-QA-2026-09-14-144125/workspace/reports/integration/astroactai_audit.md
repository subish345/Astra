# TECHNICAL COMPARATIVE AUDIT: ASTROACTAI VS. ASTRA-EA

**Document ID:** `ASTRA-AUDIT-20260913-001`  
**Target Repository:** [`https://github.com/subish345/AstroActAi`](https://github.com/subish345/AstroActAi)  
**Host Baseline:** ASTRA-EA (Autonomous Spacecraft Experiment Assurance & Assistance)  
**Date:** 2026-09-13T22:16:00+05:30  
**Status:** COMPLETED & READY FOR ARCHITECTURAL REVIEW  
**Policy Compliance:** Read-Only Audit. No code modified in ASTRA-EA. No code merged. No files copied.

---

## 1. Executive Summary & Context

The live camera test campaign (`RUN_20260913_220500`) of ASTRA-EA confirmed an operational, high-throughput pipeline (28–30 FPS end-to-end, 332/332 automated tests passing, robust state machines, and verified evidence traceability). However, the real camera visualization revealed significant perceptual weaknesses:
1. **Pose estimation is synthetic:** ASTRA-EA's `LightweightPoseEstimator` uses face/upper-body Haar cascades and geometrically guesses arm/wrist positions proportionally under the face; it cannot track real arm movements, elbows, wrists, hips, or legs.
2. **Hand detection is brittle:** ASTRA-EA's `LightweightHandDetector` relies on YCrCb/HSV skin thresholding and naive frame-splitting (`x < width/2` for left vs. right), frequently losing hands or producing erratic boxes.
3. **Visualization is functional but austere:** Object trails are single-pixel polylines without fading, and hand/pose overlays lack intuitive visual impact.

`AstroActAi` is an edge-native astronaut monitoring script targeting the Bharatiya Antariksh Station (BAS). This audit evaluates whether components from `AstroActAi` can be adapted to solve ASTRA-EA's optical perception and visualization shortcomings without undermining ASTRA-EA's rigorous architectural decoupling, test coverage, or determinism.

---

## 2. Component-by-Component Evaluation Matrix (22 Focus Areas)

Each component is classified into one of five architectural dispositions:
* **`REUSE`**: Directly usable with minimal/no modifications.
* **`ADAPT`**: Concept and core algorithm are high value; wrap into ASTRA-EA's existing abstract interfaces.
* **`REIMPLEMENT`**: Deficient in both repositories; needs clean new implementation in ASTRA-EA.
* **`KEEP ASTRA`**: ASTRA-EA's current implementation is objectively superior; reject AstroActAi's approach.
* **`REJECT`**: Incompatible with flight assurance requirements, low code quality, or anti-pattern.

| # | Focus Component | Current ASTRA-EA | AstroActAi | Classification |
|---|---|---|---|---|
| **1** | **33-Landmark Human Pose** | 9 geometric points estimated from face Haar cascade; arms/elbows do not move with real limbs. | Full 33 3D skeletal landmarks via MediaPipe Tasks `pose_landmarker_lite.task`. | **ADAPT** |
| **2** | **BlazePose/MediaPipe Implementation** | Not present; relies on legacy OpenCV Haar cascades. | MediaPipe Tasks Python API (`vision.PoseLandmarker`) running on CPU/GPU delegate. | **ADAPT** |
| **3** | **Pose Smoothing** | None. | None in Python; single-frame image mode (`detect`) without temporal EMA/OneEuroFilter. | **REIMPLEMENT** |
| **4** | **Human Tracking** | Basic face cascade index (`person_idx + 1`); no re-ID or multi-frame pose continuity. | Single astronaut assumption (`landmarks[0]`); velocity calculated across frames. | **KEEP ASTRA** (Extend) |
| **5** | **Hand Landmark Detection** | YCrCb skin thresholding + contour hull. Fails on gloves, background wood, lighting shifts. | Extracts 4 3D keypoints (wrist, thumb, index, pinky) from PoseLandmarker + palm centroid. | **ADAPT** |
| **6** | **Hand Tracking & Handedness** | Heuristic: Left if $x < \text{width}/2$, Right otherwise. Fails when right hand crosses midline. | Anatomical left/right determined by BlazePose skeleton + horizontal mirror swap map. | **ADAPT** |
| **7** | **Object Detection** | Calibrated `ColorSpatialObjectDetector` + custom ONNX `ASTRA_OBJECT_DETECTOR_v0.1.0` (`RED_BOX`, `YELLOW_BOX`, `MAIN_BOX`). | Generic COCO detector (`efficientdet_lite0.tflite`) with synthetic lookup table mapping. | **KEEP ASTRA** |
| **8** | **Object Tracking** | Mature `MultiObjectTracker`: persistent track IDs, IoU + centroid distance, lost frame buffer, state machine. | No tracking. Detections re-instantiated every frame (`ai_det_0`, `ai_det_1`). | **KEEP ASTRA** |
| **9** | **Spatial Relationships** | Comprehensive `geometry.py`: 3D/2D Euclidean, box overlap IoU, motion correlation vectors. | Hand-to-object centroid distance + palm-to-palm distance for handoff. | **KEEP ASTRA** |
| **10** | **Trajectory/Trail Rendering** | 1-pixel polyline connecting historical centroids (`track.history`). Faint visual impact. | None. No spatial trajectory trail or breadcrumb rendering. | **REIMPLEMENT** |
| **11** | **Activity Recognition** | Multi-tiered: `PrimitiveActionRecognizer` (9 verbs) + `CompositeActivityEngine` + `TemporalBuffer`. | Heuristic dwell thresholding (`DWELL_REQ = 6`) + hardcoded `ROTATE`/`INSERT` logic. | **KEEP ASTRA** |
| **12** | **Temporal Recognition** | Sliding-window `TemporalBuffer` with velocity variance, trajectory smoothness, and contact duration. | Moving string history list (`action_history: List[str]`) with fixed debounce window. | **KEEP ASTRA** |
| **13** | **Coordinate Normalization** | Multi-viewpoint spatial mapping, camera-intrinsic normalization, and normalized $[0, 1]$ bounding. | Screen space $[0, 1]$ + rack-relative offset $(x - 0.5, y - 0.5, z)$. | **KEEP ASTRA** |
| **14** | **Camera Handling** | Clean `CameraSource` abstraction (`WebcamSource`, `VideoFileSource`, `SimulatedCameraSource`), auto-reconnect, FPS accounting. | Raw OpenCV `cv2.VideoCapture` while-loop inside `astronaut_monitor.py`. | **KEEP ASTRA** |
| **15** | **Visualization Quality** | Functional dark HUD, but 9-point skeleton is stiff, hand box is crude, interaction line is basic. | Vibrant glowing 33-joint skeleton, color-coded bone segments, crosshair reticles, laser targeting lines, dwell rings. | **ADAPT** |
| **16** | **Performance & Throughput** | Perception: 15.5 ms, Pipeline P50: 12.38 ms, Throughput: 28.5–30.0 FPS. | Pose Landmarker Lite on CPU: 16.3 ms (60.6 FPS). Object detector: 22.7 ms (43 FPS). | **KEEP ASTRA** |
| **17** | **GPU/CPU Resource Usage** | 15.2% CPU utilization on 28-thread i7-14700HX; stable 300MB RSS memory footprint. | MediaPipe XNNPACK CPU delegate runs efficiently; low memory footprint. | **KEEP ASTRA** |
| **18** | **Dependencies** | OpenCV, NumPy, PyTorch, Torchvision, PySide6, PyYAML, psutil, pyttsx3. | `mediapipe>=1.0.0` (already installed in environment: v1.0.1), `requests`, `fastapi`. | **REUSE** |
| **19** | **Model Licenses** | ONNX weights (custom trained, Apache 2.0). | Google MediaPipe `pose_landmarker_lite.task` (Apache 2.0). Permissive commercial use. | **REUSE** |
| **20** | **Repository License** | Internal/SIH26174 Ground Software. | Subish345 internal repository. Identical author/maintainer ownership. | **REUSE** |
| **21** | **Code Quality & Architecture** | Highly modular, typed dataclasses, 24 test suites, 332 automated unit/integration tests. | Monolithic 2,354-line procedural script (`astronaut_monitor.py`), coupled UI and logic, zero unit tests. | **KEEP ASTRA** |
| **22** | **Integration Complexity** | N/A (Host). | Low-to-Medium if isolated to `PoseEstimator` adapter and `PerceptionVisualizer`. | **ADAPT** |

---

## 3. Deep Technical Comparison: Current ASTRA-EA vs. AstroActAi

### 3.1 Human Pose & Skeleton (Focus Area 1 & 2)

* **Current ASTRA-EA:**
  * File: `core/perception/pose/adapter.py` (`LightweightPoseEstimator`)
  * Implementation: Runs `haarcascade_frontalface_default.xml` or `haarcascade_upperbody.xml`. If a face is found, it synthesizes 9 proportional coordinates:
    ```python
    shoulder_y = cy + 0.9 * head_size
    elbow_y = shoulder_y + 1.2 * head_size
    wrist_y = elbow_y + 1.1 * head_size
    hip_y = shoulder_y + 2.2 * head_size
    ```
  * **Critical Flaw:** Limbs are static mathematical offsets from the head. Real arm articulation, reaching, waving, or gripping is invisible to the pose system.
* **AstroActAi:**
  * File: `astronaut_monitor.py` (`MicrogravityPoseEngine`)
  * Implementation: MediaPipe Tasks `PoseLandmarker` using `pose_landmarker_lite.task` (5.7 MB TFLite model).
  * Measures 33 real 3D keypoints covering shoulders, elbows, wrists, hips, knees, ankles, heels, toes, and facial landmarks.
  * Real measured performance on test host: **P50 Latency: 16.31 ms (~60.6 FPS)** on CPU with XNNPACK delegate.
* **Advantage:** Transforms ASTRA-EA from a toy face-offset skeleton into a real biomechanical tracking system.
* **Disadvantage:** Adds a model file dependency (`pose_landmarker_lite.task`, 5.7 MB).
* **Verdict:** **ADAPT** into `core/perception/pose/mediapipe_adapter.py`.

---

### 3.2 Hand Landmark Detection & Handedness (Focus Area 5 & 6)

* **Current ASTRA-EA:**
  * File: `core/perception/hands/adapter.py` (`LightweightHandDetector`)
  * Implementation: YCrCb + HSV thresholding + contour area filtering.
  * Handedness Logic: `hand_type = HandType.LEFT if palm_cx < frame_center_x else HandType.RIGHT`.
  * **Critical Flaw:** Fails under changing room lighting, produces false positives on cardboard or wood surfaces, cannot detect gloved hands, and inverts left/right whenever hands cross the center of the camera frame.
* **AstroActAi:**
  * File: `astronaut_monitor.py` (lines 972–1045)
  * Implementation: Extracts hand effectors directly from the 33-point pose model (`left_wrist`, `left_index`, `left_pinky`, `left_thumb`). Computes true anatomical palm centroid from wrist and finger clusters.
  * Handedness is true biological anatomical left vs. right, completely invariant to where the astronaut reaches across the screen. Includes horizontal mirror swapping logic (`MIRROR_SWAP_MAP`).
* **Advantage:** Highly robust to lighting, background clutter, and arm crossover. Zero extra compute cost because it reuses pose inferences.
* **Disadvantage:** Only provides 4 keypoints per hand (wrist + 3 finger roots), not full 21-joint finger articulation.
* **Verdict:** **ADAPT** into ASTRA-EA's hand observation model.

---

### 3.3 Object Detection & Tracking (Focus Area 7 & 8)

* **Current ASTRA-EA:**
  * Object Detector: `ColorSpatialObjectDetector` and `YOLOAdapter` pointing to custom ONNX weights (`ASTRA_OBJECT_DETECTOR_v0.1.0.onnx`), trained specifically on experiment boxes: `RED_BOX`, `YELLOW_BOX`, `MAIN_BOX`, and `WORK_SURFACE`.
  * Object Tracker: `MultiObjectTracker` in `core/perception/tracking/tracker.py`. Provides persistent track IDs, spatial IoU matching, state transitions (`ACTIVE`, `TEMPORARILY_LOST`, `RETIRED`), lost-frame tolerance, and position histories.
* **AstroActAi:**
  * Object Detector: `efficientdet_lite0.tflite` (COCO dataset: cup, bottle, cell phone, etc.). Synthesizes mock space payloads through string matching (`SPACE_PAYLOAD_REGISTRY`).
  * Object Tracker: **Non-existent.** Bounding boxes are re-instantiated from scratch every frame with ephemeral IDs (`ai_det_0`, `ai_det_1`). No track persistence, no track loss recovery.
* **Advantage:** ASTRA-EA is vastly superior.
* **Disadvantage:** AstroActAi's object detection pipeline is completely unusable for SIH26174 experiment specifications.
* **Verdict:** **KEEP ASTRA-EA.** Reject AstroActAi's object detector and tracker.

---

### 3.4 Spatial Interactions, Activity & Temporal Reasoning (Focus Area 9, 11, 12)

* **Current ASTRA-EA:**
  * Decoupled architecture:
    * `core/interaction/geometry.py`: Spatial metrics, velocity correlation vectors, IoU bounding.
    * `core/interaction/state_machine.py`: Per-pair `HandObjectStateMachine` (`NONE → APPROACHING → CONTACT → GRASPING → HOLDING → MOVING → RELEASING → RELEASED`).
    * `core/temporal/buffer.py`: Rolling trajectory buffer, variance filtering, duration verification.
    * `core/activity/primitive.py` & `composite.py`: 9 primitive action verbs + compound action composition.
    * `core/procedure/matcher.py`: Multi-modal evidence evaluation against procedure DAGs.
* **AstroActAi:**
  * Hardcoded in a single class `DualHandInteractionClassifier`:
    * Distance threshold check (`d < 0.14`).
    * 6-frame dwell counter (`DWELL_REQ = 6`).
    * Direct payload custody transfer (`left_held_object`, `right_held_object`).
    * Shoulder-based torso roll calculation (`delta_roll > 10.0` for `ROTATE`).
    * String-list debouncer (`action_history: List[str]`).
* **Advantage:** ASTRA-EA has aerospace-grade formal state machines with 100% test coverage; AstroActAi's logic is tightly coupled, non-configurable, and brittle.
* **Valuable Nuance from AstroActAi:** The hand-to-hand custody handoff logic (transferring held state when palm distance $< 0.12$) and torso roll calculation from shoulder angles are clever heuristics that can be ported to ASTRA-EA's `SpatialInteractionEngine`.
* **Verdict:** **KEEP ASTRA-EA** as the architectural core; cherry-pick hand-to-hand transfer and roll heuristics into ASTRA-EA's interaction engine.

---

### 3.5 Visualization & HUD Aesthetics (Focus Area 10 & 15)

* **Current ASTRA-EA:**
  * Functional but dated:
    * Skeleton: Cyan lines connecting 9 face-offset points.
    * Hands: Basic rectangular bounding boxes with text labels.
    * Interaction: Plain colored line between hand and object with distance text.
    * Object Trails: Single 1-pixel polyline through `track.history`.
* **AstroActAi:**
  * Outstanding visual aesthetics:
    * **Glowing 33-Joint Skeleton:** Torso box in emerald green (`0, 230, 118`), left arm in electric magenta (`214, 112, 218`), right arm in neon amber (`0, 165, 255`), head in cyan (`0, 229, 255`).
    * **Concentric Hand Reticles:** Animated crosshairs and reticles on active wrists and palms.
    * **Laser Targeting Guides:** Dynamic cyan/orange guide lines connecting hands to target stations with proximity percentage indicators:
      ```python
      cv2.line(frame, closest_hand_pt, (cx, cy), beam_col, 1, cv2.LINE_AA)
      cv2.circle(frame, (cx, cy), 20, beam_col, 1, cv2.LINE_AA)
      ```
    * **Procedure Step Dots:** Top-right step indicator dots (green = completed, pulsing cyan = active, gray = pending).
* **Trajectory Trail Analysis (Focus Area 10):**
  * Neither repo has true gradient alpha-fading particle trails.
  * ASTRA-EA already maintains `track.history: Deque[Tuple[float, float]]` in `Track`.
  * **Solution:** Reimplement trail rendering in ASTRA-EA by drawing thickness-scaled, alpha-decayed segments from `track.history` (fading from 4px to 1px with glowing color).
* **Advantage:** Adopting AstroActAi's color palette and reticle geometry will elevate ASTRA-EA's visual presentation to modern aerospace HUD standards.
* **Verdict:** **ADAPT** visualization styling into `core/perception/visualizer.py`.

---

## 4. Specific Weak Area Analysis & Impact Assessment

| Weakness Seen in Live Camera Output | Can AstroActAi Materially Improve It? | Technical Explanation | Recommended Action |
|---|---|---|---|
| **Missing / Weak 33-Point Body Pose** | **YES (Massive Improvement)** | Replaces synthetic 9-point Haar cascade with real 33-point 3D BlazePose model running at 16.3 ms on CPU. True limb articulation, elbows, knees, ankles. | **ADAPT** MediaPipe PoseLandmarker into new `MediaPipePoseEstimator` adapter. |
| **Weak Hand Rendering** | **YES (Major Improvement)** | Replaces fragile skin threshold boxes with pose-derived wrist reticles, palm centroids, and finger web lines. | **ADAPT** hand rendering into `PerceptionVisualizer`. |
| **Weak Object Trails** | **PARTIALLY (Needs New Code)** | AstroActAi has NO object trails. However, ASTRA-EA already stores `track.history`. | **REIMPLEMENT** trail renderer in ASTRA-EA with fading alpha and velocity coloring. |
| **Inconsistent Person Detection** | **YES (Major Improvement)** | BlazePose neural network detects whole persons even in partial profile or microgravity tilts, unlike frontal face cascades. | **ADAPT** BlazePose for person bounding. |
| **Inconsistent Object / Evidence State** | **NO (Keep ASTRA-EA)** | AstroActAi's object detection is generic COCO with no tracking. ASTRA-EA's custom models and `AssuranceEngine` are vastly superior. | **KEEP ASTRA-EA.** Do not touch object detection or assurance logic. |
| **Awkward Overlay Visualization** | **YES (Major Improvement)** | AstroActAi's cyber-aerospace HUD design (color-coded limbs, reticles, laser targeting beams, translucent telemetry cards) is visually stunning. | **ADAPT** HUD color palette and overlays into `PerceptionVisualizer`. |

---

## 5. Architectural & Software Engineering Comparison

| Criterion | Current ASTRA-EA | AstroActAi | Architectural Verdict |
|---|---|---|---|
| **Modularity & Decoupling** | High. Strict separation into `camera`, `perception`, `interaction`, `activity`, `procedure`, `assurance`, `storage`, `ui`. | Low. Single 2,354-line script `astronaut_monitor.py` containing camera, AI, logic, UI, and TTS. | **KEEP ASTRA-EA.** Never merge AstroActAi's monolithic file structure. |
| **Testing & Verification** | 24 test suites, 332 automated tests, formal rehearsal framework with 60 test scenarios. | Minimal script tests in `tests/`. No CI/CD regression suite. | **KEEP ASTRA-EA.** All adaptations must maintain 100% test pass rate. |
| **Failure Handling & Degraded Modes** | Explicit fallback chains (`ColorSpatialObjectDetector` fallback, CPU fallback, offline mode). | Basic try/except with logger warnings. | **KEEP ASTRA-EA.** Maintain defensive fallbacks. |
| **Edge Hardware Compatibility** | Pure CPU validated at 28.5 FPS; PyTorch CPU build functional. | MediaPipe XNNPACK CPU verified at 16.3 ms on test laptop. | **COMPATIBLE.** Zero new hardware required. |
| **Dependencies** | Python 3.14+, OpenCV, PyTorch, PySide6. | Requires `mediapipe>=1.0.0`. | **SAFE.** `mediapipe 1.0.1` is already installed in the user's Python environment. |
| **Model Assets & Licensing** | Custom ONNX models under Apache 2.0. | Google MediaPipe `pose_landmarker_lite.task` under Apache 2.0. | **SAFE.** Apache 2.0 permits unrestricted integration and modification. |

---

## 6. Synthesis & Recommended Action Plan

### What to REUSE:
* `pose_landmarker_lite.task` model file (5.7 MB) from Google MediaPipe (Apache 2.0).

### What to ADAPT into ASTRA-EA:
1. **`core/perception/pose/mediapipe_adapter.py`**:
   * Create a new `MediaPipePoseEstimator(PoseEstimator)` implementing ASTRA-EA's standard interface.
   * Ingest frames and emit 33 `Keypoint` instances with true 3D $(x, y, z)$ coordinates.
   * Preserve `LightweightPoseEstimator` (Haar cascades) as an automatic fallback if MediaPipe is unavailable.
2. **`core/perception/hands/mediapipe_adapter.py`**:
   * Extract hand observations directly from the pose landmarks (wrist, thumb, index, pinky, palm centroid).
   * True anatomical left/right hand tracking without image-splitting heuristics.
3. **`core/perception/visualizer.py`**:
   * Upgrade skeleton rendering to use AstroActAi's 33-keypoint color-coded bone segments (emerald torso, magenta left arm, amber right arm).
   * Add concentric hand reticles and laser targeting guides to active experiment containers.

### What to REIMPLEMENT:
1. **Pose Smoothing Filter (`OneEuroFilter` / EMA):**
   * Implement a lightweight exponential moving average or One-Euro filter in `core/perception/pose/smoothing.py` to eliminate high-frequency keypoint jitter.
2. **Dynamic Trajectory Trails:**
   * Upgrade `visualizer.py` to draw multi-segment alpha-fading glowing trails with velocity-based width from `track.history`.

### What to KEEP STRICTLY AS ASTRA-EA (REJECT from AstroActAi):
* **REJECT** AstroActAi's `efficientdet_lite0.tflite` and COCO mock registry. Keep ASTRA-EA's calibrated `ColorSpatialObjectDetector` and custom YOLO ONNX detector.
* **REJECT** AstroActAi's lacks-a-tracker object pipeline. Keep ASTRA-EA's `MultiObjectTracker`.
* **REJECT** AstroActAi's hardcoded procedure FSM. Keep ASTRA-EA's `AssuranceEngine`, `EvidenceEngine`, and YAML procedure DAGs.
* **REJECT** AstroActAi's monolithic script layout. All enhancements must conform to ASTRA-EA's modular design.

---

## 7. Next Steps & User Gate

Per instructions:
> **"DO NOT make any code changes until the audit is reviewed."**

This technical audit is fully finalized and filed in [astroactai_audit.md](file:///home/subish-loq/Documents/astra/reports/integration/astroactai_audit.md).  
Awaiting explicit review and authorization before proposing any implementation plan or code modifications.
