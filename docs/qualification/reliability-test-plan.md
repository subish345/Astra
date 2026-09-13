# ASTRA-EA: Long-Duration Reliability Qualification Test Plan

**Document ID:** `ASTRA-QTP-REL-001`  
**Test Identifier:** `QUAL-REL-001`  
**Standard:** ECSS-Q-ST-30-02C (Failure Modes, Effects and Criticality Analysis) / IEEE 1413  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Target Duration:** 168 Hours (7 Days Continuous Execution)  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

This qualification test evaluates the continuous long-duration stability, memory integrity, and timing determinism of ASTRA-EA under an uninterrupted 168-hour (1 week) simulated spacecraft mission timeline.

Specific goals:
1. Verify continuous error-free operation without daemon restarts, memory leaks, or file descriptor leaks.
2. Measure long-term parameter drift:
   - **Throughput Drift:** Verify FPS degradation remains $<2.0\%$.
   - **Latency Drift:** Verify P95 decision latency remains within $\pm 5.0\text{ ms}$ of baseline.
   - **Memory Drift:** Verify Resident Set Size (RSS) memory growth remains $<1.0\%$ after initial warm-up.
   - **Storage Rate:** Verify disk consumption rate conforms strictly to the $\le 10.0\text{ MB/s}$ limit.
3. Quantify Mean Time Between Failures ($\text{MTBF}$) for the integrated software pipeline.

---

## 2. Test Setup & Workload Generation

### 2.1 Test Environment
- Continuous run on target edge hardware under controlled temperature ($22^\circ\text{C} \pm 3^\circ\text{C}$).
- Synthetic experiment replay harness generating continuous laboratory interactions, periodic step completions, and induced deviations.

### 2.2 Monitored Health Indicators

| Metric | Target / Baseline | Upper Failure Limit | Sampling Cadence |
| :--- | :---: | :---: | :---: |
| **Pipeline Throughput** | 34.2 FPS | $<30.0\text{ FPS}$ | 10 seconds |
| **Decision Latency (P95)**| 26.4 ms | $>50.0\text{ ms}$ | 10 seconds |
| **System RAM (RSS)** | 448 MB | $>1024\text{ MB}$ | 60 seconds |
| **Open File Descriptors** | 42 | $>256$ | 60 seconds |
| **Silicon Die Temperature**| $58^\circ\text{C}$ | $>80^\circ\text{C}$ | 60 seconds |
| **SQLite WAL Checkpoint** | Every 1000 pages | Unchecked WAL growth | Hourly audit |
| **Unhandled Exceptions** | 0 | $\ge 1$ | Continuous |

---

## 3. Reliability Execution Command

ASTRA-EA supports automated execution of controlled reliability sweeps via the unified CLI:

```bash
astra qualification reliability --duration <seconds>
```

Example for 1-hour verification sweep:
```bash
astra qualification reliability --duration 3600
```

---

## 4. Acceptance Criteria

1. **Uptime:** Zero unhandled process terminations or watchdog forced restarts across 168 hours.
2. **Zero Memory Leaks:** Total RSS memory growth between Hour 2 and Hour 168 is $<1.0\%$.
3. **Deterministic Timing:** Average pipeline FPS remains $\ge 30.0$ FPS throughout the entire run.
4. **Data Integrity:** 100% of generated experiment event runs pass database integrity verification (`PRAGMA integrity_check = ok`).
