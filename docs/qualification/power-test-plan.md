# ASTRA-EA: Spacecraft Power Interface Qualification Test Plan

**Document ID:** `ASTRA-QTP-PWR-001`  
**Test Identifier:** `QUAL-PWR-001`  
**Standard:** MIL-STD-704F / MIL-STD-1275E (Aircraft / Vehicle Electrical Power Characteristics) / ECSS-E-ST-20C  
**Configuration Baseline:** `ASTRA-EA-QB-001`  
**Nominal Power Interface:** Spacecraft 28V DC Unregulated Bus (18.0V to 36.0V DC operating range)  
**Current Execution Status:** **PLANNED**  

---

## 1. Objective

This qualification test program verifies that the ASTRA-EA power conversion stages, internal power sequencing, and software state machine operate reliably under nominal, transient, degraded, and interrupted power conditions on the spacecraft 28V DC power bus.

Specific goals:
1. Verify nominal steady-state operation within the 25.0W chassis power allocation across the full 18V to 36V voltage window.
2. Characterize cold-start inrush current and verify peak inrush remains below $2.5 \times I_{nom}$.
3. Verify software power state transitions (`POWER_WARNING`, `POWER_CRITICAL`, `POWER_LOSS`, `POWER_RECOVERY`).
4. Test brownout ride-through and verify that transient power dips $\le 50\text{ ms}$ do not reboot the system.
5. Verify uncorrupted recovery and state restoration following abrupt, unannounced bus power loss.

---

## 2. Electrical Test Setup & Instrumentation

### 2.1 Test Equipment
- **Programmable DC Power Supply:** Chroma 62000P or Keysight N6700 with arbitrary waveform generator capable of producing microsecond voltage dips and spikes.
- **Digital Storage Oscilloscope:** 4-channel $500\text{ MHz}$ oscilloscope with differential voltage probes and Rogowski current probes.
- **Electronic Load:** Programmable DC electronic load to simulate worst-case compute workloads.

### 2.2 Electrical Measurement Channels

| Signal ID | Measurement Point | Parameter | Range / Limit |
| :--- | :--- | :--- | :---: |
| **`V_BUS`** | Main 28V power connector input | Bus Voltage (V) | $0 - 50\text{ V}$ |
| **`I_BUS`** | Positive lead current probe | Bus Current (A) | $0 - 10\text{ A}$ (Inrush peak $<3.0\text{ A}$) |
| **`P_TOTAL`** | Mathematical product ($V \times I$) | Total Power Consumption (W) | $\le 25.0\text{ W}$ allocation |
| **`V_CORE`** | Internal POL converter output | Compute core voltage | $0.8\text{ V} \pm 2\%$ |
| **`PWR_GOOD`**| Hardware power-good supervisor | Logic state signal | Active HIGH ($3.3\text{ V}$) |

---

## 3. Software Power State Architecture

ASTRA-EA implements a deterministic 4-stage power defense state machine:

```text
       ┌────────────────────────┐
       │     POWER_NOMINAL      │ (22V - 34V DC)
       └───────────┬────────────┘
                   │ V_bus < 22V or V_bus > 34V
                   ▼
       ┌────────────────────────┐
       │     POWER_WARNING      │ ──> Reduce UI frame rate from 60 to 15 FPS
       └───────────┬────────────┘     Disable background dataset studio exports
                   │ V_bus < 19V or Temp > 80°C
                   ▼
       ┌────────────────────────┐
       │     POWER_CRITICAL     │ ──> Flush SQLite WAL buffer to non-volatile disk
       └───────────┬────────────┘     Halt streaming server; disengage auxiliary audio
                   │                  Commit current procedure step to flash
                   │ V_bus < 16V (Immediate drop)
                   ▼
       ┌────────────────────────┐
       │       POWER_LOSS       │ ──> Supercapacitor holds core rail for 100ms
       └───────────┬────────────┘     Clean sync() and hardware unmount
                   │
                   │ V_bus restored to > 24V for >= 2.0s
                   ▼
       ┌────────────────────────┐
       │     POWER_RECOVERY     │ ──> Execute database PRAGMA integrity_check
       └────────────────────────┘     Verify model SHA-256; resume procedure from step
```

---

## 4. Test Matrix & Applied Electrical Profiles

| Test ID | Applied Electrical Stimulus | Duration | Acceptance Criteria |
| :--- | :--- | :---: | :--- |
| **`PWR-STEADY-01`** | Nominal 28.0V DC bus input | Continuous | Power draw $\le 18.5\text{ W}$ typical, $\le 25.0\text{ W}$ peak |
| **`PWR-RANGE-01`** | Voltage sweep from 18.0V up to 36.0V | 10 min | Full pipeline sustains $\ge 30.0$ FPS across entire range |
| **`PWR-INRUSH-01`** | Cold-boot power-on step from 0V to 28V | Transient | Inrush peak $I_{peak} \le 2.5\text{ A}$; rise time $>10\ \mu\text{s}$ |
| **`PWR-BROWNOUT-01`**| Voltage dip from 28V down to 14V | $50\text{ ms}$ | Compute internal rails held by bulk capacitance; zero reboot |
| **`PWR-SPIKE-01`** | $+600\text{ V}$ inductive transient (MIL-STD-1275E)| $10\ \mu\text{s}$ | Clamped by internal TVS diode; zero hardware damage |
| **`PWR-CUT-01`** | Hard power disconnect during active inference | Instant | Supercapacitor ride-through flushes WAL; zero corrupted files |
| **`PWR-RECOV-01`** | Reapply 28V after hard disconnect | Instant | System boots to READY in $\le 5.0\text{ s}$; resumes procedure step |

---

## 5. Acceptance Criteria

1. **Power Budget Allocation:** Total power consumption under 100% full optical AI workload remains below **25.0 Watts**.
2. **Brownout Ride-Through:** Survives $50\text{ ms}$ voltage interruption without compute reboot or frame drop.
3. **State Preservation:** When entering `POWER_CRITICAL`, SQLite WAL log is flushed within $15\text{ ms}$ with zero record loss.
4. **Clean Resume:** Upon power restoration, system verifies database integrity and seamlessly resumes the interrupted experiment step without false verification or manual intervention.
