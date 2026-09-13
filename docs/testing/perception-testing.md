# ASTRA-EA Perception Testing & Verification Guide

## 1. Testing Strategy

The perception testing strategy enforces three layers of verification:
1. **Unit Testing:** Validates data contracts, quality scoring, device resolution, tracking mathematics, and scheduler intervals in complete isolation without hardware dependencies.
2. **Deterministic Mock Integration:** Validates that the full pipeline (`CameraSource` $\to$ `Detector` $\to$ `Pose` $\to$ `Hands` $\to$ `Tracker` $\to$ `PerceptionState` $\to$ `EventBus`) produces compliant states using synthetic frames.
3. **Hardware / Video Benchmark:** Instruments real frame capture on physical hardware or recorded video, calculating P50/P95/P99 latencies and FPS throughput.

---

## 2. Running Automated Tests

```bash
# Run all perception tests
python3 -m pytest tests/ -k perception -v

# Run full project test suite
python3 -m pytest tests/ -v
```

---

## 3. Anti-Hallucination & Honest Benchmarking Standards

- **No Fabricated Accuracies:** When profiling inference throughput, the benchmark report clearly displays:
  ```text
  Model Accuracy: NOT EVALUATED (Requires ground-truth annotated dataset)
  ```
  Fabricating mAP or accuracy percentages without an annotated test split is strictly forbidden under project rules.
- **Deterministic Test Doubles:** Stubs used in tests explicitly tag outputs with `source = "TEST MOCK"` or `source = "STUB"`.
