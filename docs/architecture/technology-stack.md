# ASTRA-EA Technology Decisions & Stack Evaluation

## 1. Core Architectural Strategy
ASTRA-EA prioritizes **offline reliability, determinism, bounded resource footprint, and zero cloud lock-in**.

---

## 2. Technology Evaluations

### 2.1 Python 3.11+ (Runtime Environment)
- **Purpose**: Core programming language for orchestration, contracts, logic, and data structures.
- **Reason**: Rich computer vision ecosystem, mature type hinting (`typing`, `dataclasses`), cross-platform support.
- **License**: PSF License (Open Source, Permissive).
- **Offline Compatibility**: 100% offline once installed.
- **Performance**: High productivity; performance-critical loops delegated to C++/CUDA backends (OpenCV, PyTorch, NumPy).

### 2.2 OpenCV (Computer Vision & Video Ingestion)
- **Purpose**: Camera frame capture, video file reading/writing, basic image transforms, overlay drawing.
- **Reason**: Industry-standard, hardware-accelerated, battle-tested camera drivers across USB/MIPI.
- **License**: Apache 2.0.
- **Offline Compatibility**: 100% offline local library.
- **Performance**: Highly optimized SIMD and multithreaded video I/O.

### 2.3 Pydantic v2 (Data Validation & Schemas)
- **Purpose**: Strict runtime validation of experiment YAML configurations, telemetry event schemas, and module contracts.
- **Reason**: High-speed Rust-based core (`pydantic-core`), eliminates silent schema corruption bugs, automatic serialization to JSON/dict.
- **License**: MIT.
- **Offline Compatibility**: 100% offline.
- **Performance**: Negligible latency overhead (< 0.1 ms per event).

### 2.4 SQLite 3 (Audit Database)
- **Purpose**: Structured persistence for mission telemetry, procedural step events, deviation logs, and health status.
- **Reason**: Zero-configuration, serverless, single-file ACID transactional database built directly into the Python standard library.
- **License**: Public Domain.
- **Offline Compatibility**: 100% offline; no background server process required.
- **Performance**: WAL (Write-Ahead Logging) mode allows concurrent reads and high write throughput with minimal storage footprint.

### 2.5 PyYAML (Configuration Parsing)
- **Purpose**: Human-readable, astronaut/scientist-configurable experiment definitions.
- **Reason**: Standard for engineering configurations, easily editable on air-gapped workstations without code changes.
- **License**: MIT.
- **Offline Compatibility**: 100% offline.
- **Performance**: Fast parsing executed during system initialization.

### 2.6 PySide6 / Qt (Ground Demonstrator GUI)
- **Purpose**: High-density, professional space-operations mission console, timeline viewer, and dataset studio.
- **Reason**: Native desktop rendering, hardware GPU acceleration, superior performance and lower memory footprint compared to Electron/web frameworks.
- **License**: LGPLv3 / Commercial.
- **Offline Compatibility**: 100% offline native desktop GUI.
- **Performance**: High 60 FPS rendering with low CPU overhead.

### 2.7 pyttsx3 (Offline Voice Synthesis)
- **Purpose**: Audio guidance and deviation alert vocalization for astronauts.
- **Reason**: Operates directly against local OS speech synthesizers (e.g., `espeak`, `nsss`, SAPI5) without Internet or external cloud APIs.
- **License**: MPL 2.0.
- **Offline Compatibility**: 100% offline.
- **Performance**: Near-instant speech triggering with asynchronous queue management.

### 2.8 pytest (Automated Testing Framework)
- **Purpose**: Unit, integration, and system regression testing.
- **Reason**: Python standard for robust assertions, fixtures, parameterization, and test discovery.
- **License**: MIT.
- **Offline Compatibility**: 100% offline.
- **Performance**: Rapid test execution suite.
