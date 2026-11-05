# ASTRA-EA: Structural Vibration Qualification Test Plan

**Document ID:** `ASTRA-QTP-VIB-001`  
**Test Identifier:** `QUAL-VIB-001` (Random) / `QUAL-VIB-002` (Sine Sweep)  
**Standard:** NASA-STD-7001B (Payload Vibroacoustic Test Criteria) / ECSS-E-ST-10-03C §5.13  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

This qualification test program verifies that the ASTRA-EA mechanical chassis, optical camera assembly, internal circuit board mountings, NVMe storage interconnects, and electrical wiring harness survive launch vibroacoustic acoustic loads without structural deformation, fastener backing-out, optical defocus, or electrical disconnection.

Specific goals:
1. Subject the payload to random vibration energy across 3 orthogonal axes (X, Y, Z) at qualification levels ($14.1\text{ G}_\text{rms}$).
2. Execute low-level sine sweep resonance surveys (5–100 Hz @ 0.5 G) to identify fundamental natural frequencies and verify structural stiffness ($f_n > 60\text{ Hz}$).
3. Verify that the optical camera mount maintains rigid spatial alignment with defocus $<0.2$ mm post-vibration.
4. Execute standardized pre- and post-vibration functional test sweeps (`SFB-001`) to prove zero latent component degradation.

---

## 2. Vibration Facility & Test Fixture

### 2.1 Electrodynamic Shaker Facility
- **Shaker:** 3-axis electrodynamic shaker table capable of $\ge 50\text{ kN}$ force rating and $20\text{ mm}$ peak-to-peak displacement.
- **Vibration Controller:** Multi-channel digital vibration control system with independent limit channels and abort interlocks.
- **Interface Fixture:** Rigid magnesium/aluminum test fixture engineered with first resonant mode $>200\text{ Hz}$ to avoid fixture coupling into DUT measurements.

### 2.2 Accelerometer Instrumentation Plan

| Channel ID | Sensor Type | Mounting Location | Measurement Axis | Measurement Range |
| :--- | :--- | :--- | :---: | :---: |
| **`ACC-CTRL-01`** | Control Accelerometer | Shaker head / fixture base | Input Axis | $\pm 50\text{ G}$ |
| **`ACC-CTRL-02`** | Monitoring Accelerometer| Shaker fixture top surface | Input Axis | $\pm 50\text{ G}$ |
| **`ACC-DUT-01`** | Triaxial Accelerometer | Compute chassis center of gravity | X, Y, Z | $\pm 100\text{ G}$ |
| **`ACC-DUT-02`** | Triaxial Accelerometer | Optical camera mounting bracket | X, Y, Z | $\pm 100\text{ G}$ |
| **`ACC-DUT-03`** | Single-Axis Piezoresistive| NVMe storage board standoff | Normal to PCB | $\pm 100\text{ G}$ |
| **`ACC-DUT-04`** | Single-Axis Accelerometer | Lens front element barrel | Optical Axis | $\pm 100\text{ G}$ |

---

## 3. Qualification Vibration Profiles

### 3.1 Low-Level Sine Sweep Resonance Search (`QUAL-VIB-002`)
Executed before and after each random vibration run to detect structural frequency shifts indicating structural loosening or micro-cracking:
- **Frequency Range:** 5 Hz to 100 Hz
- **Sweep Rate:** 2.0 octaves/minute, logarithmic
- **Input Amplitude:** 0.5 G peak
- **Acceptance Criterion:** Shift in fundamental natural frequency $\Delta f_n < 5\%$.

### 3.2 Random Vibration Qualification Profile (`QUAL-VIB-001`)
- **Overall Level:** **$14.1\text{ G}_\text{rms}$** (Qualification level = Acceptance level + 3 dB)
- **Duration:** 120 seconds per axis (X, Y, and Z axes)

| Frequency (Hz) | Power Spectral Density ($\text{PSD}, \text{G}^2/\text{Hz}$) | Slope |
| :---: | :---: | :---: |
| 20 | 0.026 | $+6.0\text{ dB/octave}$ |
| 50 | 0.160 | Flat |
| 800 | 0.160 | Flat |
| 2000 | 0.026 | $-6.0\text{ dB/octave}$ |
| **Overall** | **$14.1\text{ G}_\text{rms}$** | **120 s / axis** |

---

## 4. Pre/Post-Vibration Functional Comparison Protocol

Vibration testing is inherently unpowered for safety. Therefore, a complete functional baseline check must be executed before and immediately after shaker exposure:

```text
PRE-VIBRATION TEST (SFB-001)
├── Fastener torque audit (mark all fasteners with torque seal)
├── Optical collimator focus test: MTF50 baseline = 0.42 cyc/px
├── Compute cold-boot: 2.1s
├── Full procedure execution: 34.2 FPS, 26.4ms P95 latency
└── Database checksum verification: MATCH

          [ AXIS X: 14.1 Grms Random Vibration (120s) ]
          [ AXIS Y: 14.1 Grms Random Vibration (120s) ]
          [ AXIS Z: 14.1 Grms Random Vibration (120s) ]
                       ↓
POST-VIBRATION TEST (SFB-001)
├── Visual & torque inspection: Zero loosened fasteners / zero seal cracks
├── Optical collimator focus test: MTF50 >= 0.38 cyc/px (Defocus < 0.2 mm)
├── Compute cold-boot: Must execute <= 5.0s
├── Full procedure execution: Must sustain >= 30.0 FPS, P95 <= 50.0 ms
└── SQLite database & model SHA-256 integrity: Zero corrupted blocks
```

---

## 5. Acceptance Criteria

1. **Structural Integrity:** No structural fracture, permanent plastic deformation, fastener disengagement, or connector pin loosening.
2. **Resonant Frequency Stability:** Fundamental frequency shift $\Delta f_n < 5\%$ between pre- and post-test sine sweeps.
3. **Optical Collimation:** Post-vibration MTF50 optical resolution degradation $<5\%$; camera mount pitch angle shift $<0.5^\circ$.
4. **Full Functional Operation:** 100% pass on standard functional sweep `SFB-001`.
5. **Zero Memory / Storage Corruption:** NVMe storage maintains 100% read/write file integrity without filesystem remounts.
