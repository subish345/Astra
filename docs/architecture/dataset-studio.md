# ASTRA-EA Dataset Studio & Training Subsystem Architecture

Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)

---

## 1. System Architecture Overview

Phase 7 establishes the **ASTRA Dataset and Model Development Platform**, providing a disciplined machine learning engineering lifecycle designed specifically for on-board spacecraft experiment verification:

```text
EXPERIMENT DEFINITION (DEMO_EXP_001)
         ↓
DATA INGESTION (Real Session Recording & Seeded Synthetic Generation)
         ↓
DATASET INTEGRITY & ZERO-LEAKAGE VALIDATION
         ↓
SESSION-LEVEL SPLITTING (Train 70% / Val 15% / Test 15%)
         ↓
MODEL TRAINING (RTX 5060 GPU Acceleration & CPU Fallback)
         ↓
HELD-OUT TEST BENCHMARKING (mAP, Confusion Matrix, Latency)
         ↓
MODEL REGISTRY (TRAINING → CANDIDATE → VALIDATED → DEPLOYMENT_CANDIDATE)
         ↓
EMPIRICAL BASELINE-VS-LEARNED COMPARISON
```

---

## 2. Dataset Hierarchy & Directory Layout

```text
datasets/
├── raw/
│   ├── synthetic/           # Procedural scenes with ground-truth bboxes
│   └── real/                # Recorded video sessions (SESSION_001, etc.)
├── annotations/             # JSON ground-truth annotations
├── splits/                  # Session-partitioned manifests (train, val, test)
├── manifests/               # Versioned manifests (ASTRA-DATASET-v0.1.json)
├── versions/                # Dataset version registry
└── reports/                 # Quality, balance, and validation HTML/JSON reports
```

### Critical Rule: Zero Temporal Leakage
Consecutive video frames from a single session or recording are **never** split across train, validation, and test sets. Splitting occurs strictly at session boundaries. The held-out test set is locked and protected from training or hyperparameter tuning.

---

## 3. Model Registry Lifecycle

Every model artifact progresses through a formal state machine:

1. **`TRAINING`**: Model is currently undergoing training epochs.
2. **`CANDIDATE`**: Model has completed training and possesses validation metrics.
3. **`VALIDATED`**: Model has been evaluated on the held-out test split of a versioned dataset with recorded mAP, precision, recall, and confusion data.
4. **`DEPLOYMENT_CANDIDATE`**: Model has outperformed the baseline in side-by-side benchmarking and is approved for active runtime deployment.
5. **`RETIRED`**: Deprecated or superseded model version preserved for archival traceability.

---

## 4. CLI Command Reference

| Command | Purpose |
|---|---|
| `python3 main.py ml doctor` | Diagnoses host GPU, PyTorch version, CUDA runtime, and runs GPU tensor tests. |
| `python3 main.py dataset list` | Lists all versioned datasets registered in the system. |
| `python3 main.py dataset record` | Ingests real camera stream into structured session directory with metadata. |
| `python3 main.py dataset synthesize` | Procedurally renders annotated scenes with controlled lighting and perspective variations. |
| `python3 main.py dataset validate` | Performs image integrity checks and verifies zero cross-split session leakage. |
| `python3 main.py dataset split` | Partitions sessions into train (70%), val (15%), and test (15%). |
| `python3 main.py dataset report` | Generates HTML and JSON class distribution and balance reports. |
| `python3 main.py model list` | Displays model registry status and evaluated metrics. |
| `python3 main.py model train` | Executes training pipeline on target dataset with checkpoint versioning. |
| `python3 main.py model evaluate` | Evaluates model on held-out test set, computing mAP, per-class metrics, and confusion matrix. |
| `python3 main.py model compare` | Direct side-by-side empirical benchmark between Baseline and Learned model. |
| `python3 main.py model validate` | Executes pre-flight sanity checks on model checkpoint artifacts. |
