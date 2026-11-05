# ASTRA-EA: Electromagnetic Compatibility (EMI/EMC) Qualification Test Plan

**Document ID:** `ASTRA-QTP-EMC-001`  
**Test Identifier:** `QUAL-EMC-001` to `QUAL-EMC-004`  
**Standard:** MIL-STD-461G (Requirements for the Control of Electromagnetic Interference) / ECSS-E-ST-20-07C  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

This qualification plan defines the electromagnetic compatibility test procedures to verify that ASTRA-EA does not emit excessive conducted or radiated noise that could interfere with spacecraft radios, avionics, or scientific payloads, and conversely remains immune to external electromagnetic fields and power line transients.

Specific goals:
1. **Conducted Emissions (CE102):** Quantify high-frequency ripple currents injected back into the spacecraft 28V power bus.
2. **Conducted Susceptibility (CS101):** Verify that sinusoidal noise superimposed on the power bus does not cause compute resets or frame dropouts.
3. **Radiated Emissions (RE102):** Measure radiated electric fields emitted from camera cabling, edge compute clock lines, and switching power supplies.
4. **Radiated Susceptibility (RS103):** Expose operating payload to high-intensity RF fields ($20\text{ V/m}$, 2 MHz to 18 GHz) while monitoring live inference performance.

---

## 2. Test Facility & Instrumentation

### 2.1 Test Chamber & Equipment
- **Anechoic RF Chamber:** Fully shielded RF test chamber with ferrite tiles and pyramidal absorber cones providing $>80\text{ dB}$ RF attenuation.
- **Line Impedance Stabilization Network (LISN):** $50\ \Omega / 50\ \mu\text{H}$ spacecraft LISN isolating 28V DC power source.
- **Measurement Antennas:**
  - Active Rod Antenna ($10\text{ kHz} - 30\text{ MHz}$)
  - Biconical Antenna ($30\text{ MHz} - 200\text{ MHz}$)
  - Double-Ridged Waveguide Horn ($200\text{ MHz} - 18\text{ GHz}$)
- **EMI Receiver / Spectrum Analyzer:** Calibrated receiver with peak, quasi-peak, and average detectors.

---

## 3. Scope of Testing (MIL-STD-461G)

| Test Method | Domain | Frequency Range | Applied Level / Limit Curve | Monitored Subsystem |
| :--- | :--- | :---: | :---: | :--- |
| **`CE102`** | Conducted Emissions, Power Leads | 10 kHz to 10 MHz | MIL-STD-461G Spacecraft Limit | DC-DC converter switching harmonics |
| **`CS101`** | Conducted Susceptibility, Power Leads | 30 Hz to 150 kHz | Up to $1.0\text{ V}_\text{rms}$ ripple | Core CPU/GPU voltage regulation |
| **`RE102`** | Radiated Emissions, Electric Field | 2 MHz to 18 GHz | MIL-STD-461G Spacecraft Limit | Camera GMSL/USB3 cable & compute clock |
| **`RS103`** | Radiated Susceptibility, Electric Field | 2 MHz to 18 GHz | $20.0\text{ V/m}$ continuous wave & pulse | Camera video stream, memory, inference loop |

---

## 4. Real-Time Software Functional Monitoring During EMI Exposure

During active radiated susceptibility (`RS103`) and conducted susceptibility (`CS101`) sweeps, the ASTRA-EA software runs continuous real-time self-auditing to detect subtle bit errors or bus stalls:

```text
MONITORED REAL-TIME SIGNALS:
├── Video ingestion frame error counter (V4L2 driver dropouts)
├── Object detection confidence stability (Delta conf < 0.05)
├── Decision latency jitter (Delta latency < 5 ms)
├── Process crash & auto-restart watchdog counter (Must remain ZERO)
├── Local SQLite WAL write transactions (Zero locked database errors)
└── SpaceWire / Telemetry packet transmission error rate (< 10^-6)
```

If RF field injection causes video frame freeze or process crash, the qualification software captures an immediate diagnostic snapshot with exact RF frequency and field strength.

---

## 5. Acceptance Criteria

1. **Emissions Compliance:** CE102 and RE102 emission levels remain at least $6.0\text{ dB}$ below the spacecraft qualification limit curves.
2. **Operational Immunity:** Under $20\text{ V/m}$ radiated field (RS103), system sustains $\ge 30.0$ FPS with zero unhandled exceptions.
3. **Data Integrity:** Zero corrupted database records, zero missed procedure state transitions, and zero kernel panics.
