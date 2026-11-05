# ASTRA-EA: Thermal-Vacuum (TVAC) Qualification Test Plan

**Document ID:** `ASTRA-QTP-TVAC-001`  
**Test Identifier:** `QUAL-TVAC-001`  
**Standard:** ECSS-E-ST-10-03C §5.5 (Thermal-Vacuum Testing) / ECSS-Q-ST-70-02C (Outgassing)  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Target Environment:** High Vacuum ($10^{-5}\text{ Torr}$), Conductive Thermal Cycling ($-20^\circ\text{C}$ to $+60^\circ\text{C}$)  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

Thermal-Vacuum (TVAC) testing is the definitive aerospace qualification test for spacecraft payload electronics. Because vacuum eliminates all convective air cooling, all payload heat must be dissipated strictly via conduction to the spacecraft interface plate and radiation.

Specific goals:
1. Verify payload operational survival and heat dissipation under high vacuum ($\le 10^{-5}\text{ Torr}$).
2. Verify conductive thermal interface efficiency across 4 thermal-vacuum cycles ($-20^\circ\text{C}$ to $+60^\circ\text{C}$ baseplate).
3. Validate payload outgassing compliance (Total Mass Loss $\text{TML} < 1.0\%$, Collected Volatile Condensable Material $\text{CVCM} < 0.1\%$).
4. Verify cold-start and steady-state inference in a vacuum environment without corona discharge or dielectric breakdown.
5. Record synchronized multi-parameter telemetry correlating environmental pressure/temperature with software assurance states.

---

## 2. Chamber Facility & Setup

### 2.1 TVAC Chamber Requirements
- **Vacuum Level:** High-vacuum pumping system capable of maintaining $\le 1.0 \times 10^{-5}\text{ Torr}$ during active payload operation.
- **Thermal Baseplate:** Liquid nitrogen ($\text{LN}_2$) cooled and electrical resistance heated thermal cold-plate ($-40^\circ\text{C}$ to $+100^\circ\text{C}$ range).
- **Shroud Temperature:** Thermal shroud maintained at $\le -50^\circ\text{C}$ to simulate deep-space radiative heat sink.
- **Quartz Crystal Microbalance (QCM):** Installed near chamber optical ports to measure outgassing deposition rate.

### 2.2 Mechanical & Conductive Mounting
- The ASTRA-EA compute chassis shall be bolted to the thermal baseplate using flight-specified interface bolts torqued to $4.5\text{ N}\cdot\text{m}$.
- A space-grade low-outgassing thermal interface material (TIM, e.g. Chomerics CHO-THERM or indium foil) with thermal conductivity $\ge 3.0\text{ W/m}\cdot\text{K}$ shall be applied between chassis and plate.

### 2.3 Chamber Feedthrough Connections
- **Power:** 28V DC bus feedthrough with filtered EMI barrier.
- **Data/Telemetry:** Hermetically sealed MIL-DTL-38999 circular feedthrough for SpaceWire / Gigabit Ethernet.
- **Optical Chamber Port:** Anti-reflective coated optical quartz window allowing overhead camera to view external experiment test target.

---

## 3. Instrumentation Plan

| Instrument | Sensor ID | Measurement Parameter | Accuracy / Range |
| :--- | :--- | :--- | :---: |
| **Ionization Vacuum Gauge** | `VG-01` | Chamber vacuum pressure | $10^{-3}$ to $10^{-8}\text{ Torr}$ |
| **Cryogenic Baseplate RTD** | `RTD-BP-01` | Thermal plate conductive sink temp | $-50^\circ\text{C}$ to $+100^\circ\text{C}$ ($\pm 0.1^\circ\text{C}$) |
| **Chassis Conduction RTDs** | `RTD-CH-01..03`| DUT interface plate & case corners | $-40^\circ\text{C}$ to $+85^\circ\text{C}$ |
| **Camera Sensor RTD** | `RTD-CAM-01` | Camera CMOS die / housing temp | $-30^\circ\text{C}$ to $+75^\circ\text{C}$ |
| **Power Bus DAQ** | `DAQ-PWR-01` | 28V Bus voltage, current, power draw | $0-50\text{ V}$, $0-5\text{ A}$ (100 Hz) |
| **Quartz Microbalance** | `QCM-01` | Condensable outgassing mass rate | $\text{ng}/\text{cm}^2/\text{hr}$ |
| **Software Telemetry** | `QualTelemetry` | FPS, P95 Latency, State, Errors | 30 Hz continuous |

---

## 4. TVAC Environmental Data Model

The qualification engine records unified telemetry correlating environmental vacuum/thermal state directly to software performance:

```json
{
  "qualification_id": "ASTRA-EA-QB-001",
  "test_id": "QUAL-TVAC-001",
  "timestamp": "2026-09-13T12:00:00Z",
  "environment": {
    "pressure_torr": 1.2e-5,
    "baseplate_temp_c": 59.8,
    "shroud_temp_c": -52.4,
    "outgassing_rate_ug_cm2_hr": 0.04
  },
  "electrical": {
    "bus_voltage_v": 28.04,
    "bus_current_a": 0.62,
    "power_watts": 17.38
  },
  "system": {
    "cpu_die_temp_c": 71.4,
    "gpu_die_temp_c": 73.2,
    "fps": 33.8,
    "latency_p95_ms": 27.2,
    "assurance_state": "VERIFIED",
    "camera_health": "NOMINAL",
    "storage_health": "NOMINAL",
    "active_errors": []
  }
}
```

---

## 5. TVAC Cycle Sequence

```text
[Pump Down to 10^-5 Torr at +25°C Baseplate]
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│ 1. COLD VACUUM DWELL (-20°C Baseplate)                 │
│    ├── Chamber dwell: 4 hours                          │
│    ├── Cold-start under vacuum: Verify boot <= 5.0 s   │
│    ├── Optical focus & illumination invariance check    │
│    └── Full experiment sequence execution (500 frames) │
└────────────────────────────────────────────────────────┘
                    │
                    ▼ (Ramp Up @ 0.5°C/min)
┌────────────────────────────────────────────────────────┐
│ 2. HOT VACUUM DWELL (+60°C Baseplate)                  │
│    ├── Chamber dwell: 4 hours                          │
│    ├── Thermal conduction equilibrium verification     │
│    ├── Silicone die temp must remain <= 82°C           │
│    ├── Heavy inference workload (1000 frames)          │
│    └── Outgassing rate monitoring via QCM              │
└────────────────────────────────────────────────────────┘
                    │
                    ▼ (Repeat for 4 Complete Cycles)
                    │
[Controlled Return to +25°C & Dry Nitrogen Backfill]
```

---

## 6. Acceptance Criteria

1. **Vacuum Integrity:** Maintained pressure $\le 1.0 \times 10^{-5}\text{ Torr}$ throughout all 4 operational cycles.
2. **Thermal Dissipation:** Maximum silicon die temperature remains $\le 82.0^\circ\text{C}$ during $+60^\circ\text{C}$ baseplate plateau with zero thermal throttling.
3. **Pipeline Performance:** Throughput sustained $\ge 30.0$ FPS with P95 latency $\le 50.0$ ms under vacuum.
4. **Outgassing Limits:** Total condensable volatile material $\text{CVCM} < 0.1\%$; zero optical contamination on camera quartz window.
5. **Electrical Insulation:** Zero electrical corona discharge or ground fault trips across the 28V DC bus.
6. **Data & Artifact Integrity:** 100% SHA-256 match on all neural model weights, configuration files, and SQLite logs post-test.
