# ASTRA-EA: Thermal Qualification Test Plan

**Document ID:** `ASTRA-QTP-THM-001`  
**Test Identifier:** `QUAL-THM-001`  
**Standard:** ECSS-E-ST-10-03C §5.4 / MIL-STD-810H Method 501.7 & 502.7  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

The thermal qualification program verifies that ASTRA-EA compute hardware, optical sensors, storage media, and software algorithms execute reliably across ambient temperature extremes without thermal throttling, unrecoverable crashes, or measurement distortion.

Specific goals:
1. Verify system cold-boot and camera initialization at minimum operating temperature ($-10^\circ\text{C}$).
2. Verify sustained 30.0 FPS pipeline inference and decision latency $\le 50.0$ ms across continuous thermal cycles.
3. Quantify thermal margins and verify that dynamic thermal throttling does not trigger below $+50^\circ\text{C}$ ambient.
4. Verify graceful software shutdown and clean power-off under elevated temperatures.
5. Verify non-volatile data retention and SQLite WAL database consistency post-test.

---

## 2. Test Configuration & Setup

### 2.1 Environmental Test Chamber
- **Chamber Type:** Programmable thermal test chamber with forced-air convective circulation.
- **Temperature Range:** $-20^\circ\text{C}$ to $+70^\circ\text{C}$ chamber capability.
- **Ramp Rate:** Controlled at $\le 1.0^\circ\text{C}/\text{minute}$ to avoid thermal shock.
- **Chamber Atmosphere:** Standard atmospheric pressure (dry nitrogen purge recommended below $+5^\circ\text{C}$ to prevent moisture condensation).

### 2.2 Device Under Test (DUT)
- ASTRA-EA compute module in flight-representative aluminum enclosure.
- Overhead optical camera mounted on calibrated fixture inside chamber.
- Isolated DC power harness and external monitoring cabling routed via chamber feedthrough.

### 2.3 Instrumentation Plan

| Instrument / Sensor | Location | Measurement Parameter | Sampling Rate |
| :--- | :--- | :--- | :---: |
| **Thermocouple TC-01** | Chamber internal air | Ambient chamber temperature | 1 Hz |
| **Thermocouple TC-02** | Compute chassis external plate | Case conduction temperature | 1 Hz |
| **Thermocouple TC-03** | Camera lens barrel & housing | Optical sensor temperature | 1 Hz |
| **Thermocouple TC-04** | NVMe storage drive heatsink | Storage media temperature | 1 Hz |
| **Internal On-Die Thermal Sensors** | CPU cores & GPU junction | Core silicone junction temps | 1 Hz |
| **DC Power Analyzer** | Main 28V DC power bus input | Voltage, Current, Power (W) | 10 Hz |
| **Software Telemetry Client** | QualificationTelemetry daemon | FPS, Latency (ms), Errors | 30 Hz |

---

## 3. Thermal Cycle Profile

The test executes 4 complete operational thermal cycles following the deterministic sequence:

```text
[Ambient +25°C]
       │
       ▼ (Ramp Down @ 1°C/min)
┌────────────────────────────────────────────────────────┐
│ 1. COLD PLATEAU (-10°C)                                │
│    ├── Chamber dwell & stabilization: 60 minutes       │
│    ├── System Cold-Boot Trigger: Measure T_boot        │
│    ├── Camera & AI detector initialization audit      │
│    ├── Nominal 4-step experiment procedure execution   │
│    └── Measurement: Latency P95, FPS, Power Draw       │
└────────────────────────────────────────────────────────┘
       │
       ▼ (Ramp Up @ 1°C/min)
┌────────────────────────────────────────────────────────┐
│ 2. WARM/HOT PLATEAU (+50°C)                            │
│    ├── Chamber dwell & stabilization: 60 minutes       │
│    ├── High-workload endurance run (500 frames)        │
│    ├── Thermal throttling check (CPU/GPU frequencies)  │
│    ├── Deviation detection & recovery verification     │
│    └── Measurement: Peak silicone die temp, RSS memory │
└────────────────────────────────────────────────────────┘
       │
       ▼ (Repeat for 4 Full Cycles)
       │
[Controlled Return to +25°C & Post-Test Functional Audit]
```

---

## 4. Test Procedure Step-by-Step

1. **Pre-Test Inspection:** Record physical baseline, lens optical focus, and compute checksums (`astra qualification dependencies`).
2. **Mounting:** Install DUT in thermal chamber and secure all thermocouple sensors.
3. **Pre-Test Functional Audit:** Run `astra qualification test-status` and execute baseline demo run at $+25^\circ\text{C}$.
4. **Cycle Execution:**
   - Command chamber to $-10^\circ\text{C}$. Soak for 1 hour until internal case temperature stabilizes ($\Delta T < 1^\circ\text{C}$ over 15 min).
   - Apply power. Verify cold boot within 5.0 seconds. Run 100 frames of optical inference.
   - Ramp chamber to $+50^\circ\text{C}$ at $1^\circ\text{C}/\text{min}$. Soak for 1 hour at $+50^\circ\text{C}$.
   - Execute continuous pipeline inference. Monitor CPU core frequency and check for thermal throttling flags in kernel dmesg.
   - Cycle 4 times consecutively.
5. **Controlled Shutdown:** At conclusion of Cycle 4 hot dwell, issue graceful software shutdown (`POWER_SHUTDOWN`).
6. **Return to Ambient:** Return chamber to $+25^\circ\text{C}$. Allow 2 hours thermal equalization.
7. **Post-Test Functional Audit:** Execute standard functional sweep `SFB-001`. Compare pre vs post metrics.

---

## 5. Acceptance Criteria

| Parameter | Specification Limit | Test Evaluation Method |
| :--- | :--- | :--- |
| **Cold Boot Latency** | $\le 5.0$ seconds at $-10^\circ\text{C}$ | Time to `READY` telemetry packet |
| **Pipeline Throughput** | $\ge 30.0$ FPS across entire cycle | `QualificationTelemetry.fps` |
| **End-to-End Latency (P95)** | $\le 50.0$ ms at $-10^\circ\text{C}$ and $+50^\circ\text{C}$ | Timestamp delta histogram |
| **Silicon Junction Temp** | $<85.0^\circ\text{C}$ (NVIDIA/Arm safe ceiling) | Internal sensor telemetry |
| **Thermal Throttling** | Zero throttling events detected | Sysfs throttling state register |
| **Data & SQLite Integrity** | 100% SQLite `PRAGMA integrity_check = ok` | Post-test database verification |
| **Camera Focus Stability** | Defocus $<0.2$ mm / MTF50 degradation $<5\%$ | Collimator chart inspection |

---

## 6. Failure Handling & Nonconformance

- If the system fails to boot at $-10^\circ\text{C}$ or triggers thermal throttling at $+50^\circ\text{C}$, the test shall be immediately paused in place.
- The test operator shall generate a Nonconformance Record (`NCR-THM-xxx`) logging exact chamber temperature, sensor telemetry, and kernel logs.
- The DUT shall not be modified without authorized Material Review Board (MRB) disposition.
