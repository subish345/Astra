# ASTRA-EA: Mechanical Shock Qualification Test Plan

**Document ID:** `ASTRA-QTP-SHK-001`  
**Test Identifier:** `QUAL-SHK-001`  
**Standard:** MIL-STD-810H Method 516.8 / ECSS-E-ST-10-03C §5.14 (Pyrotechnic Shock)  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Target Environment:** Pyrotechnic & Launch Vehicle Separation Shock (SRS up to $1,000\text{ G}$)  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

This test program specifies the future qualification protocol to verify that the ASTRA-EA payload survives high-amplitude, high-frequency mechanical shock events typical of launch vehicle fairing jettison, spacecraft stage separation, and solar array deployment pyrotechnics.

Specific goals:
1. Subject the payload to Shock Response Spectrum (SRS) pulses up to $1,000\text{ G}$ at $1,000\text{ Hz}$.
2. Verify that high-G shock waves do not fracture optical glass lens elements, shear fastener threads, dislodge soldered components, or unseat NVMe M.2 connectors.
3. Verify that post-shock electrical and optical alignments meet nominal operational specifications.

---

## 2. Test Facility & Instrumentation

### 2.1 Shock Generation Facility
- **Apparatus:** Resonant beam or drop table pyrotechnic shock simulator.
- **Fixture:** High-stiffness test plate reproducing the spacecraft payload mounting interface.

### 2.2 High-G Shock Instrumentation
- **Sensors:** Triaxial high-G piezoresistive shock accelerometers (`Endevco 7270A` or equivalent, rated to $\pm 10,000\text{ G}$, resonant frequency $>100\text{ kHz}$).
- **Data Acquisition:** High-speed transient recorder sampling at $\ge 1.0\text{ MHz}$ per channel with analog anti-aliasing filters.

---

## 3. Shock Response Spectrum (SRS) Specification

The qualification shock spectrum is defined with a damping ratio of $Q = 10$ ($5\%$ equivalent critical damping):

| Frequency (Hz) | Shock Response Spectrum (SRS) Amplitude |
| :---: | :---: |
| 100 | $20\text{ G}$ |
| 1,000 | $1,000\text{ G}$ |
| 10,000 | $1,000\text{ G}$ |

- **Exposure:** 3 shocks in both positive and negative directions along all 3 orthogonal axes (total of 18 shock events).

---

## 4. Test Execution Sequence

1. **Pre-Shock Functional State Verification:**
   - Execute standard functional sweep `SFB-001`.
   - Measure optical MTF50 and record camera calibration matrix ($f_x, f_y, c_x, c_y$).
   - Verify zero filesystem errors on NVMe storage.
2. **Shock Exposure:**
   - Mount payload to shock table interface.
   - Deliver calibrated shock pulses along $+X, -X, +Y, -Y, +Z, -Z$ axes.
   - Capture transient accelerometer waveforms and compute SRS curves in real-time.
3. **Post-Shock Physical & Visual Inspection:**
   - Inspect chassis under high-intensity inspection light for micro-fractures.
   - Inspect optical lens assembly for optical element displacement or delamination.
   - Audit fastener torques against pre-test marks.
4. **Post-Shock Functional Verification:**
   - Power on system. Verify cold boot latency $\le 5.0$ seconds.
   - Run 500 frames of laboratory experiment assurance.
   - Verify camera calibration matrix shift $\Delta f < 1.0\%$ and baseline throughput $\ge 30.0$ FPS.

---

## 5. Acceptance Criteria

- **Mechanical:** Zero physical cracking, fastener unseating, or connector displacement.
- **Optical:** Zero lens glass chipping or element decentering; camera calibration matrix shift $<1.0\%$.
- **Functional:** 100% pass on standard functional sweep `SFB-001`.
