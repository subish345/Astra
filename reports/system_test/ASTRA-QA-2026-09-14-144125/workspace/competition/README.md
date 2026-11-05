# ASTRA-EA: Competition Package & Operator Defense Suite

**Project:** Autonomous Spacecraft Experiment Assurance & Assistance (ASTRA-EA)  
**Track:** SIH26174 — AI Human Activity Recognition for On-board BAS Experiments  
**Build:** `ASTRA-EA-COMPETITION-RC1`  
**System State:** **FEATURE FREEZE ACTIVE**

---

## 1. Executive Summary

This directory contains the operational runbooks, technical defense dossiers, judge presentation materials, model/dataset cards, and system verification utilities for the live Smart India Hackathon (SIH) competition demonstration.

ASTRA-EA is an **engineering-grade ground demonstrator (TRL 4)** providing offline, vision-based experiment assurance for astronauts aboard the Bharatiya Antariksh Station (BAS).

---

## 2. Directory Layout

```text
competition/
├── README.md                  # This document
├── QUICK_START.md             # One-page fast setup guide for new operators
├── OPERATOR_MANUAL.md         # Comprehensive hands-on operational runbook
├── QUICK_REFERENCE_CARD.md    # 1-page pocket reference & emergency matrix
├── ARCHITECTURE.md            # Decoupled system architecture reference
├── SIH_TRACEABILITY.md        # Full requirement-to-evidence compliance matrix
├── DEMO_SCRIPT.md             # Timed 5–8 minute judge presentation narrative
├── TROUBLESHOOTING.md         # Fast live-demonstration recovery playbook
├── FAQ.md                     # Categorized judge question database & defense
├── MODEL_CARD.md              # Standardized model card (ASTRA_OBJECT_DETECTOR_v1.0)
├── DATASET_CARD.md            # Dataset card & composition (ASTRA-DATASET-v1.0)
├── LIMITATIONS.md             # Explicit engineering disclosures & claim boundaries
├── HARDWARE_CHECKLIST.md      # Physical equipment packing & pre-flight checklist
├── BENCHMARKS/                # Latency, throughput, soak, and model benchmarks
├── SCREENSHOTS/               # 12 high-resolution UI and HUD operational views
├── VIDEOS/                    # 7 live demonstration video clips + manifest
├── REPORTS/                   # Simulation, streaming, and diagnostic reports
├── CHECKSUMS/                 # SHA-256 integrity verification hashes
└── slides/                    # Structured 12-slide competition presentation deck
```

---

## 3. Core Commands Quick Reference

| Action | Command | Expected Result |
| :--- | :--- | :--- |
| **Comprehensive Readiness** | `astra competition-check` | Verifies 15/15 subsystems $\to$ `STATUS: READY` |
| **Hardware Health Audit** | `astra final-check` | Verifies 13/13 subsystems $\to$ `READY FOR DEMONSTRATION` |
| **Live Flight Demo** | `astra demo` | Launches Mission Console & Ground Monitor |
| **Headless CI Demo** | `astra demo --headless` | Non-GUI deterministic test run |
| **Verify Integrity** | `sha256sum -c competition/CHECKSUMS/SHA256SUMS` | Validates all frozen artifacts |
