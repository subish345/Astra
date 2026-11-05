# Edge Optimization and Hardware Abstraction Architecture

## 1. Overview and Engineering Philosophy

In spacecraft computing environments, flight avionics are characterized by stringent thermal budgets, radiation-hardened or low-power microprocessors, and tightly partitioned memory regions. High-end workstation GPUs (such as the development laptop's NVIDIA RTX 5060) are development tools, **not** guaranteed flight hardware.

ASTRA-EA adheres to a strict hardware abstraction philosophy:
$$\text{CORRECTNESS} > \text{SAFETY / ASSURANCE BEHAVIOR} > \text{EVIDENCE QUALITY} > \text{STABILITY} > \text{LATENCY} > \text{THROUGHPUT} > \text{RESOURCE EFFICIENCY}$$

1. **Assurance Invariance**: We never sacrifice procedure verification correctness or deviation detection sensitivity to achieve higher FPS.
2. **Deterministic Tri-State Decision**: Computational constraints never turn an `UNCERTAIN` classification into a `DEVIATION` or vice-versa.
3. **Zero Vendor Lock-In**: The core autonomy logic interacts solely with abstract execution backends (`ComputeBackend`) and portable inference runtimes (`InferenceRuntime`).

---

## 2. Compute Backend Abstraction

Hardware devices are decoupled from higher-level perception through the abstract base class `ComputeBackend`:

```text
                  +---------------------------+
                  |      ComputeBackend       |
                  |  (core/optimization/...)  |
                  +-------------+-------------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+---------------+       +---------------+       +---------------+
|  CPUBackend   |       |  CUDABackend  |       |FutureEdgeNPU  |
| (Host x86/ARM)|       | (NVIDIA CUDA) |       | (K230/Coral)  |
+---------------+       +---------------+       +---------------+
```

### Supported Backend Types
- **`CPUBackend`**: Zero-dependency deterministic host CPU execution using native SIMD / OpenCV vectorized kernels. Always available as a rock-solid fallback.
- **`CUDABackend`**: GPU acceleration layer querying PyTorch CUDA streams and `nvidia-smi` hardware telemetry when available, with automatic graceful fallback if CUDA drivers are missing or uninitialized.
- **`FutureEdgeBackend`**: Pluggable interface for specialized low-power edge accelerators (such as Kendryte K230, Hailo-8, Google Coral Edge TPU, or RISC-V vector extensions).

---

## 3. Adaptive Inference Scheduling

Running full neural-network object detection, 33-keypoint 3D body pose estimation, and 21-keypoint dual hand tracking on *every single frame* at 60 FPS is neither necessary nor power-efficient on flight avionics. 

The `AdaptiveInferenceScheduler` coordinates decoupled execution cadences across the pipeline:

```text
Frame t     : [Capture] -> [Tracking] -> [Detection] -> [Hands]  (Full Pass)
Frame t+1   : [Capture] -> [Tracking] ------------> [Cached Obs] (Skip Heavy Pose)
Frame t+2   : [Capture] -> [Tracking] -> [Pose] ----------------> (Interleaved)
```

### Decoupled Cadence Strategy
- **Tracking (1:1)**: High-rate Kalman filter and IoU association runs on every ingested frame to preserve kinematic continuity.
- **Object Detection (1:1 or 1:2)**: Refreshes target bounding boxes (`RED_BOX`, `YELLOW_BOX`, `MAIN_BOX`).
- **Pose Estimation (1:2 or 1:3)**: Interleaved body orientation and astronaut posture tracking.
- **Hand Detection (1:1 or 1:2)**: Critical for immediate contact and grip interaction events.

### Observation Cache with Age-Aware Invalidation
When perception stages are skipped on non-execution frames, the scheduler serves valid cached observations to the interaction and activity engines. If cached observations exceed `max_cache_age_frames` (default: 5 frames), they are automatically invalidated to prevent stale evidence injection.

---

## 4. Latest-Frame Queue Policy

When downstream compute encounters transient backpressure (e.g. storage I/O or garbage collection), naive FIFO queues accumulate latency, causing decisions to fall seconds behind the live optical feed.

ASTRA-EA introduces `LatestFrameQueue`:
- Bounded depth (default: 2 to 5 frames).
- **Drop-Oldest Eviction**: When a new camera frame arrives while the queue is full, the oldest buffered frame is discarded immediately.
- **Guaranteed Low Decision Latency**: Ensures the assurance engine always operates on the freshest physical reality.

---

## 5. Model Inference Runtimes

ASTRA-EA supports dynamic model runtime selection via `RuntimeFactory`:

1. **`OpenCVDNNRuntime`**: Zero-dependency portable ONNX runner executing through OpenCV's DNN C++ backend (`cv2.dnn.readNetFromONNX`). Fully functional on clean CPU setups without installing heavy external runtimes.
2. **`ONNXRuntimeEngine`**: High-performance runtime leveraging Microsoft ONNX Runtime with execution providers (CPUExecutionProvider, CUDAExecutionProvider) and automatic fallback to OpenCV DNN.
3. **`PyTorchRuntime`**: Direct PyTorch tensor forward pass for research and development iteration.

---

## 6. Resource Limits and Degraded Mode

The `BudgetMonitor` evaluates host metrics against configurable thresholds:
- Maximum Process RSS Memory (e.g., 4.0 GB)
- Maximum GPU VRAM Allocation (e.g., 4.0 GB)
- Maximum Host CPU Utilization (e.g., 85%)
- Maximum Queue Depth (e.g., 5 frames)

### Degraded Mode Adaptation
When resource budgets are breached:
1. System transitions to `SYSTEM: DEGRADED`.
2. Non-critical background telemetry (pose estimation interval increased, video stream bitrate reduced).
3. **Assurance Guarantee**: Crucial object detection, wrong-object deviation checking, step transitions, and local immutable disk logging remain fully active.
