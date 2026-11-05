# Profiling and Benchmarking Framework Architecture

## 1. Multi-Dimensional Latency & Resource Profiling

ASTRA-EA features an integrated, non-intrusive profiler (`PipelineProfiler`) that continuously records fine-grained temporal, throughput, and hardware consumption metrics across all execution phases.

```text
[Camera Capture]
       |
       v
 [Perception] ---> (detection, pose, hands, tracking)
       |
       v
 [Interaction] --> (spatial proximity, contact rules)
       |
       v
  [Activity] ----> (temporal windows, confidence)
       |
       v
  [Evidence] ----> (multimodal evidence synthesis)
       |
       v
 [Procedure] ----> (step matcher, state progress)
       |
       v
 [Assurance] ----> (tri-state deviation & recovery)
       |
       v
[Telemetry/UI] --> (event bus, streaming, GUI)
```

---

## 2. Granular Stage Decomposition

The profiler maintains microsecond-accurate timing buffers across 13 distinct lifecycle stages:

| Stage Identifier | Scope & Measured Operations |
| :--- | :--- |
| `capture` | Sensor ingest latency, USB/V4L2 buffer fetch, OpenCV color conversion. |
| `detection` | Deep neural network or color-spatial candidate proposal forward pass. |
| `pose` | 33-landmark anatomical pose skeleton estimation. |
| `hands` | 21-landmark hand keypoint detection and wrist localization. |
| `tracking` | Multi-object Kalman filter state propagation and Hungarian matching. |
| `interaction` | Spatial bounding box intersection and astronaut hand contact evaluation. |
| `activity` | Temporal sliding window analysis and action hypothesis scoring. |
| `evidence` | Multimodal evidence accumulation against active procedural preconditions. |
| `procedure` | Step transition conditions, timeout monitoring, sequence matching. |
| `assurance` | Tri-State engine evaluation (`VERIFIED`, `UNCERTAIN`, `DEVIATION`). |
| `ui_publish` | Ground telemetry event bus publishing and GUI state updates. |
| `stream` | MJPEG frame encoding and client broadcast delivery. |
| `recording` | Disk persistence, evidence frame compression, and telemetry JSON serialization. |

---

## 3. End-to-End Decision Latency vs Compute Latency

A common misconception in autonomous systems is treating model inference time as end-to-end latency. ASTRA-EA strictly differentiates:

1. **Model Inference Latency**: The forward pass duration of a single neural network (e.g. 4.3 ms).
2. **Compute Latency**: The sum of sequential compute operations across all stages for a frame.
3. **End-to-End Decision Latency ($T_{\text{e2e}}$)**:
   $$T_{\text{e2e}} = t_{\text{assurance\_decision}} - t_{\text{camera\_shutter}}$$
   The elapsed wall-clock duration from physical light striking the optical sensor until the autonomous system produces an immutable assurance verdict.

---

## 4. Statistical Distribution & Percentiles

Reporting solely arithmetic mean latency obscures tail latency spikes caused by garbage collection, scheduling jitter, or thread contention. `PipelineProfiler` calculates:
- **P50 (Median)**: Nominal operational latency experienced by 50% of frames.
- **P90**: Latency ceiling for 90% of frames.
- **P95**: Flight engineering standard operational SLA.
- **P99**: Extreme worst-case outlier threshold.

Percentiles are computed using exact rank-order statistical analysis:
$$\text{Index} = \left\lceil \frac{P}{100} \times N \right\rceil - 1$$

---

## 5. Throughput Separation

Throughput is reported across three independent dimensions:
- **Camera Ingestion FPS**: Rate of raw optical frames ingested from the sensor.
- **Compute Capacity FPS**: Maximum theoretical rate supported by the CPU/GPU compute pipeline ($1000 / \overline{T}_{\text{compute}}$).
- **Effective End-to-End FPS**: Actual delivered rate of fully evaluated assurance decisions.

---

## 6. Queue Depth and Backpressure Monitoring

Every asynchronous processing queue exposes:
- Current queue depth.
- Average queue depth over time.
- Peak observed depth.
- Dropped frame counter.

If queue depth exceeds configured bounds, backpressure telemetry alerts the mission supervisor and degraded mode controller.
