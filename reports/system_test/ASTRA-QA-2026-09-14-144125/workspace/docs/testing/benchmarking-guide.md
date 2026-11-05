# Benchmarking & Performance Validation Guide

## 1. Overview

This document outlines the standard operational procedures for benchmarking, profiling, soak testing, and validating model optimizations in ASTRA-EA.

All benchmark commands produce both human-readable console summaries and structured, machine-parsable JSON reports stored in `storage/reports/benchmark/`.

---

## 2. Core Benchmark Commands

### A. Recording Baseline Benchmark (Unoptimized)
Before making architectural or model changes, record the unoptimized baseline:
```bash
python3 main.py benchmark baseline --frames 60
```
- **Output Report**: `storage/reports/benchmark/baseline_benchmark.json`
- Measures all 13 pipeline stages at 1:1 cadence (every stage running on every frame).

### B. Running Profiled Benchmark
To benchmark the system under specific deployment profiles and adaptive schedulers:
```bash
# Balanced operational profile
python3 main.py benchmark run --profile balanced --frames 60

# Real-time high-throughput profile
python3 main.py benchmark run --profile realtime --frames 60

# Ultra-low resource profile
python3 main.py benchmark run --profile low_resource --frames 60
```
- **Output Report**: `storage/reports/benchmark/benchmark_report.json`

### C. Precision & Resolution Experiments
Evaluate model trade-offs across input resolutions (640x640, 320x320, 224x224) and precision modes:
```bash
python3 main.py benchmark optimize
```
Enforces the **Critical Safety Quality Gate**: checks whether `RED_BOX` or `YELLOW_BOX` recall degrades, or if red/yellow cross-confusion exceeds 5%.

---

## 3. Endurance Soak & Memory Stability Testing

To verify thermal stability and ensure absence of memory leaks during long-duration runs:
```bash
# Development verification run (10 to 60 seconds)
python3 main.py benchmark soak --duration 10 --fps 30

# Full flight qualification soak run (e.g. 1 hour)
python3 main.py benchmark soak --duration 3600 --fps 30
```
- **Output Report**: `storage/reports/benchmark/soak_report.json`

### Leak Detection Criteria
- Telemetry samples process RSS memory once per second.
- Compares post-warmup startup RSS against shutdown RSS.
- Flags memory leaks if the memory growth slope exceeds **5 MB/min** and net RSS delta exceeds **15 MB**.
- Flags thermal throttling if FPS degrades by more than 25% between early and late test intervals.

---

## 4. ONNX Model Export & Validation

### Export Checkpoint to ONNX
```bash
python3 main.py model export --format onnx
```
- Output: `models/checkpoints/ASTRA_OBJECT_DETECTOR_v0.1.0.onnx`
- Generates YOLOv8-compatible tensor layout: $[1, 9, 8400]$ (4 coordinates + 5 classes).

### Validate Exported Model
```bash
python3 main.py model validate-export
```
Validates:
1. ONNX protobuf integrity (`onnx.checker.check_model`).
2. OpenCV DNN runtime loading (`cv2.dnn.readNetFromONNX`).
3. Forward pass execution and inference latency.
4. Absence of `NaN` or `Inf` floating point values.

### Generate Hardware Compatibility Matrix
```bash
python3 main.py model compatibility
```
- Output: `storage/reports/benchmark/model_compatibility_report.json`
- Tests models across CPU, CUDA, and ONNX execution targets.
